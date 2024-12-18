import { Transition } from "@web/core/transition";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { reactive, Component, onMounted, onWillStart } from "@odoo/owl";
import { effect } from "@web/core/utils/reactive";
import { batched } from "@web/core/utils/timing";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { CustomerDisplayPosAdapter } from "@point_of_sale/customer_display/customer_display_adapter";

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
        useOwnDebugContext();

        // prevent backspace from performing a 'back' navigation
        document.addEventListener("keydown", (ev) => {
            if (ev.key === "Backspace" && !ev.target.matches("input, textarea")) {
                ev.preventDefault();
            }
        });

        if (this.pos.config.iface_big_scrollbars) {
            const body = document.getElementsByTagName("body")[0];
            body.classList.add("big-scrollbars");
        }

        onWillStart(this.pos._loadFonts);
        onMounted(this.props.disableLoader);
        if (this.pos.config.customer_display_type === "none") {
            return;
        }
        effect(
            batched(
                ({
                    selectedOrder,
                    scaleData,
                    scaleWeight,
                    scaleTare,
                    totalPriceOnScale,
                    isScaleScreenVisible,
                }) => {
                    if (selectedOrder) {
                        const allScaleData = {
                            ...scaleData,
                            weight: scaleWeight,
                            tare: scaleTare,
                            totalPriceOnScale,
                            isScaleScreenVisible,
                        };
                        this.sendOrderToCustomerDisplay(selectedOrder, allScaleData);
                    }
                }
            ),
            [this.pos]
        );
    }

    sendOrderToCustomerDisplay(selectedOrder, scaleData) {
        const adapter = new CustomerDisplayPosAdapter();
        adapter.formatOrderData(selectedOrder);
        adapter.addScaleData(scaleData);
        adapter.data.weight = scaleData.weight;
        adapter.data.tare = scaleData.tare;
        adapter.data.totalPriceOnScale = scaleData.totalPriceOnScale;
        adapter.dispatch(this.pos);
    }

    // GETTERS //
    get showCashMoveButton() {
        return Boolean(this.pos.config.cash_control);
    }
}
