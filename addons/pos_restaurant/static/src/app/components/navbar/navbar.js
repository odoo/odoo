import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { FloorPlanEditorNavBar } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/navbar/navbar";
import { useFloorPlanStore } from "@pos_restaurant/app/hooks/floor_plan_hook";

patch(Navbar.prototype, {
    setup() {
        super.setup();
        if (this.pos.config.module_pos_restaurant) {
            this.floorPlanStore = useFloorPlanStore();
        }
    },

    showTabs() {
        if (this.pos.config.module_pos_restaurant) {
            return !this.pos.selectedTable;
        } else {
            return super.showTabs();
        }
    },
    onSwitchButtonClick() {
        this.floorPlanStore?.toggleFloorPlanStyle();
    },
    get showEditPlanButton() {
        return this.pos.showEditPlanButton;
    },
    makeButtonBounce() {
        this.pos.shouldSetTable = true;
        setTimeout(() => (this.pos.shouldSetTable = false), 400);
    },
    canClick() {
        if (this.pos.getOrder()?.isFilledDirectSale) {
            this.makeButtonBounce();
            return false;
        }
        return true;
    },
    onTicketButtonClick() {
        return this.canClick() && this.pos.navigate("TicketScreen");
    },
    onClickPlanButton() {
        this.pos.getOrder()?.cleanCourses();
        return this.canClick() && this.pos.navigate("FloorScreen");
    },
    get mainButton() {
        return this.pos.router.state.current === "FloorScreen" ? "table" : super.mainButton;
    },
    get currentOrderName() {
        return this.pos.getOrder().getName().replace("T ", "");
    },
});

Navbar.components = { ...Navbar.components, FloorPlanEditorNavBar };
