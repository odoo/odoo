/** @odoo-module **/
import { Reactive } from "@web/core/utils/reactive";

export class Stage extends Reactive {
    constructor({ id, name, color, alert_timer, sequence }, preparationDisplay) {
        super();

        this.id = id;
        this.name = name;
        this.color = color;
        this.alertTimer = alert_timer;
        this.sequence = sequence;
        this.preparationDisplay = preparationDisplay;
        this.orderCount = 0;
        this.recallIdsHistory = [];
    }

    addOrderToRecallHistory(id) {
        if (this.isLastHistoryOld()) {
            this.recallIdsHistory.length = 0;
        }
        this.recallIdsHistory.push(id);
        const previousStage = this.preparationDisplay.orderNextStage(this.id, -1);
        if (!previousStage) {
            return;
        }
        const previousHistoryOrderId = previousStage.recallIdsHistory.find((o) => o === id);
        if (previousHistoryOrderId) {
            previousStage.recallIdsHistory = previousStage.recallIdsHistory.filter(
                (o) => o !== previousHistoryOrderId
            );
        }
    }

    isLastHistoryOld() {
        const lastElement = this.recallIdsHistory[this.recallIdsHistory.length - 1];
        if (!lastElement) {
            return false;
        }
        const order = this.preparationDisplay.orders[lastElement];
        if (!order) {
            return true;
        }
        const lastDuration = order.computeDuration();
        if (lastDuration > 10) {
            return true;
        }
        return false;
    }
}
