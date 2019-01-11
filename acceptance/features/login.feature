@fixture.browser
Feature: Login
  As a user
  I should be able to login
  So that I can access my odoo account

  Scenario: User logs in with correct password
    When the user browses to the login page
    And the user logs in with username "admin" and password "admin"
    Then the user should be logged in as "Mitchell Admin"

  Scenario: User tries to log in with incorrect password
    When the user browses to the login page
    And the user logs in with username "admin" and password "adminhuma"
    Then the user should be redirected to the login page
    And the error message "Wrong login/password" should be displayed

  Scenario: User tries to log in with incorrect username
    When the user browses to the login page
    And the user logs in with username "adminhuma" and password "admin"
    Then the user should be redirected to the login page
    And the error message "Wrong login/password" should be displayed
