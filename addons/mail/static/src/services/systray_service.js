/** @odoo-module **/

import { CallSystrayMenuContainer } from "@mail/components/call_systray_menu_container/call_systray_menu_container";

import { registry } from "@web/core/registry";

const systrayRegistry = registry.category("systray");

export const systrayService = {
    dependencies: ["messaging"],
    start() {
        systrayRegistry.add(
            "mail.CallSystrayMenuContainer",
            { Component: CallSystrayMenuContainer },
            { sequence: 100 }
        );
    },
};
