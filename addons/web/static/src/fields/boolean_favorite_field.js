/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { isFalsy } from "@web/core/utils/xml";
import { standardFieldProps } from "./standard_field_props";

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
BooleanFavoriteField.extractProps = (fieldName, record, attrs) => {
    return {
        noLabel: isFalsy(attrs.nolabel),
    };
};

registry.category("fields").add("boolean_favorite", BooleanFavoriteField);
