import { Transition } from "@web/core/transition";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { usePos, usePosRouter } from "@point_of_sale/app/hooks/pos_hook";
import { Component, onMounted } from "@odoo/owl";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { useIdleTimer } from "./utils/use_idle_timer";
import useTours from "./hooks/use_tours";
import { init as initDebugFormatters } from "./utils/debug-formatter";
/**
 * Chrome is the root component of the PoS App.
 */
export class Chrome extends Component {
    static template = "point_of_sale.Chrome";
    static components = { Transition, MainComponentsContainer, Navbar };
    static props = { disableLoader: Function };
    setup() {
        this.pos = usePos();
        this.router = usePosRouter();
        useIdleTimer(this.pos.idleTimeout, (ev) => {
            const stopEventPropagation = ["mousedown", "click", "keypress"];
            if (stopEventPropagation.includes(ev.type)) {
                ev.stopPropagation();
            }
            this.pos.navigateToFirstPage();
            return false;
        });
        if (this.pos.router.state.current === "SaverScreen") {
            this.pos.navigateToFirstPage();
        }

        window.posmodel = this.pos;
        useOwnDebugContext();
        if (this.env.debug) {
            initDebugFormatters();
        }

        if (odoo.use_pos_fake_tours) {
            window.pos_fake_tour = useTours();
        }

        if (this.pos.config.iface_big_scrollbars) {
            const body = document.getElementsByTagName("body")[0];
            body.classList.add("big-scrollbars");
        }

        onMounted(() => {
            this.props.disableLoader();
            this.pos.debounceUpdateCustomerDisplay();
        });
    }
}
