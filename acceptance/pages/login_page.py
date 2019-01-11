# -*- coding: utf-8 -*-
from pypom import page


class LoginPage(page.Page):
    URL_TEMPLATE = "/web/login"
    _username_field_locator = ("name", "login")
    _password_field_locator = ("name", "password")
    _form_locator = ("css", ".oe_login_form")
    _form_submit_locator = ("css", ".btn-block")
    _form_error_message_locator = ("css", ".oe_login_form .alert-danger")

    @property
    def loaded(self):
        form = self.find_element(*self._form_locator)
        return form.visible if form else False

    def login(self, username, password):
        self.find_element(*self._username_field_locator).fill(username)
        self.find_element(*self._password_field_locator).fill(password)
        self.find_element(*self._form_submit_locator).click()

    @property
    def error_message(self):
        error_message = self.find_element(*self._form_error_message_locator)
        return error_message.value if error_message else None
