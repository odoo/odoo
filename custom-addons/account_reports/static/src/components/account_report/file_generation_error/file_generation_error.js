/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

export class FileGenerationErrorWidget extends Component {
    static template = "account_reports.FileGenerationErrorWidget";

    async setup() {
        super.setup();
        this.errors = JSON.parse(this.props.record.data.file_generation_errors);
    }

    async handleOnClick(error){
        const wizard = this.env.model.root;
        const reportAction = await this.env.model.orm.call(
            wizard.resModel,
            error.action_name,
            [wizard.resId, error.action_params],
        );
        this.env.model.action.doAction(reportAction);
    }
}

export const fileGenerationErrorWidget = {
    component: FileGenerationErrorWidget,
};

registry.category("fields").add("account_report_file_generation_error", fileGenerationErrorWidget);
