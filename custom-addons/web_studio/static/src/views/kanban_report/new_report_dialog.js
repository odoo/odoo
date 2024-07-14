/** @odoo-module */

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class NewReportDialog extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.user = useService("user");
        this.layouts = [
            {
                name: "web.external_layout",
                label: _t("External"),
                description: _t("Business header/footer"),
            },
            {
                name: "web.internal_layout",
                label: _t("Internal"),
                description: _t("Minimal header/footer"),
            },
            {
                name: "web.basic_layout",
                label: _t("Blank"),
                description: _t("No header/footer"),
            },
        ];
    }

    async createNewReport(layout) {
        const report = await this.rpc("/web_studio/create_new_report", {
            model_name: this.props.resModel,
            layout,
            context: this.user.context,
        });
        this.props.onReportCreated(report);
        this.props.close();
    }
}
NewReportDialog.template = "web_studio.NewReportDialog";
NewReportDialog.components = { Dialog };
NewReportDialog.props = ["resModel", "onReportCreated", "close"];
