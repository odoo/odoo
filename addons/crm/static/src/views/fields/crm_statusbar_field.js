/** @odoo-module **/

import { registry } from "@web/core/registry";
import { StatusBarField, preloadStatusBar } from "@web/views/fields/statusbar/statusbar_field";
import { useCheckRainbowman } from "@crm/views/check_rainbowman_message";

export class CrmStatusBarField extends StatusBarField {
    setup() {
        super.setup();
        this.checkRainbowmanMessage = useCheckRainbowman();
    }

    /**
     * @override
     *
     * Check for rainbow man message when we change the stage.
     */
    async selectItem(item) {
        if (!this.props.readonly) {
            return super.selectItem(item);
        }
        // super does not await
        switch (this.props.type) {
            case "many2one":
                await this.props.update([item.id, item.name]);
                break;
            case "selection":
                await this.props.update(item.id);
                break;
        }
        await this.checkRainbowmanMessage(this.props.record.resId);
    }
}

registry.category("fields").add("crm_statusbar", CrmStatusBarField);

registry.category("preloadedData").add("crm_statusbar", {
    loadOnTypes: ["many2one"],
    extraMemoizationKey: (record, fieldName) => {
        return record.data[fieldName];
    },
    preload: preloadStatusBar,
});

import { FieldStatus } from "web.relational_fields";
import field_registry from "web.field_registry";

field_registry.add("crm_statusbar", FieldStatus);
