/** @odoo-module native */
import { AccountReturnSelectionBadge } from "@account/components/account_return/widgets/account_return_selection_badge";
import { useEffect, useState } from "@odoo/owl";
import { AccountReportLineName } from "@report_formula/components/account_report/line_name/line_name";
import { patch } from "@web/core/utils/patch";
import { RelationalModel } from "@web/model/relational_model";

patch(AccountReportLineName, {
    components: { ...AccountReportLineName.components, AccountReturnSelectionBadge },
});

patch(AccountReportLineName.prototype, {
    setup() {
        super.setup();
        this.accountStatus = useState({ record: false });
        useEffect(
            () => {
                this.loadAuditStatus();
            },
            () => [this.props.line],
        );
    },

    async loadAuditStatus() {
        if (this.props.line.account_status) {
            if (
                this.accountStatus.record &&
                this.props.line.account_status.id === this.accountStatus.record.resId
            ) {
                return;
            }

            const fields = {
                status: {
                    selection: [
                        ["todo", "To Review"],
                        ["reviewed", "Reviewed"],
                        ["supervised", "Supervised"],
                        ["anomaly", "Anomaly"],
                    ],
                    required: false,
                },
            };

            const model = new RelationalModel(
                this.env,
                {
                    config: {
                        resModel: "account.audit.account.status",
                        fields: fields,
                        activeFields: fields,
                        openGroupsByDefault: true,
                        isMonoRecord: true,
                    },
                    groupsLimit: Number.MAX_SAFE_INTEGER,
                    limit: 1,
                    countLimit: 1,
                },
                { orm: this.orm },
            );

            this.accountStatus.record = new model.constructor.Record(
                model,
                {
                    context: this.env.controller.context,
                    activeFields: fields,
                    fields: fields,
                    resModel: "account.audit.account.status",
                    resId: this.props.line.account_status.id,
                    resIds: [this.props.line.account_status.id],
                    isMonoRecord: true,
                    mode: "readonly",
                },
                this.props.line.account_status,
                { manuallyAdded: !this.props.line.account_status.id },
            );
        } else if (this.accountStatus.record) {
            this.accountStatus.record = false;
        }
    },

    get accountStatusBadgeOptions() {
        return {
            todo: { decoration: "info" },
            reviewed: { decoration: "success" },
            supervised: { decoration: "success" },
            anomaly: { decoration: "danger" },
        };
    },
});
