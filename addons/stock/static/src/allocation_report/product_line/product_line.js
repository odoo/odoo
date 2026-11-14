import { computed, useProps, types, Component, usePlugin } from "@odoo/owl";

import { OutLine } from "../out_line/out_line";
import { ORM } from "@web/core/orm_plugin";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";

export class ProductLine extends Component {
    static template = "stock.AllocationReport.ProductLine";
    static components = {
        OutLine,
    }

    props = useProps({
        freeQty: types.signal(types.number()),
        id: types.number(),
        isSmall: types.boolean().optional(),
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
        this.ormService = usePlugin(ORM);
        this.actionService = usePlugin(ActionPlugin);
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
