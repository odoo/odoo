/** @odoo-module **/

import { Component } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

export class QuickCheckIn extends Component {
    static template = "frontdesk.QuickCheckIn";
    static props = {
        plannedVisitors: { type: Object, optional: true },
        setPlannedVisitorData: Function,
        showScreen: Function,
        token: String,
        stationId: Number,
        theme: String,
    };

    /**
     * Updates the planned visitor record in the backend
     *
     * @private
     * @param {Object} visitor
     */
    async _onClick(visitor) {
        await rpc(
            `/frontdesk/${this.props.stationId}/${this.props.token}/prepare_visitor_data`,
            {
                visitor_id: visitor.id,
            }
        );
        this.props.setPlannedVisitorData(visitor.id, visitor.message, visitor.host_ids);
        this.props.showScreen("RegisterPage");
    }
}
