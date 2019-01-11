@fixture.browser
Feature: Maintenance
  As a user
  I should be able to schedule a maintenance request
  So that I can get things fixed

  @issue-29810
  Scenario: Avatar image should not be shown for undefined maintenance request
    Given user "admin" has logged in with password "admin"
    And the user has browsed to the apps page
    And the admin has installed the "Maintenance" app
    When the user browses to the Scheduled Maintenance page
    And the user adds a maintenance request with summary
      """
      Need to fix this ASAP!!!
      """
    Then the technician assigned for the task should be "Undefined"
    And the avatar image of undefined user should not be displayed
