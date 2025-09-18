// @ts-check

/** @module @web/fields/basic/boolean_favorite/boolean_favorite_field - Star toggle field for marking records as favorites */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { standardFieldProps } from "@web/fields/standard_field_props";

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

    /** @returns {string} */
    get iconClass() {
        return this.props.record.data[this.props.name]
            ? "fa fa-star me-1"
            : "fa fa-star-o me-1";
    }

    /** @returns {string} */
    get label() {
        return this.props.record.data[this.props.name]
            ? _t("Remove from Favorites")
            : _t("Add to Favorites");
    }

    /** @returns {Promise<void>} */
    async update() {
        if (this.props.readonly) {
            return;
        }
        const changes = {
            [this.props.name]: !this.props.record.data[this.props.name],
        };
        await this.props.record.update(changes, { save: this.props.autosave });
    }
}

export const booleanFavoriteField = {
    component: BooleanFavoriteField,
    displayName: _t("Favorite"),
    supportedTypes: ["boolean"],
    isEmpty: () => false,
    listViewWidth: ({ hasLabel }) => (!hasLabel ? 20 : false),
    supportedOptions: [
        {
            label: _t("Autosave"),
            name: "autosave",
            type: "boolean",
            default: true,
            help: _t(
                "If checked, the record will be saved immediately when the field is modified.",
            ),
        },
    ],
    extractProps: ({ attrs, options }, dynamicInfo) => ({
        noLabel: exprToBoolean(attrs.nolabel),
        autosave: "autosave" in options ? Boolean(options.autosave) : true,
        readonly: dynamicInfo.readonly,
    }),
};

registry.category("fields").add("boolean_favorite", booleanFavoriteField);
