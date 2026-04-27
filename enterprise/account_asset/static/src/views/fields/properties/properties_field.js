/** @odoo-module **/

import { PropertiesField } from "@web/views/fields/properties/properties_field";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PropertiesField.prototype, {
    async onPropertyCreate() {
        if (
            this.props.record.resModel === 'account.asset'
            && (!this.state.canChangeDefinition || !(await this.checkDefinitionWriteAccess()))
        ) {
            this.notification.add(
                _t("You can add Property fields only on Assets with an Asset Model set."),
                { type: "warning" }
            );
            return;
        }
        super.onPropertyCreate();
    }
});
