/** @odoo-module **/

import { registry } from "@web/core/registry";
import { RadioField, radioField } from "@web/views/fields/radio/radio_field";

class RadioImageField extends RadioField {}
RadioImageField.template = "hr_holidays.RadioImageField";

registry.category("fields").add("hr_holidays_radio_image", {
    ...radioField,
    component: RadioImageField,
});
