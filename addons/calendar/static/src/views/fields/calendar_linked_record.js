import { ModelSelector } from "@web/core/model_selector/model_selector";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { referenceField, ReferenceField } from "@web/views/fields/reference/reference_field";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

export class CalendarReferenceField extends ReferenceField {
    static template = "calendar.CalendarReferenceField";
    static components = { ModelSelector };

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.action = useService("action");
    }

    get availableModels() {
        return this.selection.map((item) => item[0]);
    }

    onModelSelected(model) {
        const resModel = model.technical;
        if (!resModel) {
            return;
        }
        this.dialog.add(SelectCreateDialog, {
            resModel,
            title: "Select a Record To Link",
            noCreate: true,
            multiSelect: false,
            onSelected: async (resIds) => {
                const resId = resIds[0];
                if (resId) {
                    await this.props.record.update({
                        [this.props.name]: {
                            resModel,
                            resId,
                        },
                    });
                }
            },
        });
    }

    openRecord() {
        const value = this.getValue();
        if (!value?.resId) {
            return;
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: value.resModel,
            res_id: value.resId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    clearRecord() {
        this.props.record.update({ [this.props.name]: false });
    }
}

export const calendarReferenceField = {
    ...referenceField,
    component: CalendarReferenceField,
    displayName: "Linked Record Selector",
    supportedTypes: ["reference"],
};

registry.category("fields").add("calendar_reference_field", calendarReferenceField);
