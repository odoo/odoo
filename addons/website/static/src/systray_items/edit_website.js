/** @odoo-module **/

import { registry } from "@web/core/registry";

const { Component } = owl;

class EditWebsiteSystray extends Component {}
EditWebsiteSystray.template = "website.EditWebsiteSystray";

export const systrayItem = {
    Component: EditWebsiteSystray,
};

registry.category("website_systray").add("EditWebsite", systrayItem, { sequence: 9 });
