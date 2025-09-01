import { useDateTimePicker } from "@web/core/datetime/datetime_picker_hook";
import { serializeDate } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component } from "@odoo/owl";

export class ButtonNewContractWidget extends Component {
    static template = "hr.ButtonNewContract";
    static props = {
        ...standardWidgetProps,
    };

    /** @override **/
    setup() {
        super.setup();
        this.orm = useService("orm");

        this.dateTimePicker = useDateTimePicker({
            target: `datetime-picker-target-new-contract`,
            onApply: (date) => {
                if (date) {
                    this.tryAndCreateContract(serializeDate(date));
                }
            },
            get pickerProps() {
                return { type: "date" };
            },
        });
    }

    async onClickNewContractBtn() {
        await this.props.record.save();
        await this.orm.call("hr.version", "check_contract_finished", [
            [this.props.record.data.version_id.id],
        ]);
        this.dateTimePicker.open();
    }

    async tryAndCreateContract(date) {
        await this.orm.call("hr.employee", "check_no_existing_contract", [
            [this.props.record.resId],
            date,
        ]);
        const contract = await this.orm.call("hr.employee", "create_contract", [
            [this.props.record.resId],
            date,
        ]);
        await this.loadVersion(contract);
    }

    async loadVersion(version_id) {
        const { record } = this.props;
        await record.save();
        await this.props.record.model.load({
            context: {
                ...this.props.record.model.env.searchModel.context,
                version_id: version_id,
            },
        });
    }
}

export const buttonNewContractWidget = {
    component: ButtonNewContractWidget,
};

registry.category("view_widgets").add("button_new_contract", buttonNewContractWidget);
