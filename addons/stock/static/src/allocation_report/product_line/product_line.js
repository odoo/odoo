import { computed, props, types, Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

import { OutLine } from "../out_line/out_line";

export class ProductLine extends Component {
    static template = "stock.AllocationReport.ProductLine";
    static components = {
        OutLine,
    }

    props = props({
        freeQty: types.signal(types.number()),
        id: types.number(),
        name: types.string,
        needs: types.array(),
        totalQty: types.number(),
        uom: types.object(),
        sourceIds: types.array(),
        updateMoveReservation: types.function(),
    })

    displayViewMore = computed(() => {
        return this.props.needs.some((need) => need.hidden());
    })

    rowSpan = computed(() => {
        let visibleNeedsCount = 0;
        let hasHiddenNeeds = false;
        for (const need of this.props.needs) {
            if (!need.hidden()) {
                visibleNeedsCount += 1;
            } else if (!hasHiddenNeeds) {
                hasHiddenNeeds = true;
            }
        }
        return hasHiddenNeeds ? (visibleNeedsCount + 1) : visibleNeedsCount;
    })

    setup() {
        this.ormService = useService("orm");
        this.actionService = useService("action");
        const needs = this.props.needs;
        this.needs = needs.sort((needA, needB) => {
            const reservationA = needA.moves.some(move => move.is_reserved);
            const reservationB = needB.moves.some(move => move.is_reserved);
            return reservationB - reservationA;
        });
    }

    async updateMoveReservation(toReserve, outLine) {
        this.props.updateMoveReservation(toReserve, this.props.id, outLine);
    }

    getOutLineProps(outLine) {
        const props = {
            ...outLine,
            availableQuantity: this.props.freeQty(),
            moves: outLine.moves,
            productUom: this.props.uom,
            updateMoveReservation: this.updateMoveReservation.bind(this),
        };
        return props;
    }

    onClickViewMore() {
        let countToDisplay = 5;
        for (const outLine of this.props.needs) {
            if (outLine.hidden()) {
                outLine.hidden.set(false);
                countToDisplay--;
            }
            if (!countToDisplay) {
                break;
            }
        }
    }

    async onClickForecast() {
        const action = await this.ormService.call(
            "stock.move",
            "action_product_forecast_report",
            [[this.props.sourceIds[0]]],
        );

        return this.actionService.doAction(action);
    }
}
