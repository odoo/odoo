/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Component } from "@odoo/owl";

export class TakeAwayButton extends Component {
    static template = "pos_restaurant.TakeAwayButton";

    setup() {
        this.pos = usePos();
    }

    get currentOrder() {
        return this.pos.get_order();
    }

    click() {
        const isTakeAway = !this.currentOrder.take_away;
        const defaultFp = this.pos.config?.default_fiscal_position_id[0] ?? false;
        const fiscalPosition = this.pos.fiscal_positions.find(
            (fiscalPosition) =>
                fiscalPosition.id ===
                (isTakeAway ? this.pos.config.take_away_alternative_fp_id[0] : defaultFp)
        );

        this.currentOrder.take_away = isTakeAway;
        this.currentOrder.set_fiscal_position(fiscalPosition);
    }
}

ProductScreen.addControlButton({
    component: TakeAwayButton,
    condition: function () {
        return (
            this.pos.config.take_away &&
            this.pos.config.module_pos_restaurant &&
            this.pos.config.take_away_alternative_fp_id
        );
    },
});
