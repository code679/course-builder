# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# @author: psimakov@google.com (Pavel Simakov)

"""A collection of actions for testing Course Builder pages."""

import logging
import os
import re

import main
from models.models import Lesson
from models.models import Unit
import suite
from tools import verify

from google.appengine.api import namespace_manager


class TestBase(suite.BaseTestClass):
    """Contains methods common to all tests."""

    def getApp(self):
        main.debug = True
        return main.app

    def setUp(self):
        super(TestBase, self).setUp()

        # set desired namespace and inits data
        namespace = namespace_manager.get_namespace()
        try:
            if hasattr(self, 'namespace'):
                namespace_manager.set_namespace(self.namespace)
            self.init_datastore()
        finally:
            if not namespace:
                namespace_manager.set_namespace(None)

    def init_datastore(self):
        """Loads course data from the CSV files."""
        logging.info('')
        logging.info('Initializing datastore')

        # load and parse data from CSV file
        unit_file = os.path.join(
            os.path.dirname(__file__), '../../data/unit.csv')
        lesson_file = os.path.join(
            os.path.dirname(__file__), '../../data/lesson.csv')
        units = verify.read_objects_from_csv_file(
            unit_file, verify.UNITS_HEADER, Unit)
        lessons = verify.read_objects_from_csv_file(
            lesson_file, verify.LESSONS_HEADER, Lesson)

        # store all units and lessons
        for unit in units:
            unit.put()
        for lesson in lessons:
            lesson.put()
        assert Unit.all().count() == 11
        assert Lesson.all().count() == 29

    def canonicalize(self, href, response=None):
        """Create absolute URL using <base> if defined, '/' otherwise."""
        if href.startswith('/'):
            return href
        base = '/'
        if response:
            match = re.search(r'<base href=[\'"]?([^\'" >]+)', response.body)
            if match and not href.startswith('/'):
                base = match.groups()[0]
        return '%s%s' % (base, href)

    def hook_response(self, response):
        """Modify response.goto() to compute URL using <base>, if defined."""
        gotox = response.goto

        def newGoto(href, method='get', **args):
            return gotox(self.canonicalize(href), method, **args)

        response.goto = newGoto
        return response

    def get(self, url):
        url = self.canonicalize(url)
        logging.info('HTTP Get: %s', url)
        response = self.testapp.get(url)
        return self.hook_response(response)

    def post(self, url, params):
        url = self.canonicalize(url)
        logging.info('HTTP Post: %s', url)
        response = self.testapp.post(url, params)
        return self.hook_response(response)

    def click(self, response, name):
        logging.info('Link click: %s', name)
        response = response.click(name)
        return self.hook_response(response)

    def submit(self, form):
        logging.info('Form submit: %s', form)
        response = form.submit()
        return self.hook_response(response)


def assert_equals(expected, actual):
    if not expected == actual:
        raise Exception('Expected \'%s\', does not match actual \'%s\'.' %
                        (expected, actual))


def assert_contains(needle, haystack):
    if not needle in haystack:
        raise Exception('Can\'t find \'%s\' in \'%s\'.' % (needle, haystack))


def assert_none_fail(browser, callbacks):
    """Invokes all callbacks and expects each one not to fail."""
    for callback in callbacks:
        callback(browser)


def assert_all_fail(browser, callbacks):
    """Invokes all callbacks and expects each one to fail."""

    class MustFail(Exception):
        pass

    for callback in callbacks:
        try:
            callback(browser)
            raise MustFail('Expected to fail: %s().' % callback.__name__)
        except MustFail as e:
            raise e
        except Exception:
            pass


def login(email):
    os.environ['USER_EMAIL'] = email
    os.environ['USER_ID'] = 'user1'


def get_current_user_email():
    email = os.environ['USER_EMAIL']
    if not email:
        raise Exception('No current user.')
    return email


def logout():
    del os.environ['USER_EMAIL']
    del os.environ['USER_ID']


def register(browser, name):
    """Registers a new student with the given name."""

    response = browser.get('/')
    assert_equals(response.status_int, 302)

    response = view_registration(browser)

    response.form.set('form01', name)
    response = browser.submit(response.form)

    assert_contains('Thank you for registering for', response.body)
    check_profile(browser, name)


def check_profile(browser, name):
    response = view_my_profile(browser)
    assert_contains('Email', response.body)
    assert_contains(name, response.body)
    assert_contains(get_current_user_email(), response.body)
    return response


