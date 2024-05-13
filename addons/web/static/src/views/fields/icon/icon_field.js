import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class IconField extends Component {
    static template = "web.IconField";
    static props = {
        ...standardFieldProps,
        title: { type: String, optional: true },
    };
    static defaultProps = {
        title: "",
    };
}

export const iconField = {
    component: IconField,
    displayName: _t("Icon"),
    supportedTypes: ["char"],
    extractProps: ({ attrs }) => ({
        title: attrs.title,
    }),
};

registry.category("fields").add("icon", iconField);
