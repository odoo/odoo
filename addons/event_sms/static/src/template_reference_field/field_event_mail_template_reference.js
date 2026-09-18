import { patch } from "@web/core/utils/patch";
import { EventMailTemplateReferenceField } from "@event/template_reference_field/field_event_mail_template_reference";

patch(EventMailTemplateReferenceField.prototype, {
    get templatesWithRelatedModel() {
        return [
            ...super.templatesWithRelatedModel,
            "sms.template",
        ];
    },
});
