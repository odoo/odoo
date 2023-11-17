/** @odoo-module */

import { Transition } from "@web/core/transition";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { reactive, Component, onMounted, onWillStart } from "@odoo/owl";

/**
 * Chrome is the root component of the PoS App.
 */
export class Chrome extends Component {
    static template = "point_of_sale.Chrome";
    static components = { Transition, MainComponentsContainer, Navbar };
    static props = { disableLoader: Function };
    setup() {
        this.pos = usePos();
        const reactivePos = reactive(this.pos);
        // TODO: Should we continue on exposing posmodel as global variable?
        window.posmodel = reactivePos;

        // prevent backspace from performing a 'back' navigation
        document.addEventListener("keydown", (ev) => {
            if (ev.key === "Backspace" && !ev.target.matches("input, textarea")) {
                ev.preventDefault();
            }
        });

        onWillStart(this.pos._loadFonts);
        onMounted(this.props.disableLoader);
    }

    // GETTERS //

    get showCashMoveButton() {
        return Boolean(this.pos.config.cash_control);
    }
}
