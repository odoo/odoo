/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("sign_widgets_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Settings",
            trigger: 'a[data-menu-xmlid="base.menu_administration"]',
            run: "click",
        },
        {
            content: "Users",
            trigger: "div#invite_users button.o_web_settings_access_rights",
            run: "click",
        },
        {
            content: "Mitchel",
            trigger: "table.o_list_table td.o_data_cell:contains(Admin)",
            run: "click",
        },

        {
            content: "Preference tab",
            trigger: 'a.nav-link:contains("' + _t("Preferences") + '")',
            run: "click",
        },
        {
            content: "Editor loaded",
            trigger: ".note-editable",
            run: "click",
        },
        {
            content: "Click on widget sign",
            trigger: ".o_signature:first",
            run: "click",
        },
        {
            content: "Click on auto button",
            trigger: ".o_web_sign_auto_button",
            run: "click",
        },
        {
            content: "Click on style button",
            trigger: ".o_web_sign_auto_select_style > button",
            run: "click",
        },
        {
            content: "Select a style",
            trigger: ".dropdown-menu .dropdown-item:nth-child(3)",
            run: "click",
        },
        {
            content: "Click on style button",
            trigger: ".o_web_sign_auto_select_style > button",
            run: "click",
        },
        {
            content: "Select a style",
            trigger: ".dropdown-menu .dropdown-item:nth-child(2)",
            run: "click",
        },
        {
            trigger: "canvas.o_web_sign_signature",
        },
        {
            content: "Sign",
            trigger: 'button.btn-primary:contains("Adopt & Sign")',
            run: "click",
        },
        ...stepUtils.saveForm(),
    ],
});
