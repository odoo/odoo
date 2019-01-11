# -*- coding: utf-8 -*-
from behave import *


@given('user "{username}" has logged in with password "{password}"')
def step_user_has_logged_in(context, username, password):
    """
    :type context: behave.runner.Context
    :type username: str
    """
    step_user_browses_to_login_page(context)
    step_user_logs_in_with(context, username, password)


@given('the admin has installed the "{app_name}" app')
def step_admin_install_app(context, app_name):
    """
    :type context: behave.runner.Context
    :type app_name: str
    """
    context.pages.get("apps").install(app_name)


@when("the user browses to the login page")
def step_user_browses_to_login_page(context):
    """
    :type context: behave.runner.Context
    """
    context.pages.get("login").open()


@when("the user browses to the apps page")
@given("the user has browsed to the apps page")
def step_user_browses_login_page(context):
    """
    :type context: behave.runner.Context
    """
    context.pages.get("apps").open()


@when('the user logs in with username "{username}" and password "{password}"')
def step_user_logs_in_with(context, username, password):
    """
    :type context: behave.runner.Context
    :type username: str
    :type password: str
    """
    context.pages.get("login").login(username, password)


@when("the user browses to the Scheduled Maintenance page")
def step_browses_to_scheduled_maintenance(context):
    """
    :type context: behave.runner.Context
    """
    context.pages.get("scheduled_maintenance").open()
    context.pages.get("scheduled_maintenance").wait_for_page_to_load()


@when("the user adds a maintenance request with summary")
def step_user_adds_maintenance_req_summary(context):
    """
    :type context: behave.runner.Context
    """
    context.pages.get("scheduled_maintenance").create_maintenance_request(context.text)


@then('the user should be logged in as "{name}"')
def step_user_redirected_to_apps_page(context, name):
    """
    :type context: behave.runner.Context
    :type name: str
    """
    base_page = context.pages.get("base")
    base_page.wait_for_page_to_load()
    assert (
        base_page.username == name
    ), f"Username could not be found. Found: {base_page.username}"


@then('the technician assigned for the task should be "{username}"')
def step_user_should_be_on_technicians_list(context, username):
    """
    :type context: behave.runner.Context
    :type username: str
    """
    technicians = context.pages.get("scheduled_maintenance").get_technicians_list()
    assert username in technicians, f"Could not find {username}. Found: {technicians}"


@then("the avatar image of undefined user should not be displayed")
def step_avatar_image_should_not_be_displayed(context):
    """
    :type context: behave.runner.Context
    """
    is_avatar_image_present = context.pages.get(
        "scheduled_maintenance"
    ).is_avatar_image_present("Undefined")
    assert (
        not is_avatar_image_present
    ), "Avatar image was not expected to be present but was"


@then("the user should be redirected to the login page")
def step_user_redirected_to_login_page(context):
    """
    :type context: behave.runner.Context
    """
    context.pages.get("login").wait_for_page_to_load()


@then('the error message "{expected_message}" should be displayed')
def step_error_message_should_be_displayed(context, expected_message):
    """
    :type context: behave.runner.Context
    :type expected_message: str
    """
    actual_message = context.pages.get("login").error_message
    assert actual_message == expected_message, f"Error message: {actual_message}"
