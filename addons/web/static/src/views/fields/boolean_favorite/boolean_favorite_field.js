import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { exprToBoolean } from "@web/core/utils/strings";
import { standardFieldProps } from "../standard_field_props";

import { Component, props, t } from "@odoo/owl";

export class BooleanFavoriteField extends Component {
    static template = "web.BooleanFavoriteField";
    props = props({
        ...standardFieldProps,
        noLabel: t.boolean().optional(false),
    });

    get iconClass() {
        return this.props.record.data[this.props.name] ? "fa fa-star" : "fa fa-star-o";
    }

    get label() {
        return this.props.record.data[this.props.name]
            ? _t("Remove from Favorites")
            : _t("Add to Favorites");
    }

    async update() {
        if (this.props.readonly) {
            return;
        }
        const changes = { [this.props.name]: !this.props.record.data[this.props.name] };
        await this.props.record.update(changes);
    }
}

export const booleanFavoriteField = {
    component: BooleanFavoriteField,
    displayName: _t("Favorite"),
    supportedTypes: ["boolean"],
    isEmpty: () => false,
    listViewWidth: ({ hasLabel }) => (!hasLabel ? 20 : false),
    extractProps: ({ attrs }, dynamicInfo) => ({
        noLabel: exprToBoolean(attrs.nolabel),
        readonly: dynamicInfo.readonly,
    }),
};

registry.category("fields").add("boolean_favorite", booleanFavoriteField);
