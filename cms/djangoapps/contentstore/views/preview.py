from __future__ import absolute_import

import logging
import hashlib
from functools import partial

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from edxmako.shortcuts import render_to_string

from xmodule_modifiers import replace_static_urls, wrap_xblock, wrap_fragment
from xmodule.error_module import ErrorDescriptor
from xmodule.exceptions import NotFoundError, ProcessingError
from xmodule.modulestore.django import modulestore, loc_mapper, ModuleI18nService
from xmodule.modulestore.locator import Locator
from xmodule.x_module import ModuleSystem
from xblock.runtime import KvsFieldData
from xblock.django.request import webob_to_django_response, django_to_webob_request
from xblock.exceptions import NoSuchHandlerError
from xblock.fragment import Fragment

from lms.lib.xblock.field_data import LmsFieldData
from lms.lib.xblock.runtime import quote_slashes, unquote_slashes
from cms.lib.xblock.runtime import local_resource_url

from util.sandboxing import can_execute_unsafe_code

import static_replace
from .session_kv_store import SessionKeyValueStore
from .helpers import render_from_lms
from ..utils import get_course_for_item

from contentstore.views.access import get_user_role

__all__ = ['preview_handler']

log = logging.getLogger(__name__)


@login_required
def preview_handler(request, usage_id, handler, suffix=''):
    """
    Dispatch an AJAX action to an xblock

    usage_id: The usage-id of the block to dispatch to, passed through `quote_slashes`
    handler: The handler to execute
    suffix: The remainder of the url to be passed to the handler
    """
    # Note: usage_id is currently the string form of a Location, but in the
    # future it will be the string representation of a Locator.
    location = unquote_slashes(usage_id)

    descriptor = modulestore().get_item(location)
    instance = _load_preview_module(request, descriptor)
    # Let the module handle the AJAX
    req = django_to_webob_request(request)
    try:
        resp = instance.handle(handler, req, suffix)

    except NoSuchHandlerError:
        log.exception("XBlock %s attempted to access missing handler %r", instance, handler)
        raise Http404

    except NotFoundError:
        log.exception("Module indicating to user that request doesn't exist")
        raise Http404

    except ProcessingError:
        log.warning("Module raised an error while processing AJAX request",
                    exc_info=True)
        return HttpResponseBadRequest()

    except Exception:
        log.exception("error processing ajax call")
        raise

    return webob_to_django_response(resp)


class PreviewModuleSystem(ModuleSystem):  # pylint: disable=abstract-method
    """
    An XModule ModuleSystem for use in Studio previews
    """
    def handler_url(self, block, handler_name, suffix='', query='', thirdparty=False):
        return reverse('preview_handler', kwargs={
            'usage_id': quote_slashes(unicode(block.scope_ids.usage_id).encode('utf-8')),
            'handler': handler_name,
            'suffix': suffix,
        }) + '?' + query

    def local_resource_url(self, block, uri):
        return local_resource_url(block, uri)


def _preview_module_system(request, descriptor):
    """
    Returns a ModuleSystem for the specified descriptor that is specialized for
    rendering module previews.

    request: The active django request
    descriptor: An XModuleDescriptor
    """

    if isinstance(descriptor.location, Locator):
        course_location = loc_mapper().translate_locator_to_location(descriptor.location, get_course=True)
        course_id = course_location.course_id
    else:
        course_id = get_course_for_item(descriptor.location).location.course_id
    display_name_only = (descriptor.category == 'static_tab')

    wrappers = [
        # This wrapper wraps the module in the template specified above
        partial(wrap_xblock, 'PreviewRuntime', display_name_only=display_name_only),

        # This wrapper replaces urls in the output that start with /static
        # with the correct course-specific url for the static content
        partial(replace_static_urls, None, course_id=course_id),
        _studio_wrap_xblock,
    ]

    return PreviewModuleSystem(
        static_url=settings.STATIC_URL,
        # TODO (cpennington): Do we want to track how instructors are using the preview problems?
        track_function=lambda event_type, event: None,
        filestore=descriptor.runtime.resources_fs,
        get_module=partial(_load_preview_module, request),
        render_template=render_from_lms,
        debug=True,
        replace_urls=partial(static_replace.replace_static_urls, data_directory=None, course_id=course_id),
        user=request.user,
        can_execute_unsafe_code=(lambda: can_execute_unsafe_code(course_id)),
        mixins=settings.XBLOCK_MIXINS,
        course_id=course_id,
        anonymous_student_id='student',

        # Set up functions to modify the fragment produced by student_view
        wrappers=wrappers,
        error_descriptor_class=ErrorDescriptor,
        # get_user_role accepts a location or a CourseLocator.
        # If descriptor.location is a CourseLocator, course_id is unused.
        get_user_role=lambda: get_user_role(request.user, descriptor.location, course_id),
        descriptor_runtime=descriptor.runtime,
        services={
            "i18n": ModuleI18nService(),
        },
    )


def _load_preview_module(request, descriptor):
    """
    Return a preview XModule instantiated from the supplied descriptor.

    request: The active django request
    descriptor: An XModuleDescriptor
    """
    student_data = KvsFieldData(SessionKeyValueStore(request))
    descriptor.bind_for_student(
        _preview_module_system(request, descriptor),
        LmsFieldData(descriptor._field_data, student_data),  # pylint: disable=protected-access
    )
    return descriptor


# pylint: disable=unused-argument
def _studio_wrap_xblock(xblock, view, frag, context, display_name_only=False):
    """
    Wraps the results of rendering an XBlock view in a div which adds a header and Studio action buttons.
    """
    # Only add the Studio wrapper when on the container page. The unit page will remain as is for now.
    if context.get('container_view', None) and view == 'student_view':
        published = not context['is_draft']
        locator = loc_mapper().translate_location(xblock.course_id, xblock.location, published=published)
        template_context = {
            'xblock_context': context,
            'xblock': xblock,
            'locator': locator,
            'content': frag.content,
        }
        if xblock.category == 'vertical':
            template = 'studio_vertical_wrapper.html'
        elif xblock.location != context.get('root_xblock').location and xblock.has_children:
            template = 'container_xblock_component.html'
        else:
            template = 'studio_xblock_wrapper.html'
        html = render_to_string(template, template_context)
        frag = wrap_fragment(frag, html)
    return frag


def get_preview_fragment(request, descriptor, context):
    """
    Returns the HTML returned by the XModule's student_view,
    specified by the descriptor and idx.
    """
    module = _load_preview_module(request, descriptor)

    try:
        fragment = module.render("student_view", context)
    except Exception as exc:                          # pylint: disable=W0703
        log.warning("Unable to render student_view for %r", module, exc_info=True)
        fragment = Fragment(render_to_string('html_error.html', {'message': str(exc)}))
    return fragment
