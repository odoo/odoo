# -*- coding: utf-8 -*-
from pypom import Page


class BasePage(Page):
    _root_element_locator = ("css", ".o_content")
    _username_locator = ("css", ".oe_topbar_name")

    @property
    def loaded(self):
        root = self.find_element(*self._root_element_locator)
        return root.visible if root else False

    @property
    def username(self):
        return self.find_element(*self._username_locator).value
