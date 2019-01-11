# -*- coding: utf-8 -*-
from pypom import Region

from .base_page import BasePage


class CreateMaintenancePopup(Region):
    _root_locator = ("css", ".modal-content")
    _summary_field_locator = ("css", ".o_input")
    _submit_button_locator = ("css", ".btn-primary")

    def create_request(self, summary):
        self.find_element(*self._summary_field_locator).fill(summary)
        self.find_element(*self._submit_button_locator).click()
        # wait until the popup disappears
        self.wait.until(lambda _: self.root is None)

    @property
    def loaded(self):
        return True if self.root else False


class ScheduledMaintenancePage(BasePage):
    URL_TEMPLATE = "/web#action=110&active_id=1&model=maintenance.request"

    _calendar_container_locator = ("css", ".o_calendar_container")
    _today_schedule_field_locator = ("css", "div.fc-day-grid td.fc-today")
    _technicians_items_locator = ("css", ".o_calendar_filter_item")

    @property
    def create_maintenance_popup(self):
        return CreateMaintenancePopup(self)

    @property
    def loaded(self):
        container = self.find_element(*self._calendar_container_locator)
        return container.visible if container else False

    def create_maintenance_request(self, summary):
        self.find_element(*self._today_schedule_field_locator).click()
        self.create_maintenance_popup.wait_for_region_to_load()
        self.create_maintenance_popup.create_request(summary)

    def get_technicians_list(self):
        technicians = self.find_elements(*self._technicians_items_locator)
        return [technician.value for technician in technicians]

    def is_avatar_image_present(self, name):
        technicians = self.find_elements(*self._technicians_items_locator)
        for technician in technicians:
            if technician.value == name:
                avatars = technician.find_by_css("img")
                return True if avatars else False
        return False
