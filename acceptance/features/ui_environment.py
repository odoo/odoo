# -*- coding: utf-8 -*-
import os

from behave import fixture, use_fixture
from splinter.browser import Browser

from pages.base_page import BasePage
from pages.login_page import LoginPage
from pages.apps_page import AppsPage
from pages.maintenance_page import ScheduledMaintenancePage


@fixture
def browser(context):
    user_data = context.config.userdata
    driver = user_data["driver_name"]

    kwargs = {"driver_name": driver}
    if driver == "remote":
        selenium_url = user_data["selenium_url"]
        kwargs.update({"url": selenium_url, "browser": "chrome"})
        if "TRAVIS" in os.environ:
            kwargs.update({"tunnel-identifier": os.environ["TRAVIS_JOB_NUMBER"]})

    context.browser = Browser(**kwargs)
    if "TRAVIS" in os.environ:
        session_id = context.browser.driver.session_id
        print("\nView SauceLabs job at:", f"https://saucelabs.com/jobs/{session_id}")
    yield context.browser

    # CLEANUP
    context.browser.quit()


@fixture
def get_pages(context):
    base_url = context.config.userdata.get("base_url")
    context.pages = {
        "base": BasePage(context.browser, base_url=base_url),
        "login": LoginPage(context.browser, base_url=base_url),
        "apps": AppsPage(context.browser, base_url=base_url),
        "scheduled_maintenance": ScheduledMaintenancePage(
            context.browser, base_url=base_url
        ),
    }
    return context.pages


def before_all(context):
    context.config.userdata.update(
        {
            "base_url": os.environ.get("BASE_URL", "http://localhost:8069"),
            "driver_name": os.environ.get("DRIVER_NAME", "chrome"),
        }
    )
    if "SELENIUM_URL" in os.environ:
        context.config.userdata["selenium_url"] = os.environ["SELENIUM_URL"]


def before_tag(context, tag):
    if "fixture.browser" in tag:
        use_fixture(browser, context)
        use_fixture(get_pages, context)
