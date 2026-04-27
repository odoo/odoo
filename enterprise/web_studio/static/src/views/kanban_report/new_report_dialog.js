/** @odoo-module */

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";

export class NewReportDialog extends Component {
    static template = "web_studio.NewReportDialog";
    static components = { Dialog };
    static props = ["resModel", "onReportCreated", "close"];

    setup() {
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
        const report = await rpc("/web_studio/create_new_report", {
            model_name: this.props.resModel,
            layout,
            context: user.context,
        });
        this.props.onReportCreated(report);
        this.props.close();
    }
}
