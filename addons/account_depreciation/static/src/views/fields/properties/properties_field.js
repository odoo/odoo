/** @odoo-module native */

import { PropertiesField } from "@web/fields/specialized/properties";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/translation";

patch(PropertiesField.prototype, {
    _getPropertyEditWarningText() {
        if (this.props.record.resModel === "account.asset") {
            return _t(
                "You can add Property fields only on Assets with a Depreciation Profile set.",
            );
        }
        return super._getPropertyEditWarningText();
    },
});
