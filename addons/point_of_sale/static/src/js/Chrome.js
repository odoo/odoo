/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { batched } from "@point_of_sale/js/utils";
import { throttleForAnimation } from "@web/core/utils/timing";
import { Transition } from "@web/core/transition";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { ErrorHandler } from "@web/core/utils/components";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { usePos } from "@point_of_sale/app/pos_hook";
import {
    useExternalListener,
    useSubEnv,
    reactive,
    onWillUnmount,
    Component,
    onMounted,
} from "@odoo/owl";

/**
 * Chrome is the root component of the PoS App.
 */
export class Chrome extends Component {
    static template = "Chrome"; // FIXME POSREF namespace templates
    static components = { Transition, MainComponentsContainer, ErrorHandler, Navbar };
    static props = { disableLoader: Function };
    setup() {
        this.pos = usePos();
        this.popup = useService("popup");

        const reactivePos = reactive(this.pos.globalState);
        // TODO: Should we continue on exposing posmodel as global variable?
        window.posmodel = reactivePos;
        // FIXME POSREF: remove
        useSubEnv({
            get isMobile() {
                return window.innerWidth <= 768;
            },
            pos: reactive(
                reactivePos,
                batched(() => this.render(true)) // FIXME POSREF remove render(true)
            ),
        });
        let currentIsMobile = this.env.isMobile;
        const updateUI = throttleForAnimation(() => {
            if (this.env.isMobile !== currentIsMobile) {
                currentIsMobile = this.env.isMobile;
                // FIXME POSREF
                this.render(true);
            }
        });
        useExternalListener(window, "resize", updateUI);
        onWillUnmount(updateUI.cancel);

        // prevent backspace from performing a 'back' navigation
        document.addEventListener("keydown", (ev) => {
            if (ev.key === "Backspace" && !ev.target.matches("input, textarea")) {
                ev.preventDefault();
            }
        });

        onMounted(this.props.disableLoader);
    }

    // GETTERS //

    get showCashMoveButton() {
        return Boolean(this.pos.globalState?.config?.cash_control);
    }
    /**
     * Unmounts the tempScreen on error and dispatches the error in a separate
     * stack so that it can be handled by the error service and display an error
     * popup.
     *
     * @param {any} err the error that was thrown in the temp screen.
     */
    onTempScreenError(err) {
        this.pos.tempScreen = null;
        Promise.reject(err);
    }
}
