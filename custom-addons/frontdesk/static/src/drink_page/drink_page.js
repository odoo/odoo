/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useInactivity } from "../use_inactivity";

export class DrinkPage extends Component {
    setup() {
        this.rpc = useService("rpc");
        useInactivity(() => this.props.showScreen("EndPage"), 15000);
    }

    /**
     * Updates the visitor or planned visitor record in the backend
     *
     * @private
     */
    async _onDrinkSelect(drinkId) {
        await this.rpc(
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

DrinkPage.template = "frontdesk.DrinkPage";
DrinkPage.props = {
    drinkInfo: { type: Object, optional: true },
    setDrink: Function,
    showScreen: Function,
    stationId: Number,
    theme: String,
    token: String,
    visitorId: Number,
};

registry.category("frontdesk_screens").add("DrinkPage", DrinkPage);
