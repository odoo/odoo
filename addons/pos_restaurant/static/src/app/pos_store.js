/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/pos_store";
import { PaymentScreen } from "@point_of_sale/js/Screens/PaymentScreen/PaymentScreen";
import { FloorScreen } from "@pos_restaurant/app/floor_screen/floor_screen";

const NON_IDLE_EVENTS = [
    "mousemove",
    "mousedown",
    "touchstart",
    "touchend",
    "touchmove",
    "click",
    "scroll",
    "keypress",
];
let IDLE_TIMER_SETTER;

patch(PosStore.prototype, "pos_restaurant.PosStore", {
    /**
     * @override
     */
    async setup() {
        await this._super(...arguments);
        if (this.globalState.config.module_pos_restaurant) {
            this.setActivityListeners();
            this.showScreen("FloorScreen", { floor: this.globalState.table?.floor || null });
            this.initTableOrderCount();
        }
    },

    async initTableOrderCount() {
        const result = await this.orm.call("pos.config", "get_tables_order_count", [
            this.globalState.config.id,
        ]);
        this.ws_syncTableCount(result);
    },

    // Will receive all messages coming from the server via
    // the websocket and dispatch them to the different utility functions.
    handleBusMessages(detail) {
        this._super(...arguments);
        console.debug("socketMessage", detail);
        if (detail.type === "TABLE_ORDER_COUNT") {
            this.ws_syncTableCount(detail.payload);
        } else if (detail.type === "TABLE_CHANGED") {
            this.ws_syncTableChanges(detail.payload);
        } else if (detail.type === "DISABLE_FLOOR") {
            this.ws_disableFloor(detail.payload);
        }
    },

    // Handles server bus messages of type `DISABLE_FLOOR`,
    // it will delete the floor and its tables.
    ws_disableFloor(data) {
        const floorId = data.id;
        const floor = this.globalState.floors_by_id[floorId];
        const orderList = [...this.globalState.get_order_list()];

        if (!floor) {
            return;
        }

        for (const order of orderList) {
            if (floor.table_ids.includes(order.tableId)) {
                this.globalState.removeOrder(order, false);
            }
        }

        delete this.globalState.floors_by_id[floorId];

        this.globalState.floors = this.globalState.floors.filter((floor) => floor.id != floorId);
        this.globalState.TICKET_SCREEN_STATE.syncedOrders.cache = {};
        this.globalState.isEditMode = false;
        this.globalState.floorPlanStyle = "default";
    },

    // Will fetch all the floors plan from the server when
    // an action message will be sent to it.
    async ws_syncTableChanges(data) {
        const newTable = data.changes;
        const floor = this.globalState.floors_by_id[newTable.floor_id];
        const table = floor.tables.find((table) => table.id === newTable.id);
        newTable.floor = floor;

        // Is a new table
        if (!table) {
            newTable.active = true;
            floor.tables.push(newTable);
        } else {
            if (!newTable.active) {
                table.active = false;
                return;
            }

            // Is a table update
            for (const key in table) {
                if (table[key] !== newTable[key]) {
                    console.debug(
                        `table ${table.id} changed ${key} from ${table[key]} to ${newTable[key]}`
                    );
                    table[key] = newTable[key];
                }
            }
        }
    },

    // Sync the number of orders on each table with other PoS
    // using the same floorplan.
    async ws_syncTableCount(data) {
        for (const table of data) {
            const table_obj = this.globalState.getTableById(table.id);
            if (table_obj) {
                table_obj.order_count = table.orders;
            }
        }
    },
    setActivityListeners() {
        IDLE_TIMER_SETTER = this.setIdleTimer.bind(this);
        for (const event of NON_IDLE_EVENTS) {
            window.addEventListener(event, IDLE_TIMER_SETTER);
        }
    },
    setIdleTimer() {
        clearTimeout(this.idleTimer);
        if (this.shouldResetIdleTimer()) {
            this.idleTimer = setTimeout(() => this.actionAfterIdle(), 60000);
        }
    },
    async actionAfterIdle() {
        const isPopupClosed = this.popup.closePopupsButError();
        if (isPopupClosed) {
            this.closeTempScreen();
            const { table } = this.globalState;
            const order = this.globalState.get_order();
            if (order && order.get_screen_data().name === "ReceiptScreen") {
                // When the order is finalized, we can safely remove it from the memory
                // We check that it's in ReceiptScreen because we want to keep the order if it's in a tipping state
                this.globalState.removeOrder(order);
            }
            this.showScreen("FloorScreen", { floor: table?.floor });
        }
    },
    shouldResetIdleTimer() {
        const stayPaymentScreen =
            this.mainScreen.component === PaymentScreen &&
            this.globalState.get_order().paymentlines.length > 0;
        return (
            this.globalState.config.module_pos_restaurant &&
            !stayPaymentScreen &&
            this.mainScreen.component !== FloorScreen
        );
    },
    showScreen(screenName) {
        if (screenName === "FloorScreen" && this.globalState.table) {
            this.globalState.unsetTable();
        }
        this._super(...arguments);
        this.setIdleTimer();
    },
    closeScreen() {
        if (this.globalState.config.module_pos_restaurant && !this.globalState.get_order()) {
            return this.showScreen("FloorScreen");
        }
        return this._super(...arguments);
    },
    /**
     * @override
     * Before closing pos, we remove the event listeners set on window
     * for detecting activities outside FloorScreen.
     */
    async closePos() {
        if (IDLE_TIMER_SETTER) {
            for (const event of NON_IDLE_EVENTS) {
                window.removeEventListener(event, IDLE_TIMER_SETTER);
            }
        }
        return this._super(...arguments);
    },
});
