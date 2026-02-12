import { Component } from "@odoo/owl";
import { ModelSelector } from "@web/core/model_selector/model_selector";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

export class CalendarLinkedRecord extends Component {
    static template = "calendar.CalendarLinkedRecord";
    static props = { ...standardFieldProps };
    static components = { ModelSelector };

    setup() {
        this.dialog = useService("dialog");
        this.action = useService("action");
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    get resModel() {
        return this.value?.resModel;
    }

    get resId() {
        return this.value?.resId;
    }

    get selection() {
        return this.props.record.fields[this.props.name].selection || [];
    }

    get displayName() {
        return this.value?.displayName;
    }

    get availableModels() {
        return this.selection.map((item) => item[0]);
    }

    get modelName() {
        if (!this.resModel) {
            return "";
        }
        const found = this.selection.find((item) => item[0] === this.resModel);
        return found ? found[1] : this.resModel;
    }

    onModelSelected(model) {
        const resModel = model.technical;
        if (resModel) {
            this.dialog.add(SelectCreateDialog, {
                resModel: resModel,
                title: "Select a Record To Link",
                noCreate: false,
                multiSelect: false,
                onSelected: async (resIds) => {
                    const resId = resIds[0];
                    if (resId) {
                        await this.props.record.update({
                            [this.props.name]: {
                                resModel: resModel,
                                resId: resId,
                            },
                        });
                    }
                },
                onClose: () => {},
            });
        }
    }

    openRecord() {
        if (!this.resId || !this.resModel) {
            return;
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: this.resModel,
            res_id: this.resId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    clearRecord() {
        this.props.record.update({ [this.props.name]: false });
    }
}

export const calendarLinkedRecord = {
    component: CalendarLinkedRecord,
    displayName: "Linked Record Selector",
    supportedTypes: ["reference"],
};

registry.category("fields").add("calendar_linked_record", calendarLinkedRecord);
