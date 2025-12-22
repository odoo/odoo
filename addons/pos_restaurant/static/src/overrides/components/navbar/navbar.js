import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import {
    getButtons,
    EMPTY,
    ZERO,
    BACKSPACE,
} from "@point_of_sale/app/generic_components/numpad/numpad";
import { TableSelector } from "./table_selector/table_selector";

patch(Navbar.prototype, {
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
    get showEditPlanButton() {
        return true;
    },
    setFloatingOrder(floatingOrder) {
        this.pos.selectedTable = null;
        this.pos.set_order(floatingOrder);
        this.pos.showScreen("ProductScreen");
    },
    async onClickTableTab() {
        await this.pos.syncAllOrders();
        this.dialog.add(TableSelector, {
            title: _t("Table Selector"),
            placeholder: _t("Enter a table number"),
            buttons: getButtons([
                EMPTY,
                ZERO,
                { ...BACKSPACE, class: "o_colorlist_item_color_transparent_1" },
            ]),
            confirmButtonLabel: _t("Jump"),
            getPayload: async (table_number) => {
                const find_table = (t) => t.table_number === parseInt(table_number);
                const table =
                    this.pos.currentFloor?.table_ids.find(find_table) ||
                    this.pos.models["restaurant.table"].find(find_table);
                if (table) {
                    return this.pos.setTableFromUi(table);
                }
                const floating_order = this.pos
                    .get_open_orders()
                    .find((o) => o.getFloatingOrderName() === table_number);
                if (floating_order) {
                    return this.setFloatingOrder(floating_order);
                }
                if (!table && !floating_order) {
                    this.pos.selectedTable = null;
                    const newOrder = this.pos.add_new_order();
                    newOrder.floating_order_name = table_number;
                    newOrder.setBooked(true);
                    return this.setFloatingOrder(newOrder);
                }
            },
        });
    },
    onClickPlanButton() {
        this.pos.showScreen("FloorScreen", { floor: this.floor });
    },
});
