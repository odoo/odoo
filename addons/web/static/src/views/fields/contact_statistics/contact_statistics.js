import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";

export class ContactStatisticsField extends Component {
    static template = "web.ContactStatisticsField";
    static props = {
        ...standardFieldProps,
    };

    get list() {
        return this.props.record.data[this.props.name] || [];
    }
}

export const contactStatisticsField = {
    component: ContactStatisticsField,
    displayName: _t("Contact Statistics"),
    supportedTypes: ["json"],
};

registry.category("fields").add("contact_statistics", contactStatisticsField);
