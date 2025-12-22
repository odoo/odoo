import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";

export class Breadcrumbs extends Component {
    static template = "web.Breadcrumbs";
    static components = { Dropdown, DropdownItem };
    static props = {
        breadcrumbs: Array,
        slots: { type: Object, optional: true },
    };

    getBreadcrumbTooltip({ isFormView, name }) {
        if (isFormView) {
            return _t("Back to “%s” form", name);
        }
        return _t("Back to “%s”", name);
    }
}
