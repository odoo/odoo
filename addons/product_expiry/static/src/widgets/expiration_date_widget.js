/** @odoo-module */

import { DateTimeField, dateTimeField } from "@web/views/fields/datetime/datetime_field";
import { registry } from "@web/core/registry";

export class ExpirationDateWidgetField extends DateTimeField {
    setup() {
        super.setup();
        this.isExpired = this.props.record.data.is_expired;
    }
}
ExpirationDateWidgetField.template = "product_expiry.ExpirationDateWidget";

export const expirationDateWidgetField = {
    ...dateTimeField,
    component: ExpirationDateWidgetField,
};

registry.category("fields").add("expiration_date_widget", expirationDateWidgetField);
