import { Transition } from "@web/core/transition";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { reactive, Component, onMounted, onWillStart } from "@odoo/owl";
import { effect } from "@web/core/utils/reactive";
import { batched } from "@web/core/utils/timing";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { CustomerDisplayPosAdapter } from "@point_of_sale/app/customer_display/customer_display_adapter";
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

        const reactivePos = reactive(this.pos);
        window.posmodel = reactivePos;
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

        onWillStart(this.pos._loadFonts);
        onMounted(this.props.disableLoader);
        effect(
            batched(({ selectedOrder, scale }) => {
                if (selectedOrder) {
                    const scaleData = scale.product
                        ? {
                              product: { ...scale.product },
                              unitPrice: scale.unitPriceString,
                              totalPrice: scale.totalPriceString,
                              netWeight: scale.netWeightString,
                              grossWeight: scale.grossWeightString,
                              tare: scale.tareWeightString,
                          }
                        : null;
                    this.sendOrderToCustomerDisplay(selectedOrder, scaleData);
                }
            }),
            [this.pos]
        );
    }

    sendOrderToCustomerDisplay(selectedOrder, scaleData) {
        const adapter = new CustomerDisplayPosAdapter();
        adapter.formatOrderData(selectedOrder);
        adapter.data.scaleData = scaleData;
        adapter.dispatch(this.pos);
    }

    // GETTERS //
    get showCashMoveButton() {
        return Boolean(this.pos.config.cash_control);
    }
}
