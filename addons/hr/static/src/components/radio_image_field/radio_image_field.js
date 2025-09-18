import { registry } from "@web/core/registry";
import { RadioField, radioField } from "@web/fields/selection/radio/radio_field";

class RadioImageField extends RadioField {
    static template = "hr_homeworking.RadioImageField";
}

registry.category("fields").add("hr_homeworking_radio_image", {
    ...radioField,
    component: RadioImageField,
});
