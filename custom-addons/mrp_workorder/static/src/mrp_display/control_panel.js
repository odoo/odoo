/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";

export class ControlPanelButtons extends Component {
    static template = "mrp_workorder.ControlPanelButtons";
    static props = {
        activeWorkcenter: [Boolean, Number],
        productionCount: Number,
        selectWorkcenter: Function,
        toggleWorkcenter: Function,
        workcenters: Array,
        workorders: Array,
        relevantCount: Number,
        adminWorkorders: Array,
        hideNewWorkcenterButton: Boolean,
    };

    get workcenterButtons() {
        const workcenterButtons = {};
        let productionCount = this.props.productionCount;
        let adminCount = 0;
        for (const { id, display_name } of this.props.workcenters) {
            workcenterButtons[id] = { count: 0, name: display_name };
        }
        for (const workorder of this.props.workorders) {
            if (workorder.data.state == 'cancel') continue;
            const button = workcenterButtons[workorder.data.workcenter_id[0]];
            if (button) {
                button.count++;
            }
            if (this.props.adminWorkorders.includes(workorder.resId)) {
                adminCount++;
            }
        }
        if (this.props.activeWorkcenter > 0 && workcenterButtons[this.props.activeWorkcenter]) {
            workcenterButtons[this.props.activeWorkcenter].count = this.props.relevantCount;
        } else if (this.props.activeWorkcenter === 0) {
            productionCount = this.props.relevantCount;
        } else if (this.props.activeWorkcenter === -1) {
            adminCount = this.props.relevantCount;
        }
        return [
            ["0", { count: productionCount, name: _t("All MO") }],
            ["-1", { count: adminCount, name: _t("My WO") }],
            ...this.props.workcenters.map((wc) => [String(wc.id), workcenterButtons[wc.id]]),
        ];
    }
}
