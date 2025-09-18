// @ts-check

/** @module @web/search/breadcrumbs/breadcrumbs - Navigation breadcrumb trail showing the action stack with back-navigation */

import { Component } from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
/** Navigation breadcrumb trail showing the action stack with back-navigation. */
export class Breadcrumbs extends Component {
    static template = "web.Breadcrumbs";
    static components = { Dropdown, DropdownItem };
    static props = {
        breadcrumbs: Array,
        slots: { type: Object, optional: true },
    };

    /**
     * @param {{ isFormView: boolean, name: string }} breadcrumb
     * @returns {string}
     */
    getBreadcrumbTooltip({ isFormView, name }) {
        if (isFormView) {
            return _t("Back to “%s” form", name);
        }
        return _t("Back to “%s”", name);
    }
}
