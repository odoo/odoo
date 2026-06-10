import { Transition } from "@web/core/transition";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { usePos, usePosRouter } from "@point_of_sale/app/hooks/pos_hook";
import { Component, onMounted, useEffect } from "@odoo/owl";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { CustomerDisplayPosAdapter } from "@point_of_sale/app/customer_display/customer_display_adapter";
import { useIdleTimer } from "./utils/use_idle_timer";
import useTours from "./hooks/use_tours";
import { init as initDebugFormatters } from "./utils/debug-formatter";
import { debounce } from "@web/core/utils/timing";
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

        onMounted(this.props.disableLoader);

        this.customerDisplayAdapter = new CustomerDisplayPosAdapter();

        const debouncedDispatch = debounce((pos) => {
            this.customerDisplayAdapter.dispatch(pos);
        }, 100);

        useEffect(() => {
            const pos = this.pos;
            const routerState = this.router.state;
            const selectedOrder = pos.selectedOrder;

            if (routerState.current === "SaverScreen" || routerState.current === "LoginScreen") {
                this.customerDisplayAdapter.displayScreenSaver();
            } else if (selectedOrder) {
                this.customerDisplayAdapter.formatOrderData(selectedOrder);
            }
            this.customerDisplayAdapter.setExtraData(
                this.getCustomerDisplayExtraData(pos, routerState)
            );
            debouncedDispatch(pos);
        });
    }

    getCustomerDisplayExtraData(pos, routerState) {
        return {};
    }

    // GETTERS //
    get showCashMoveButton() {
        return Boolean(this.pos.config.cash_control);
    }
}
