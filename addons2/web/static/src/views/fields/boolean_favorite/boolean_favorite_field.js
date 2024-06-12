/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { archParseBoolean } from "@web/views/utils";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class BooleanFavoriteField extends Component {
    static template = "web.BooleanFavoriteField";
    static props = {
        ...standardFieldProps,
        noLabel: { type: Boolean, optional: true },
        autosave: { type: Boolean, optional: true },
    };
    static defaultProps = {
        noLabel: false,
    };

    async update() {
        const changes = { [this.props.name]: !this.props.record.data[this.props.name] };
        await this.props.record.update(changes, { save: this.props.autosave });
    }
}

export const booleanFavoriteField = {
    component: BooleanFavoriteField,
    displayName: _t("Favorite"),
    supportedTypes: ["boolean"],
    isEmpty: () => false,
    supportedOptions: [
        {
            label: _t("Autosave"),
            name: "autosave",
            type: "boolean",
            default: true,
            help: _t(
                "If checked, the record will be saved immediately when the field is modified."
            ),
        },
    ],
    extractProps: ({ attrs, options }) => ({
        noLabel: archParseBoolean(attrs.nolabel),
        autosave: "autosave" in options ? Boolean(options.autosave) : true,
    }),
};

registry.category("fields").add("boolean_favorite", booleanFavoriteField);
