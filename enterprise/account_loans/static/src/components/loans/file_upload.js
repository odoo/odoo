import { registry } from "@web/core/registry";
import { FileUploader } from "@web/views/fields/file_handler";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component } from "@odoo/owl";


export class NewLoanComponent extends Component {
    static template = "account_accountant.NewLoan";
    static components = {
        FileUploader,
    };
    static props = {
        ...standardWidgetProps,
        record: { type: Object, optional: true },
    };

    setup() {
        this.orm = this.env.services.orm;
        this.action = this.env.services.action;
    }

    async onFileUploaded(file) {
        if (this.props.record && this.props.record.data.name){  //Save the record before calling the wizard
            await this.props.record.model.root.save({reload: false});
        }
        const att_data = {
            name: file.name,
            mimetype: file.type,
            datas: file.data,
        };
        const [att_id] = await this.orm.create("ir.attachment", [att_data]);
        const action = await this.orm.call("account.loan", "action_upload_amortization_schedule", [this.props.record?.resId, att_id]);
        this.action.doAction(action);
    }

    async openComputeWizard() {
        if (this.props.record && this.props.record.data.name){  //Save the record before calling the wizard
            await this.props.record.model.root.save({reload: false});
        }
        const action = await this.orm.call("account.loan", "action_open_compute_wizard", [this.props.record?.resId]);
        this.action.doAction(action);
    }
}

export const newLoan = {
    component: NewLoanComponent,
};

registry.category("view_widgets").add("new_loan", newLoan);
