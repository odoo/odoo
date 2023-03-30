import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { EventMailTemplateMany2OneField } from "./field_event_mail_template_many2one";
import { ReferenceField, referenceField } from "@web/views/fields/reference/reference_field";

export class EventMailTemplateReferenceField extends ReferenceField {
    static template = "event.mail_template_reference_field";
    static components = {
        Many2OneField: EventMailTemplateMany2OneField,
    };
}

export const eventMailTemplateReferenceField = {
    ...referenceField,
    component: EventMailTemplateReferenceField,
    displayName: _t("Event Mail Template Reference"),
};

registry.category("fields").add("event_mail_template_reference_field", eventMailTemplateReferenceField);
