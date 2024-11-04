import { Transition } from "@web/core/transition";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { reactive, Component, onMounted, onWillStart } from "@odoo/owl";
import { effect } from "@web/core/utils/reactive";
import { batched } from "@web/core/utils/timing";
import { deduceUrl } from "@point_of_sale/utils";
import { useOwnDebugContext } from "@web/core/debug/debug_context";

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
        this.customerDisplayChannel = new BroadcastChannel("UPDATE_CUSTOMER_DISPLAY");
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
                    if (
                        !selectedOrder &&
                        !scaleData &&
                        !scaleWeight &&
                        !scaleTare &&
                        !totalPriceOnScale &&
                        !isScaleScreenVisible
                    ) {
                        return;
                    }
                    this.sendOrderToCustomerDisplay(selectedOrder, scaleData);
                }
            ),
            [this.pos]
        );
    }

    sendOrderToCustomerDisplay(selectedOrder, scaleData) {
        const customerDisplayData = selectedOrder.getCustomerDisplayData();
        customerDisplayData.isScaleScreenVisible = this.pos.isScaleScreenVisible;
        if (scaleData) {
            customerDisplayData.scaleData = {
                productName: scaleData.productName,
                uomName: scaleData.uomName,
                uomRounding: scaleData.uomRounding,
                productPrice: scaleData.productPrice,
            };
        }
        customerDisplayData.weight = this.pos.scaleWeight;
        customerDisplayData.tare = this.pos.scaleTare;
        customerDisplayData.totalPriceOnScale = this.pos.totalPriceOnScale;

        if (this.pos.config.customer_display_type === "local") {
            this.customerDisplayChannel.postMessage(customerDisplayData);
        }
        if (this.pos.config.customer_display_type === "remote") {
            this.pos.data.call("pos.config", "update_customer_display", [
                [this.pos.config.id],
                customerDisplayData,
                this.pos.config.access_token,
            ]);
        }
        if (this.pos.config.customer_display_type === "proxy") {
            const proxyIP = this.pos.getDisplayDeviceIP();
            fetch(`${deduceUrl(proxyIP)}/hw_proxy/customer_facing_display`, {
                method: "POST",
                headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    params: {
                        action: "set",
                        data: customerDisplayData,
                    },
                }),
            }).catch(() => {
                console.log("Failed to send data to customer display");
            });
        }
    }

    // GETTERS //

    get showCashMoveButton() {
        return Boolean(this.pos.config.cash_control);
    }
}
