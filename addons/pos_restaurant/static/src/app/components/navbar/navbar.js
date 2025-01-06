import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";

patch(Navbar.prototype, {
    showTabs() {
        if (this.pos.config.module_pos_restaurant) {
            return !this.pos.selectedTable;
        } else {
            return super.showTabs();
        }
    },
    onSwitchButtonClick() {
        const mode = this.pos.floorPlanStyle === "kanban" ? "default" : "kanban";
        localStorage.setItem("floorPlanStyle", mode);
        this.pos.floorPlanStyle = mode;
    },
    get showEditPlanButton() {
        return true;
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
        return this.canClick() && this.pos.showScreen("TicketScreen");
    },
    onClickPlanButton() {
        return this.canClick() && this.pos.showScreen("FloorScreen");
    },
    get mainButton() {
        return this.pos.mainScreen.component.name === "FloorScreen" ? "table" : super.mainButton;
    },
});
