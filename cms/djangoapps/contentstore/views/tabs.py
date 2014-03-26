"""
Views related to course tabs
"""
import sys
from access import has_course_access
from util.json_request import expect_json, JsonResponse

from django.http import HttpResponseNotFound
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django_future.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from edxmako.shortcuts import render_to_response
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.django import loc_mapper
from xmodule.modulestore.locator import BlockUsageLocator
from xmodule.tabs import CourseTabList, StaticTab, CourseTab, InvalidTabsException

from ..utils import get_modulestore

from django.utils.translation import ugettext as _

__all__ = ['tabs_handler']

@expect_json
@login_required
@ensure_csrf_cookie
@require_http_methods(("GET", "POST", "PUT"))
def tabs_handler(request, tag=None, package_id=None, branch=None, version_guid=None, block=None):
    """
    The restful handler for static tabs.

    GET
        html: return page for editing static tabs
        json: not supported
    PUT or POST
        json: update the tab order. It is expected that the request body contains a JSON-encoded dict with entry "tabs".
        The value for "tabs" is an array of tab locators, indicating the desired order of the tabs.

    Creating a tab, deleting a tab, or changing its contents is not supported through this method.
    Instead use the general xblock URL (see item.xblock_handler).
    """
    locator = BlockUsageLocator(package_id=package_id, branch=branch, version_guid=version_guid, block_id=block)
    if not has_course_access(request.user, locator):
        raise PermissionDenied()

    old_location = loc_mapper().translate_locator_to_location(locator)
    store = get_modulestore(old_location)
    course_item = store.get_item(old_location)

    if 'application/json' in request.META.get('HTTP_ACCEPT', 'application/json'):
        if request.method == 'GET':
            raise NotImplementedError('coming soon')
        else:
            if 'tab_ids' in request.json:
                return reorder_tabs_handler(course_item, request)
            elif 'tab_id' in request.json:
                return edit_tab_handler(course_item, request)
            else:
                raise NotImplementedError('Creating or changing tab content is not supported.')

    elif request.method == 'GET':  # assume html
        # get all tabs from the tabs list: static tabs (a.k.a. user-created tabs) and built-in tabs
        # present in the same order they are displayed in LMS

        tabs_to_render = []
        for tab in CourseTabList.iterate_displayable_cms(
                course_item,
                settings,
        ):
            if isinstance(tab, StaticTab):
                static_tab_loc = old_location.replace(category='static_tab', name=tab.url_slug)
                static_tab = modulestore('direct').get_item(static_tab_loc)
                tab.locator = loc_mapper().translate_location(
                    course_item.location.course_id, static_tab.location, False, True
                )
            tabs_to_render.append(tab)

        return render_to_response('edit-tabs.html', {
            'context_course': course_item,
            'tabs_to_render': tabs_to_render,
            'course_locator': locator
        })
    else:
        return HttpResponseNotFound()


def reorder_tabs_handler(course_item, request):
    """
    Helper function for handling reorder of tabs request
    """

    old_tab_list = course_item.tabs

    ids_of_new_tab_order = request.json['tab_ids']

    # create a new list in the new order
    new_tab_list = []
    for tab_id in ids_of_new_tab_order:
        tab = CourseTabList.get_tab_by_id(old_tab_list, tab_id)
        if tab is None:
            return JsonResponse(
                {"error": "Tab with id '{0}' does not exist.".format(tab_id)}, status=400
            )
        new_tab_list.append(tab)

    # the old_tab_list may contain additional tabs that were not rendered in the UI because of
    # global or course settings.  so add those to the end of the list.
    old_tab_ids = [tab.tab_id for tab in old_tab_list]
    non_displayed_tab_ids = set(old_tab_ids) - set(ids_of_new_tab_order)
    for non_displayed_tab_id in non_displayed_tab_ids:
        new_tab_list.append(CourseTabList.get_tab_by_id(old_tab_list, non_displayed_tab_id))

    # validate the tabs to make sure everything is Ok (e.g., did the client try to reorder unmovable tabs?)
    try:
        CourseTabList.validate_tabs(new_tab_list)
    except InvalidTabsException, e:
        return JsonResponse(
            {"error": "New list of tabs is not valid: {0}.".format(str(e))}, status=400
        )

    course_item.tabs = new_tab_list
    modulestore('direct').update_item(course_item, request.user.id)

    return JsonResponse()


def edit_tab_handler(course_item, request):
    """
    Helper function for handling requests to edit settings of a single tab
    """
    tab_id = request.json['tab_id']

    tab = CourseTabList.get_tab_by_id(course_item.tabs, tab_id)
    if tab is None:
        return JsonResponse(
            {"error": "Tab with id '{0}' does not exist.".format(tab_id)}, status=400
        )

    if 'is_hidden' in request.json:
        tab.is_hidden = request.json['is_hidden']
        modulestore('direct').update_item(course_item, request.user.id)

    return JsonResponse()


# "primitive" tab edit functions driven by the command line.
# These should be replaced/deleted by a more capable GUI someday.
# Note that the command line UI identifies the tabs with 1-based
# indexing, but this implementation code is standard 0-based.

def validate_args(num, tab_type):
    "Throws for the disallowed cases."
    if num <= 1:
        raise ValueError('Tabs 1 and 2 cannot be edited')
    if tab_type == 'static_tab':
        raise ValueError('Tabs of type static_tab cannot be edited here (use Studio)')


def primitive_delete(course, num):
    "Deletes the given tab number (0 based)."
    tabs = course.tabs
    validate_args(num, tabs[num].get('type', ''))
    del tabs[num]
    # Note for future implementations: if you delete a static_tab, then Chris Dodge
    # points out that there's other stuff to delete beyond this element.
    # This code happens to not delete static_tab so it doesn't come up.
    modulestore('direct').update_item(course, '**replace_user**')


def primitive_insert(course, num, tab_type, name):
    "Inserts a new tab at the given number (0 based)."
    validate_args(num, tab_type)
    new_tab = CourseTab.from_json({u'type': unicode(tab_type), u'name': unicode(name)})
    tabs = course.tabs
    tabs.insert(num, new_tab)
    modulestore('direct').update_item(course, '**replace_user**')

