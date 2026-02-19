/** @odoo-module **/

import { BooleanField } from "@web/views/fields/boolean/boolean_field";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";

export class CronTypeWidgetField extends BooleanField {
    static template = 'cron_type_widget'

    // Method to get the title based on the selected value
    get getTypeTitle() {
        if (this.props.value === 'manual') {
            return _lt("Manual");
        } else if (this.props.value === 'automatic') {
            return _lt("Automatic");
        }
    }
}

registry.category("fields").add("cron_type_widget", CronTypeWidgetField);
