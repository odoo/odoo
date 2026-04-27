import { Category } from "@pos_preparation_display/app/components/category/category";
import { Stages } from "@pos_preparation_display/app/components/stages/stages";
import { Order } from "@pos_preparation_display/app/components/order/order";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { usePreparationDisplay } from "@pos_preparation_display/app/preparation_display_service";
import { Component, onPatched, useState, whenReady } from "@odoo/owl";
import { mountComponent } from "@web/env";

export class PreparationDisplay extends Component {
    static components = { Category, Stages, Order, MainComponentsContainer };
    static template = `pos_preparation_display.PreparationDisplay`;
    static props = {};

    setup() {
        this.preparationDisplay = usePreparationDisplay();
        this.displayName = odoo.preparation_display.name;
        this.showSidebar = true;
        this.onNextPatch = new Set();
        this.state = useState({
            isMenuOpened: false,
        });

        onPatched(() => {
            for (const cb of this.onNextPatch) {
                cb();
            }
        });
    }
    get filterSelected() {
        return (
            this.preparationDisplay.selectedCategories.size +
            this.preparationDisplay.selectedProducts.size
        );
    }
    archiveAllVisibleOrders() {
        const lastStageVisibleOrderIds = this.preparationDisplay.filteredOrders.filter(
            (order) => order.stageId === this.preparationDisplay.lastStage.id
        );

        for (const order of lastStageVisibleOrderIds) {
            order.displayed = false;
        }

        this.preparationDisplay.doneOrders(lastStageVisibleOrderIds);
        this.preparationDisplay.filterOrders();
    }
    resetFilter() {
        this.preparationDisplay.selectedCategories = new Set();
        this.preparationDisplay.selectedProducts = new Set();
        this.preparationDisplay.filterOrders();
        this.preparationDisplay.saveFilterToLocalStorage();
    }
    toggleCategoryFilter() {
        this.preparationDisplay.showCategoryFilter = !this.preparationDisplay.showCategoryFilter;
    }
    recallLastChange() {
        const stageId = this.preparationDisplay.selectedStageId;
        const stage = this.preparationDisplay.stages.get(stageId);
        const recallHistory = stage.recallIdsHistory;
        if (recallHistory.length === 0) {
            return;
        } else if (stage.isLastHistoryOld()) {
            recallHistory.length = 0;
            return;
        }
        const lastIdChange = recallHistory.pop();
        const order = this.preparationDisplay.orders[lastIdChange];
        const nextStage = this.preparationDisplay.orderNextStage(stageId);
        if (order.stageId === nextStage.id) {
            this.preparationDisplay.changeOrderStage(order, true, -1, 0);
        } else {
            this.recallLastChange();
        }
    }
    isHistoryEmpty() {
        return (
            this.preparationDisplay.stages.get(this.preparationDisplay.selectedStageId)
                .recallIdsHistory.length == 0
        );
    }
    isBurgerMenuClosed() {
        return !this.state.isMenuOpened;
    }
    closeMenu() {
        this.state.isMenuOpened = false;
    }
    openMenu() {
        this.state.isMenuOpened = true;
    }
}
whenReady(() => mountComponent(PreparationDisplay, document.body));
