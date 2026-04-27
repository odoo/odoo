/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useInactivity } from "../use_inactivity";

export class DrinkPage extends Component {
    static template = "frontdesk.DrinkPage";
    static props = {
        drinkInfo: { type: Object, optional: true },
        setDrink: Function,
        showScreen: Function,
        stationId: Number,
        theme: String,
        token: String,
        visitorId: Number,
    };
    setup() {
        useInactivity(() => this.props.showScreen("EndPage"), 15000);
    }

    /**
     * Updates the visitor or planned visitor record in the backend
     *
     * @private
     */
    async _onDrinkSelect(drinkId) {
        await rpc(
            `/frontdesk/${this.props.stationId}/${this.props.token}/prepare_visitor_data`,
            {
                visitor_id: this.props.visitorId,
                drink_ids: [drinkId],
            }
        );
        this.props.setDrink(true);
        this.props.showScreen("EndPage");
    }
}

registry.category("frontdesk_screens").add("DrinkPage", DrinkPage);
