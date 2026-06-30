import { Transition } from "@web/core/transition";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { usePos, usePosRouter } from "@point_of_sale/app/hooks/pos_hook";
import { Component, onMounted, useEffect, props, t } from "@odoo/owl";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { CustomerDisplayPosAdapter } from "@point_of_sale/app/customer_display/customer_display_adapter";
import { useIdleTimer } from "./utils/use_idle_timer";
import useTours from "./hooks/use_tours";
import { init as initDebugFormatters } from "./utils/debug-formatter";
import { debounce } from "@web/core/utils/timing";
import { getColorScheme } from "@point_of_sale/utils";
/**
 * Chrome is the root component of the PoS App.
 */
export class Chrome extends Component {
    static template = "point_of_sale.Chrome";
    static components = { Transition, MainComponentsContainer, Navbar };
    props = props({ disableLoader: t.function() });
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

        this.adapter = new CustomerDisplayPosAdapter();
        this.dispatchDebounced = debounce(() => this.adapter.dispatch(this.pos));

        useEffect(() => {
            this.sendOrderToCustomerDisplay(this.pos, this.router.state);
        });
    }

    sendOrderToCustomerDisplay({ selectedOrder }, routerState) {
        if (routerState.current === "SaverScreen" || routerState.current === "LoginScreen") {
            this.adapter.displayScreenSaver();
        } else if (selectedOrder) {
            this.adapter.formatOrderData(selectedOrder);
        }
        this.adapter.setExtraData(this.getCustomerDisplayExtraData(...arguments));
        this.dispatchDebounced();
    }

    getCustomerDisplayExtraData(pos, routerState) {
        return {
            displayTheme: getColorScheme(),
        };
    }

    // GETTERS //
    get showCashMoveButton() {
        return Boolean(this.pos.config.cash_control);
    }
}
