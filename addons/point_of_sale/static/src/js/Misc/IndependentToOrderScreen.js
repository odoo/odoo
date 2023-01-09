/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";

class IndependentToOrderScreen extends PosComponent {
    close() {
        const order = this.env.pos.get_order();
        const { name: screenName } = order.get_screen_data();
        this.showScreen(screenName);
    }
}

export default IndependentToOrderScreen;
