""" Tests for tab functions (just primitive). """

import json
from contentstore.views import tabs
from contentstore.tests.utils import CourseTestCase
from django.test import TestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from courseware.courses import get_course_by_id
from xmodule.tabs import CourseTabList, WikiTab, InvalidTabsException


class TabsPageTests(CourseTestCase):
    """Test cases for Tabs (a.k.a Pages) page"""

    def setUp(self):
        """Common setup for tests"""

        # call super class to setup course, etc.
        super(TabsPageTests, self).setUp()

        # Set the URL for tests
        self.url = self.course_locator.url_reverse('tabs')

        # add a static tab to the course, for code coverage
        ItemFactory.create(
            parent_location=self.course_location,
            category="static_tab",
            display_name="Static_1"
        )
        self.reload_course()

    def check_invalid_tab_id_response(self, resp):
        self.assertEqual(resp.status_code, 400)
        resp_content = json.loads(resp.content)
        self.assertIn("error", resp_content)
        self.assertIn("invalid_tab_id", resp_content['error'])

    def test_not_implemented(self):
        """Verify not implemented errors"""

        # JSON GET request not supported
        with self.assertRaises(NotImplementedError):
            self.client.get(self.url)

        # invalid JSON POST request
        with self.assertRaises(NotImplementedError):
            self.client.ajax_post(
                self.url,
                data={'invalid_request': None}
            )

    def test_view_index(self):
        """Basic check that the Pages page responds correctly"""
        resp = self.client.get_html(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('course-nav-tab-list', resp.content)

    def test_reorder_tabs(self):
        """Test re-ordering of tabs"""

        # get the original tab ids
        orig_tab_ids = [tab.tab_id for tab in self.course.tabs]
        tab_ids = list(orig_tab_ids)
        num_orig_tabs = len(orig_tab_ids)

        # make sure we have enough tabs to play around with
        self.assertTrue(num_orig_tabs >= 5)

        # reorder the last two tabs
        tab_ids[num_orig_tabs - 1], tab_ids[num_orig_tabs - 2] = tab_ids[num_orig_tabs - 2], tab_ids[num_orig_tabs - 1]

        # remove the middle tab
        # (the code needs to handle the case where tabs requested for re-ordering is a subset of the tabs in the course)
        removed_tab = tab_ids.pop(num_orig_tabs / 2)
        self.assertTrue(len(tab_ids) == num_orig_tabs - 1)

        # post the request
        resp = self.client.ajax_post(
            self.url,
            data={'tab_ids': tab_ids}
        )
        self.assertEqual(resp.status_code, 204)

        # reload the course and verify the new tab order
        self.reload_course()
        new_tab_ids = [tab.tab_id for tab in self.course.tabs]
        self.assertEqual(new_tab_ids, tab_ids + [removed_tab])
        self.assertNotEqual(new_tab_ids, orig_tab_ids)

    def test_reorder_tabs_invalid_list(self):
        """Test re-ordering of tabs with invalid tab list"""
        orig_tab_ids = [tab.tab_id for tab in self.course.tabs]
        tab_ids = list(orig_tab_ids)

        # reorder the first two tabs
        tab_ids[0], tab_ids[1] = tab_ids[1], tab_ids[0]

        # post the request
        resp = self.client.ajax_post(
                self.url,
                data={'tab_ids': tab_ids}
            )
        self.assertEqual(resp.status_code, 400)
        resp_content = json.loads(resp.content)
        self.assertIn("error", resp_content)

    def test_reorder_tabs_invalid_tab(self):
        """Test re-ordering of tabs with invalid tab"""
        invalid_tab_ids = ['courseware', 'info', 'invalid_tab_id']

        # post the request
        resp = self.client.ajax_post(
                self.url,
                data={'tab_ids': invalid_tab_ids}
            )
        self.check_invalid_tab_id_response(resp)

    def check_toggle_tab_visiblity(self, tab_type, new_is_hidden_setting):
        """Helper method to check changes in tab visibility"""
        # find the tab
        old_tab = CourseTabList.get_tab_by_type(self.course.tabs, tab_type)

        # visibility should be different from new setting
        self.assertNotEqual(old_tab.is_hidden, new_is_hidden_setting)

        # post the request
        resp = self.client.ajax_post(
            self.url,
            data=json.dumps({'tab_id': old_tab.tab_id, 'is_hidden': new_is_hidden_setting}),
        )
        self.assertEqual(resp.status_code, 204)

        # reload the course and verify the new visibility setting
        self.reload_course()
        new_tab = CourseTabList.get_tab_by_type(self.course.tabs, tab_type)
        self.assertEqual(new_tab.is_hidden, new_is_hidden_setting)

    def test_toggle_tab_visibility(self):
        """Test toggling of tab visiblity"""
        self.check_toggle_tab_visiblity(WikiTab.type, True)
        self.check_toggle_tab_visiblity(WikiTab.type, False)

    def test_toggle_invalid_tab_visibility(self):
        """Test toggling visibility of an invalid tab"""

        # post the request
        resp = self.client.ajax_post(
            self.url,
            data=json.dumps({'tab_id': 'invalid_tab_id'}),
        )
        self.check_invalid_tab_id_response(resp)


class PrimitiveTabEdit(TestCase):
    """Tests for the primitive tab edit data manipulations"""

    def test_delete(self):
        """Test primitive tab deletion."""
        course = CourseFactory.create(org='edX', course='999')
        with self.assertRaises(ValueError):
            tabs.primitive_delete(course, 0)
        with self.assertRaises(ValueError):
            tabs.primitive_delete(course, 1)
        with self.assertRaises(IndexError):
            tabs.primitive_delete(course, 6)
        tabs.primitive_delete(course, 2)
        self.assertFalse({u'type': u'textbooks'} in course.tabs)
        # Check that discussion has shifted up
        self.assertEquals(course.tabs[2], {'type': 'discussion', 'name': 'Discussion'})

    def test_insert(self):
        """Test primitive tab insertion."""
        course = CourseFactory.create(org='edX', course='999')
        tabs.primitive_insert(course, 2, 'notes', 'aname')
        self.assertEquals(course.tabs[2], {'type': 'notes', 'name': 'aname'})
        with self.assertRaises(ValueError):
            tabs.primitive_insert(course, 0, 'notes', 'aname')
        with self.assertRaises(ValueError):
            tabs.primitive_insert(course, 3, 'static_tab', 'aname')

    def test_save(self):
        """Test course saving."""
        course = CourseFactory.create(org='edX', course='999')
        tabs.primitive_insert(course, 3, 'notes', 'aname')
        course2 = get_course_by_id(course.id)
        self.assertEquals(course2.tabs[3], {'type': 'notes', 'name': 'aname'})
