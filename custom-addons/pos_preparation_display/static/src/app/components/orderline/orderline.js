/** @odoo-module **/
import { Component } from "@odoo/owl";
import { usePreparationDisplay } from "@pos_preparation_display/app/preparation_display_service";
import { useService } from "@web/core/utils/hooks";

export class Orderline extends Component {
    static props = {
        orderline: Object,
    };

    setup() {
        this.preparationDisplay = usePreparationDisplay();
        this.orm = useService("orm");
    }

    get attributeData() {
        const attributeVal = this.preparationDisplay.attributeValues;
        const attributes = this.preparationDisplay.attributes;

        return Object.values(
            this.props.orderline.attribute_ids.reduce((acc, attr) => {
                const attributeValue = attributeVal.find((v) => v.id === attr);
                const attribute = attributes.find((a) => a.id === attributeValue.attribute_id[0]);

                if (acc[attribute.id]) {
                    acc[attribute.id].value += `, ${attributeValue.name}`;
                } else {
                    acc[attribute.id] = {
                        id: attr,
                        name: attribute.name,
                        value: attributeValue.name,
                    };
                }

                return acc;
            }, {})
        );
    }

    async changeOrderlineStatus() {
        const orderline = this.props.orderline;
        const newState = !orderline.todo;
        const order = this.props.orderline.order;

        orderline.todo = newState;
        if (order.stageId !== this.preparationDisplay.lastStage.id) {
            this.preparationDisplay.changeOrderStage(order);
        }
    }
}

Orderline.template = "pos_preparation_display.Orderline";
