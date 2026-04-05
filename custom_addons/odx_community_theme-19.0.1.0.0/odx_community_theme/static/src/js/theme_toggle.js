/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class ThemeToggle extends Component {
    static template = "odx_community_theme.ThemeToggle";
    static props = {};

    setup() {
        this.theme = useState(useService("odx_theme"));
    }

    toggle() {
        this.theme.toggleTheme();
    }

    get isDark() {
        return this.theme.resolvedTheme === "dark";
    }
}

registry.category("systray").add("odx_community_theme.theme_toggle", {
    Component: ThemeToggle,
}, { sequence: 100 });
