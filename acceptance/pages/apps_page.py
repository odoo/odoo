# -*- coding: utf-8 -*-
from .base_page import BasePage
from .discuss_page import DiscussPage


class AppsPage(BasePage):
    URL_TEMPLATE = "/web#action=32&model=ir.module.module"
    _main_content_locator = ("css", ".o_kanban_ungrouped")
    _app_install_btn_locator = ("xpath", "//div[@title='{app_name}']//button")
    _app_installed_text_xpath = (
        "//div[@title='{app_name}']//div[contains(text(), 'Installed')]"
    )

    @property
    def loaded(self):
        return self.find_element(*self._main_content_locator).visible or False

    def install(self, app_name):
        strategy, selector = self._app_install_btn_locator
        app_installed_indicator = self.find_element(
            "xpath", self._app_installed_text_xpath.format(app_name=app_name)
        )

        if not app_installed_indicator:
            self.find_element(strategy, selector.format(app_name=app_name)).click()

            # wait till the app is installed
            wait = self.driver_adapter.wait_factory(30)
            wait.until(lambda _: DiscussPage.URL_TEMPLATE in self.driver.url)
