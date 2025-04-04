/** @odoo-module **/

import { PropertiesField } from "@web/views/fields/properties/properties_field";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PropertiesField.prototype, {
    _getPropertyCreateWarningText() {
        if (this.props.record.resModel === "product.template" && !this.props.record.data?.categ_id) {
            return _t("You must set a product category to create a property field.");
        }
        return super._getPropertyCreateWarningText();
    },
});