def view_registration(browser):
    response = browser.get('register')
    assert_contains('What is your name?', response.body)
    return response


def view_preview(browser):
    response = browser.get('preview')
    assert_contains(' the stakes are high.', response.body)
    assert_contains(
        '<li><p class="top_content">Pre-course assessment</p></li>',
        response.body)
    return response


def view_course(browser):
    response = browser.get('course')
    assert_contains(' the stakes are high.', response.body)
    assert_contains('<a href="assessment?name=Pre">Pre-course assessment</a>',
                    response.body)
    assert_contains(get_current_user_email(), response.body)
    return response


def view_unit(browser):
    response = browser.get('unit?unit=1&lesson=1')
    assert_contains('Unit 1 - Introduction', response.body)
    assert_contains(get_current_user_email(), response.body)
    return response


def view_activity(browser):
    response = browser.get('activity?unit=1&lesson=2')
    assert_contains('<script src="assets/js/activity-1.2.js"></script>',
                    response.body)
    assert_contains(get_current_user_email(), response.body)
    return response


def view_announcements(browser):
    response = browser.get('announcements')
    assert_contains('Example Announcement', response.body)
    assert_contains(get_current_user_email(), response.body)
    return response


def view_my_profile(browser):
    response = browser.get('student/home')
    assert_contains('Date enrolled', response.body)
    assert_contains(get_current_user_email(), response.body)
    return response


def view_forum(browser):
    response = browser.get('forum')
    assert_contains('document.getElementById("forum_embed").src =',
                    response.body)
    assert_contains(get_current_user_email(), response.body)
    return response


def view_assessments(browser):
    for name in ['Pre', 'Mid', 'Fin']:
        response = browser.get('assessment?name=%s' % name)
        assert 'assets/js/assessment-%s.js' % name in response.body
        assert_equals(response.status_int, 200)
        assert_contains(get_current_user_email(), response.body)


def change_name(browser, new_name):
    response = browser.get('student/home')

    response.form.set('name', new_name)
    response = browser.submit(response.form)

    assert_equals(response.status_int, 302)
    check_profile(browser, new_name)


def unregister(browser):
    response = browser.get('student/home')
    response = browser.click(response, 'Unenroll')

    assert_contains('to unenroll from', response.body)
    browser.submit(response.form)


class Permissions(object):
    """Defines who can see what."""

    @classmethod
    def get_logged_out_allowed_pages(cls):
        """Returns all pages that a logged-out user can see."""
        return [view_preview]

    @classmethod
    def get_logged_out_denied_pages(cls):
        """Returns all pages that a logged-out user can't see."""
        return [view_announcements, view_forum, view_course, view_assessments,
                view_unit, view_activity, view_my_profile, view_registration]

    @classmethod
    def get_enrolled_student_allowed_pages(cls):
        """Returns all pages that a logged-in, enrolled student can see."""
        return [view_announcements, view_forum, view_course,
                view_assessments, view_unit, view_activity, view_my_profile]

    @classmethod
    def get_enrolled_student_denied_pages(cls):
        """Returns all pages that a logged-in, enrolled student can't see."""
        return [view_registration, view_preview]

    @classmethod
    def get_unenrolled_student_allowed_pages(cls):
        """Returns all pages that a logged-in, unenrolled student can see."""
        return [view_registration, view_preview]

    @classmethod
    def get_unenrolled_student_denied_pages(cls):
        """Returns all pages that a logged-in, unenrolled student can't see."""
        pages = Permissions.get_enrolled_student_allowed_pages()
        for allowed in Permissions.get_unenrolled_student_allowed_pages():
            if allowed in pages:
                pages.remove(allowed)
        return pages

    @classmethod
    def assert_logged_out(cls, browser):
        """Check that only pages for a logged-out user are visible."""
        assert_none_fail(browser, Permissions.get_logged_out_allowed_pages())
        assert_all_fail(browser, Permissions.get_logged_out_denied_pages())

    @classmethod
    def assert_enrolled(cls, browser):
        """Check that only pages for an enrolled student are visible."""
        assert_none_fail(
            browser, Permissions.get_enrolled_student_allowed_pages())
        assert_all_fail(
            browser, Permissions.get_enrolled_student_denied_pages())

    @classmethod
    def assert_unenrolled(cls, browser):
        """Check that only pages for an unenrolled student are visible."""
        assert_none_fail(
            browser, Permissions.get_unenrolled_student_allowed_pages())
        assert_all_fail(
            browser, Permissions.get_unenrolled_student_denied_pages())