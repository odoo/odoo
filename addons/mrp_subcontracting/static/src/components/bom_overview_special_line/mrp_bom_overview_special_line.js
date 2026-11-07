import { patch } from "@web/core/utils/patch";
import { BomOverviewSpecialLine } from "@mrp/components/bom_overview_special_line/mrp_bom_overview_special_line";
import { usePlugin } from "@odoo/owl";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";

patch(BomOverviewSpecialLine.prototype, {
    setup() {
        super.setup();
        this.actionService = usePlugin(ActionPlugin);
    },

    //---- Handlers ----

    async goToSubcontractor() {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: this.subcontracting.partner_id,
            views: [[false, "form"]],
            target: "current",
            context: {
                active_id: this.subcontracting.partner_id,
            },
        });
    },

    //---- Getters ----

    get subcontracting() {
        return this.props.data.subcontracting || {};
    },
});
