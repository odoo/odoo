#!/usr/bin/python2.5
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the 'License')
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""User Agent Parser Unit Tests.
Run:
# python -m user_agent_parser_test  (runs all the tests, takes awhile)
or like:
# python -m user_agent_parser_test ParseTest.testBrowserscopeStrings
"""


from __future__ import unicode_literals, absolute_import

__author__ = "slamm@google.com (Stephen Lamm)"

import os
import re
import unittest
import yaml

try:
    # Try and use libyaml bindings if available since faster
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

from ua_parser import user_agent_parser

TEST_RESOURCES_DIR = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), "../uap-core"
)


class ParseTest(unittest.TestCase):
    def testBrowserscopeStrings(self):
        self.runUserAgentTestsFromYAML(
            os.path.join(TEST_RESOURCES_DIR, "tests/test_ua.yaml")
        )

    def testBrowserscopeStringsOS(self):
        self.runOSTestsFromYAML(os.path.join(TEST_RESOURCES_DIR, "tests/test_os.yaml"))

    def testStringsOS(self):
        self.runOSTestsFromYAML(
            os.path.join(TEST_RESOURCES_DIR, "test_resources/additional_os_tests.yaml")
        )

    def testStringsDevice(self):
        self.runDeviceTestsFromYAML(
            os.path.join(TEST_RESOURCES_DIR, "tests/test_device.yaml")
        )

    def testMozillaStrings(self):
        self.runUserAgentTestsFromYAML(
            os.path.join(
                TEST_RESOURCES_DIR, "test_resources/firefox_user_agent_strings.yaml"
            )
        )

    # NOTE: The YAML file used here is one output by makePGTSComparisonYAML()
    # below, as opposed to the pgts_browser_list-orig.yaml file.  The -orig
    # file is by no means perfect, but identifies many browsers that we
    # classify as "Other".  This test itself is mostly useful to know when
    # somthing in UA parsing changes.  An effort should be made to try and
    # reconcile the differences between the two YAML files.
    def testPGTSStrings(self):
        self.runUserAgentTestsFromYAML(
            os.path.join(TEST_RESOURCES_DIR, "test_resources/pgts_browser_list.yaml")
        )

    def testParseAll(self):
        user_agent_string = "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.4; fr; rv:1.9.1.5) Gecko/20091102 Firefox/3.5.5,gzip(gfe),gzip(gfe)"
        expected = {
            "device": {"family": "Mac", "brand": "Apple", "model": "Mac"},
            "os": {
                "family": "Mac OS X",
                "major": "10",
                "minor": "4",
                "patch": None,
                "patch_minor": None,
            },
            "user_agent": {
                "family": "Firefox",
                "major": "3",
                "minor": "5",
                "patch": "5",
            },
            "string": user_agent_string,
        }

        result = user_agent_parser.Parse(user_agent_string)
        self.assertEqual(
            result,
            expected,
            "UA: {0}\n expected<{1}> != actual<{2}>".format(
                user_agent_string, expected, result
            ),
        )

    # Make a YAML file for manual comparsion with pgts_browser_list-orig.yaml
    def makePGTSComparisonYAML(self):
        import codecs

        outfile = codecs.open("outfile.yaml", "w", "utf-8")
        print >> outfile, "test_cases:"

        yamlFile = open(os.path.join(TEST_RESOURCES_DIR, "pgts_browser_list.yaml"))
        yamlContents = yaml.load(yamlFile, Loader=SafeLoader)
        yamlFile.close()

        for test_case in yamlContents["test_cases"]:
            user_agent_string = test_case["user_agent_string"]
            kwds = {}
            if "js_ua" in test_case:
                kwds = eval(test_case["js_ua"])

            (family, major, minor, patch) = user_agent_parser.ParseUserAgent(
                user_agent_string, **kwds
            )

            # Escape any double-quotes in the UA string
            user_agent_string = re.sub(r'"', '\\"', user_agent_string)
            print >> outfile, '    - user_agent_string: "' + user_agent_string + '"' + "\n" + '      family: "' + family + '"\n' + "      major: " + (
                "" if (major is None) else "'" + major + "'"
            ) + "\n" + "      minor: " + (
                "" if (minor is None) else "'" + minor + "'"
            ) + "\n" + "      patch: " + (
                "" if (patch is None) else "'" + patch + "'"
            )
        outfile.close()

    # Run a set of test cases from a YAML file
    def runUserAgentTestsFromYAML(self, file_name):
        yamlFile = open(os.path.join(TEST_RESOURCES_DIR, file_name))
        yamlContents = yaml.load(yamlFile, Loader=SafeLoader)
        yamlFile.close()

        for test_case in yamlContents["test_cases"]:
            # Inputs to Parse()
            user_agent_string = test_case["user_agent_string"]
            kwds = {}
            if "js_ua" in test_case:
                kwds = eval(test_case["js_ua"])

            # The expected results
            expected = {
                "family": test_case["family"],
                "major": test_case["major"],
                "minor": test_case["minor"],
                "patch": test_case["patch"],
            }

            result = {}
            result = user_agent_parser.ParseUserAgent(user_agent_string, **kwds)
            self.assertEqual(
                result,
                expected,
                "UA: {0}\n expected<{1}, {2}, {3}, {4}> != actual<{5}, {6}, {7}, {8}>".format(
                    user_agent_string,
                    expected["family"],
                    expected["major"],
                    expected["minor"],
                    expected["patch"],
                    result["family"],
                    result["major"],
                    result["minor"],
                    result["patch"],
                ),
            )

    def runOSTestsFromYAML(self, file_name):
        yamlFile = open(os.path.join(TEST_RESOURCES_DIR, file_name))
        yamlContents = yaml.load(yamlFile, Loader=SafeLoader)
        yamlFile.close()

        for test_case in yamlContents["test_cases"]:
            # Inputs to Parse()
            user_agent_string = test_case["user_agent_string"]
            kwds = {}
            if "js_ua" in test_case:
                kwds = eval(test_case["js_ua"])

            # The expected results
            expected = {
                "family": test_case["family"],
                "major": test_case["major"],
                "minor": test_case["minor"],
                "patch": test_case["patch"],
                "patch_minor": test_case["patch_minor"],
            }

            result = user_agent_parser.ParseOS(user_agent_string, **kwds)
            self.assertEqual(
                result,
                expected,
                "UA: {0}\n expected<{1} {2} {3} {4} {5}> != actual<{6} {7} {8} {9} {10}>".format(
                    user_agent_string,
                    expected["family"],
                    expected["major"],
                    expected["minor"],
                    expected["patch"],
                    expected["patch_minor"],
                    result["family"],
                    result["major"],
                    result["minor"],
                    result["patch"],
                    result["patch_minor"],
                ),
            )

    def runDeviceTestsFromYAML(self, file_name):
        yamlFile = open(os.path.join(TEST_RESOURCES_DIR, file_name))
        yamlContents = yaml.load(yamlFile, Loader=SafeLoader)
        yamlFile.close()

        for test_case in yamlContents["test_cases"]:
            # Inputs to Parse()
            user_agent_string = test_case["user_agent_string"]
            kwds = {}
            if "js_ua" in test_case:
                kwds = eval(test_case["js_ua"])

            # The expected results
            expected = {
                "family": test_case["family"],
                "brand": test_case["brand"],
                "model": test_case["model"],
            }

            result = user_agent_parser.ParseDevice(user_agent_string, **kwds)
            self.assertEqual(
                result,
                expected,
                "UA: {0}\n expected<{1} {2} {3}> != actual<{4} {5} {6}>".format(
                    user_agent_string,
                    expected["family"],
                    expected["brand"],
                    expected["model"],
                    result["family"],
                    result["brand"],
                    result["model"],
                ),
            )


class GetFiltersTest(unittest.TestCase):
    def testGetFiltersNoMatchesGiveEmptyDict(self):
        user_agent_string = "foo"
        filters = user_agent_parser.GetFilters(
            user_agent_string, js_user_agent_string=None
        )
        self.assertEqual({}, filters)

    def testGetFiltersJsUaPassedThrough(self):
        user_agent_string = "foo"
        filters = user_agent_parser.GetFilters(
            user_agent_string, js_user_agent_string="bar"
        )
        self.assertEqual({"js_user_agent_string": "bar"}, filters)

    def testGetFiltersJsUserAgentFamilyAndVersions(self):
        user_agent_string = (
            "Mozilla/4.0 (compatible; MSIE 8.0; "
            "Windows NT 5.1; Trident/4.0; GTB6; .NET CLR 2.0.50727; "
            ".NET CLR 3.0.4506.2152; .NET CLR 3.5.30729)"
        )
        filters = user_agent_parser.GetFilters(
            user_agent_string, js_user_agent_string="bar", js_user_agent_family="foo"
        )
        self.assertEqual(
            {"js_user_agent_string": "bar", "js_user_agent_family": "foo"}, filters
        )


if __name__ == "__main__":
    unittest.main()
