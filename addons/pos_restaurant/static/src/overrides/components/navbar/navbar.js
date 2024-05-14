import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { TipScreen } from "@pos_restaurant/app/tip_screen/tip_screen";
import { patch } from "@web/core/utils/patch";
import { ListContainer } from "@point_of_sale/app/generic_components/list_container/list_container";
import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";
import { _t } from "@web/core/l10n/translation";

patch(Navbar, {
    components: { ...Navbar.components, ListContainer },
});
patch(Navbar.prototype, {
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
    get showTableIcon() {
        return this.pos.selectedTable?.name && this.pos.showBackButton();
    },
    onSwitchButtonClick() {
        const mode = this.pos.floorPlanStyle === "kanban" ? "default" : "kanban";
        localStorage.setItem("floorPlanStyle", mode);
        this.pos.floorPlanStyle = mode;
    },
    newFloatingOrder() {
        this.pos.add_new_order();
        this.pos.showScreen("ProductScreen");
    },
    getFloatingOrders() {
        return this.pos.get_order_list().filter((order) => !order.table_id);
    },
    selectFloatingOrder(order) {
        this.pos.set_order(order);
        this.pos.showScreen("ProductScreen");
    },
    editOrderNote(order) {
        this.dialog.add(TextInputPopup, {
            title: _t("Edit order note"),
            placeholder: _t("Emma's Birthday Party"),
            startingValue: order.note,
            getPayload: async (newName) => {
                if (typeof order.id == "number") {
                    this.pos.data.write("pos.order", [order.id], {
                        note: newName,
                    });
                } else {
                    order.note = newName;
                }
            },
        });
    },
    get showEditPlanButton() {
        return true;
    },
});
