import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DocumentFileUploader } from "../document_file_uploader/document_file_uploader";

import { Component, onWillStart } from "@odoo/owl";

export class BillGuide extends Component {
    static template = "account.BillGuide";
    static components = {
        DocumentFileUploader,
    };
    static props = ["*"];  // could contain view_widget props

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.context = null;
        this.alias = null;
        this.showSampleAction = false;
        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        const rec = this.props.record;
        const ctx = this.env.searchModel.context;
        if (rec) {
            // prepare context from journal record
            this.context = {
                default_journal_id: rec.resId,
                default_move_type: (rec.data.type === 'sale' && 'out_invoice') || (rec.data.type === 'purchase' && 'in_invoice') || 'entry',
                active_model: rec.resModel,
                active_ids: [rec.resId],
            }
            this.alias = rec.data.alias_domain_id && rec.data.alias_id[1] || false;
        } else if (!ctx?.default_journal_id && ctx?.active_id) {
            this.context = {
                default_journal_id: ctx.active_id,
            }
        }
        this.showSampleAction = await this.orm.call("account.journal", "is_sample_action_available");
    }

    handleButtonClick(action, model="account.journal") {
        this.action.doActionButton({
            resModel: model,
            name: action,
            context: this.context || this.env.searchModel.context,
            type: 'object',
        });
    }

    openVendorBill() {
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            views: [[false, "form"]],
            context: {
                default_move_type: "in_invoice",
            },
        });
    }
}


export const billGuide = {
    component: BillGuide,
};

registry.category("view_widgets").add("bill_upload_guide", billGuide);
