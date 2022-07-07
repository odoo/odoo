/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { archParseBoolean } from "@web/views/utils";
import { standardFieldProps } from "../standard_field_props";

const { Component } = owl;

export class BooleanFavoriteField extends Component {}

BooleanFavoriteField.template = "web.BooleanFavoriteField";
BooleanFavoriteField.props = {
    ...standardFieldProps,
    noLabel: { type: Boolean, optional: true },
};
BooleanFavoriteField.defaultProps = {
    noLabel: false,
};

BooleanFavoriteField.displayName = _lt("Favorite");
BooleanFavoriteField.supportedTypes = ["boolean"];

BooleanFavoriteField.isEmpty = () => false;
BooleanFavoriteField.extractProps = ({ attrs }) => {
    return {
        noLabel: archParseBoolean(attrs.nolabel),
    };
};

registry.category("fields").add("boolean_favorite", BooleanFavoriteField);
