import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import {
    getButtons,
    DECIMAL,
    ZERO,
    BACKSPACE,
} from "@point_of_sale/app/generic_components/numpad/numpad";
import { FloorScreen } from "@pos_restaurant/app/floor_screen/floor_screen";

patch(Navbar.prototype, {
    onClickPlanButton() {
        if (this.pos.config.module_pos_restaurant) {
            this.pos.showScreen("FloorScreen", { floor: this.floor });
        }
    },
    isFloorScreenActive() {
        return this.pos.mainScreen.component && this.pos.mainScreen.component === FloorScreen;
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
    getTable() {
        return this.pos.orderToTransferUuid
            ? this.pos.models["pos.order"].find((o) => o.uuid == this.pos.orderToTransferUuid)
                  ?.table_id
            : this.pos.selectedTable;
    },
    showTabs() {
        return !this.pos.selectedTable;
    },
    get showTableNumber() {
        return typeof this.getTable()?.table_number === "number";
    },
    get showSwitchTableButton() {
        return this.pos.mainScreen.component.name === "FloorScreen";
    },
    onSwitchButtonClick() {
        const mode = this.pos.floorPlanStyle === "kanban" ? "default" : "kanban";
        localStorage.setItem("floorPlanStyle", mode);
        this.pos.floorPlanStyle = mode;
    },
    get showEditPlanButton() {
        return true;
    },
    async switchTable() {
        const table_number = await makeAwaitable(this.dialog, NumberPopup, {
            title: _t("Table Selector"),
            placeholder: _t("Enter a table number"),
            buttons: getButtons([{ ...DECIMAL, disabled: true }, ZERO, BACKSPACE]),
            defaultPayload: { value: null },
        });
        if (!table_number) {
            return;
        }
        const find_table = (t) => t.table_number === parseInt(table_number);
        let table = this.pos.currentFloor?.table_ids.find(find_table);
        if (!table) {
            table = this.pos.models["restaurant.table"].find(find_table);
        }
        let floating_order;
        if (!table) {
            floating_order = this.getFloatingOrders().find(
                (o) => o.getFloatingOrderName() === table_number
            );
        }
        if (!table && !floating_order) {
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t("No table or floating order found with this number"),
            });
            return;
        }
        this.pos.selectedTable = null;
        this.pos.searchProductWord = "";
        if (table) {
            await this.pos.setTableFromUi(table);
        } else {
            this.selectFloatingOrder(floating_order);
        }
    },
    getFloatingOrders() {
        const result = super.getFloatingOrders();
        return result.filter((o) => !o.table_id);
    },
});
