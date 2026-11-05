import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { PhoneField, phoneField } from "@web/views/fields/phone/phone_field";

class KanbanPhoneField extends PhoneField {
    static template = "hr.KanbanPhoneField";
}

registry.category("fields").add("hr_kanban_phone", {
    ...phoneField,
    component: KanbanPhoneField,
    displayName: _t("Employee Kanban Phone"),
    extractProps: (params) => ({
        ...phoneField.extractProps(params),
        displayButtons: params.options.display_buttons ?? true,
    }),
});
