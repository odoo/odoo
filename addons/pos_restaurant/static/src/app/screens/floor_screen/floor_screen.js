import { Component, useEffect, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { FloorEditorToolBar } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/toolbar/toolbar";
import { NumpadDropdown } from "@pos_restaurant/app/components/numpad_dropdown/numpad_dropdown";
import { FloorPlan } from "@pos_restaurant/app/screens/floor_screen/floor_plan/floor_plan";
import { useFloorPlanStore } from "@pos_restaurant/app/hooks/floor_plan_hook";
import { FloorPlanEditor } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/floor_plan_editor";

export class FloorScreen extends Component {
    static template = "pos_restaurant.FloorScreen";
    static components = { NumpadDropdown, FloorEditorToolBar, FloorPlan, FloorPlanEditor };
    static props = {};
    static storeOnOrder = false;

    setup() {
        this.pos = usePos();
        this.floorPlanStore = useFloorPlanStore();
        this.ui = useService("ui");

        useEffect(
            (isEditMode) => {
                if (isEditMode) {
                    document.body.classList.add("o_fp_edit_mode");
                } else {
                    document.body.classList.remove("o_fp_edit_mode");
                }
            },
            () => [this.floorPlanStore.editMode]
        );

        onMounted(() => {
            this.pos.openOpeningControl();
            if (!this.pos.isOrderTransferMode) {
                this.resetTable();
            }
        });
    }

    async resetTable() {
        this.pos.searchProductWord = "";
        const table = this.pos.selectedTable;
        if (table) {
            await this.pos.unsetTable();
        }
        // Set order to null when reaching the floor screen.
        if (!(this.pos.getOrder()?.isFilledDirectSale && !this.pos.getOrder().finalized)) {
            this.pos.setOrder(null);
        }
    }

    startFloorPlanEditing() {
        this.floorPlanStore.startEditMode();
    }

    selectFloor(floorUuid) {
        this.floorPlanStore.selectFloorByUuid(floorUuid);
    }

    clickNewOrder() {
        this.pos.addNewOrder();
        this.pos.navigate("ProductScreen", {
            orderUuid: this.pos.selectedOrderUuid,
        });
    }

    toggleTableSelector() {
        this.pos.tableSelectorState = !this.pos.tableSelectorState;
    }

    isEditMode() {
        return this.floorPlanStore.editMode;
    }

    onToolbarTransitionEnd(e) {
        if (e.propertyName !== "opacity") {
            return;
        }
        if (!this.floorPlanStore.editMode) {
            this.floorPlanStore.showEditToolbar = false;
        }
    }

    initFloorPlanEditorActionHandler(actionHandler) {
        this.fpeActionHandler = actionHandler;
    }

    getFloorPlanEditorActionHandler() {
        return this.fpeActionHandler;
    }
}

registry.category("pos_pages").add("FloorScreen", {
    name: "FloorScreen",
    component: FloorScreen,
    route: `/pos/ui/${odoo.pos_config_id}/floor`,
    params: {},
});
