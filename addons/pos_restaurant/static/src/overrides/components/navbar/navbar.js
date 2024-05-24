import { useEffect, useState } from "@odoo/owl";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { TipScreen } from "@pos_restaurant/app/tip_screen/tip_screen";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);
        this.state = useState({
            listPopup: false,
            arrowPopup: false,
        });

        useEffect(
            () => {
                const list = document.getElementsByClassName("shadow-table-list");
                if (!list || !this.pos.config.module_pos_restaurant) {
                    return;
                }

                const observer = new ResizeObserver((ev) => {
                    const target = ev[0].target;
                    if (target.scrollWidth > target.clientWidth + 10) {
                        this.state.arrowPopup = true;
                    } else {
                        this.state.arrowPopup = false;
                    }
                }).observe(list[0]);

                return () => {
                    observer.disconnect();
                };
            },
            () => []
        );
    },
    toggleOrderList() {
        this.state.listPopup = !this.state.listPopup;
    },
    async onClickBackButton() {
        if (this.pos.mainScreen.component && this.pos.config.module_pos_restaurant) {
            if (
                (this.pos.mainScreen.component === ProductScreen &&
                    this.pos.mobile_pane == "right") ||
                this.pos.mainScreen.component === TipScreen
            ) {
                this.pos.showScreen("FloorScreen", { floor: this.floor });
            } else {
                super.onClickBackButton(...arguments);
            }
            return;
        }
        super.onClickBackButton(...arguments);
    },
    /**
     * If no table is set to pos, which means the current main screen
     * is floor screen, then the order count should be based on all the orders.
     */
    get orderCount() {
        if (this.pos.config.module_pos_restaurant && this.pos.selectedTable) {
            return this.pos.getTableOrders(this.pos.selectedTable.id).length;
        }
        return super.orderCount;
    },
    onSwitchButtonClick() {
        const mode = this.pos.floorPlanStyle === "kanban" ? "default" : "kanban";
        localStorage.setItem("floorPlanStyle", mode);
        this.pos.floorPlanStyle = mode;
    },
    createOrderWithoutTable() {
        const order = this.pos.add_new_order();
        order.uiState.shadowTableName = order.tracking_number;
        this.selectedOrderUuid = order.uuid;
        this.pos.showScreen("ProductScreen");
    },
    get orderWithoutTable() {
        return this.pos.models["pos.order"].filter((o) => !o.table_id && !o.finalized);
    },
    onClickOrder(order) {
        this.pos.selectedOrderUuid = order.uuid;
        this.pos.showScreen("ProductScreen");
    },
});
