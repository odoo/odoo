import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { ListX2ManyField, listX2ManyField } from "@web/views/fields/x2many/list_x2many_field";
import { formatX2manyApplication } from "../../js/fields/formattedValue";

export class ClickableListX2ManyField extends ListX2ManyField{
    static template = "hr_recruitment.ClickableListX2ManyField"

    setup() {
        super.setup();
        this.action = useService("action");
    }

    get formattedValue() {
        return formatX2manyApplication(this.props.record.data[this.props.name]);
    }

    async openRecords() {
        const currentRecord = this.props.record.data[this.props.name];
        const model = this.props.record.fields[this.props.name].relation;

        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Related Records",
            res_model: model,
            views: [[false, "list"], [false, "form"]],
            domain: [["id", "in", currentRecord.currentIds]],
            context: {},
            target: "current",
        });
    }
}

export const clickableField = { ...listX2ManyField, component: ClickableListX2ManyField };
registry.category("fields").add("clickable_list_x2many", clickableField);
