import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
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
        this.dialog = useService("dialog");
        this.context = null;
        this.alias = null;
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
    }

    handleButtonClick(action, model = "account.journal") {
        // Prevent accidental data pollution with confirmation window
        this.dialog.add(ConfirmationDialog, {
            body: "Creating a sample bill will add demo data to your database. Are you sure you wish to proceed?",

            confirm: () => {
                this.action.doActionButton({
                    resModel: model,
                    name: action,
                    context: this.context || this.env.searchModel.context,
                    type: 'object',
                });
            },

            cancel: () => { },
        });

    }
}


export const billGuide = {
    component: BillGuide,
};

registry.category("view_widgets").add("bill_upload_guide", billGuide);
