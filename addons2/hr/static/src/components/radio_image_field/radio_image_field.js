/** @odoo-module */

import { registry } from "@web/core/registry";
import { RadioField, preloadRadio, radioField } from "@web/views/fields/radio/radio_field";

class RadioImageField extends RadioField {}
RadioImageField.template = "hr_homeworking.RadioImageField";

registry.category("fields").add("hr_homeworking_radio_image", {
    ...radioField,
    component: RadioImageField,
});

registry.category("preloadedData").add("hr_homeworking_radio_image", {
    loadOnTypes: ["many2one"],
    preload: preloadRadio,
});
