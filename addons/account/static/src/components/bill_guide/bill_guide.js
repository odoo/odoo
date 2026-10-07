import { Component, proxy, t, usePlugin, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { ViewButton } from "@web/views/view_button/view_button";
import { LazySessionPlugin } from "@web/webclient/lazy_session_plugin";

export class BillGuide extends Component {
    static template = "account.BillGuide";
    static components = { ViewButton };

    props = useProps({
        ...standardWidgetProps,
        record: t.object().optional(),
    });

    setup() {
        this.lazySession = usePlugin(LazySessionPlugin);
        this.action = useService("action");
        this.ui = useService("ui");

        const rec = this.props.record;
        const ctx = this.env.searchModel.context;
        if (rec) {
            // prepare context from journal record
            this.context = {
                default_journal_id: rec.resId,
                default_move_type: (rec.data.type === 'sale' && 'out_invoice') || (rec.data.type === 'purchase' && 'in_invoice') || 'entry',
                active_model: rec.resModel,
                active_ids: [rec.resId],
            };
            this.alias = rec.data.alias_domain_id && rec.data.alias_id[1] || false;
        } else if (!ctx?.default_journal_id && ctx?.active_id) {
            this.context = {
                default_journal_id: ctx.active_id,
            };
        }

        this.showSampleAction = proxy({ value: false });
        this.lazySession.getValue("is_demo", v => (this.showSampleAction.value = !!v));
    }

    // the journal receiving the files of the upload button
    get uploadRecord() {
        return {
            resModel: "account.journal",
            resId: this.props.record?.resId,
            context: this.env.searchModel.context,
        };
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
            context: this.context || this.env.searchModel.context,
        });
    }

    get isMobileDevice() {
        return this.ui.isSmall;
    }
}


export const billGuide = {
    component: BillGuide,
};

registry.category("view_widgets").add("bill_upload_guide", billGuide);
