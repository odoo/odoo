/** @odoo-module **/
import { Component, useState, onWillUnmount, useRef } from "@odoo/owl";
import { usePreparationDisplay } from "@pos_preparation_display/app/preparation_display_service";
import { Orderline } from "@pos_preparation_display/app/components/orderline/orderline";
import { computeFontColor } from "@pos_preparation_display/app/utils";

export class Order extends Component {
    static props = {
        order: Object,
    };

    setup() {
        this.preparationDisplay = usePreparationDisplay();
        this.orderlinesContainer = useRef("orderlines-container");
        this.state = useState({
            duration: 0,
            productHighlighted: [],
        });

        this.actionInProgress = false;
        this.state.duration = this._computeDuration();
        this.interval = setInterval(() => {
            this.state.duration = this._computeDuration();
        }, 1000);

        onWillUnmount(() => {
            clearInterval(this.interval);
        });
    }
    get stage() {
        const order = this.props.order;
        return this.preparationDisplay.stages.get(order.stageId);
    }

    get fondColor() {
        return computeFontColor(this.stage.color);
    }

    getSortedOrderlines() {
        return this.props.order.orderlines.sort(
            (a, b) =>
                this.preparationDisplay.categories[a.productCategoryIds[0]].sequence -
                this.preparationDisplay.categories[b.productCategoryIds[0]].sequence
        );
    }
    _computeDuration() {
        const timeDiff = this.props.order.computeDuration();

        if (timeDiff > this.stage.alertTimer) {
            this.isAlert = true;
        } else {
            this.isAlert = false;
        }

        return timeDiff;
    }

    async doneOrder() {
        if (this.props.order.stageId !== this.preparationDisplay.lastStage.id) {
            return;
        }

        this.props.order.displayed = false;
        this.preparationDisplay.doneOrders([this.props.order]);
    }

    get cardColor() {
        return "o_pdis_card_color_0";
    }

    async clickOrder() {
        if (this.actionInProgress) {
            return;
        }
        try {
            this.actionInProgress = true;
            const order = this.props.order;
            if (order.stageId === this.preparationDisplay.lastStage.id) {
                return;
            } else {
                await this.preparationDisplay.sendStrickedLineToNextStage(this.props.order);
            }
        } catch (error) {
            console.warn(error);
        } finally {
            this.actionInProgress = false;
        }
    }
}

Order.components = { Orderline };
Order.template = "pos_preparation_display.Order";
