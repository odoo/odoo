/** @odoo-module **/

import { registry } from "@web/core/registry";
import { RadioField, preloadRadio } from "@web/views/fields/radio/radio_field";

class RadioImageField extends RadioField {}
RadioImageField.template = "hr_holidays.RadioImageField";

registry.category("fields").add("hr_holidays_radio_image", RadioImageField);

registry.category("preloadedData").add("hr_holidays_radio_image", {
    loadOnTypes: ["many2one"],
    preload: preloadRadio,
});
