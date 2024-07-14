/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class QuickCheckIn extends Component {
    setup() {
        this.rpc = useService("rpc");
    }

    /**
     * Updates the planned visitor record in the backend
     *
     * @private
     * @param {Object} visitor
     */
    async _onClick(visitor) {
        await this.rpc(
            `/frontdesk/${this.props.stationId}/${this.props.token}/prepare_visitor_data`,
            {
                visitor_id: visitor.id,
            }
        );
        this.props.setPlannedVisitorData(visitor.id, visitor.message, visitor.host_ids);
        this.props.showScreen("RegisterPage");
    }
}

QuickCheckIn.template = "frontdesk.QuickCheckIn";
QuickCheckIn.props = {
    plannedVisitors: { type: Object, optional: true },
    setPlannedVisitorData: Function,
    showScreen: Function,
    token: String,
    stationId: Number,
    theme: String,
};
