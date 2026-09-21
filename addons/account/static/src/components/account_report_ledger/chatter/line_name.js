/** @odoo-module native */
import { AccountReportLineName } from "@account/components/account_report/line_name/line_name";
import { patch } from "@web/core/utils/patch";

patch(AccountReportLineName.prototype, {
    get isChatterAnnotated() {
        return this.props.line.visible_annotations;
    },

    get isChatterSelected() {
        return this.controller.chatterState.lineId === this.props.line.id;
    },

    async openChatter(ev) {
        ev.stopPropagation();

        if (!this.props.line.chatter) {
            return;
        }

        this.controller.toggleLineChatter({
            resModel: this.props.line.chatter.model,
            resId: this.props.line.chatter.id,
            line_id: this.props.line.id,
        });
    },
});
