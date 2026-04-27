import { Reactive } from "@web/core/utils/reactive";
import { deserializeDateTime } from "@web/core/l10n/dates";

export class Order extends Reactive {
    constructor({
        id,
        stage_id,
        generalNote,
        displayed,
        responsible,
        orderlines,
        create_date,
        last_stage_change,
        pos_order_id,
        customer_count,
        tracking_number,
    }) {
        super();
        this.setup(...arguments);
    }

    setup(order) {
        this.id = order.id;
        this.stageId = order.stage_id;
        this.generalNote = order.generalNote;
        this.displayed = order.displayed;
        this.responsible = order.responsible;
        this.orderlines = order.orderlines;
        this.createDate = order.create_date;
        this.lastStageChange = order.last_stage_change;
        this.posOrderId = order.pos_order_id;
        this.customer_count = order.customer_count;
        this.changeStageTimeout = null;
        this.tracking_number = order.tracking_number;
    }

    clearChangeTimeout() {
        clearTimeout(this.changeStageTimeout);
        this.changeStageTimeout = null;
    }

    computeDuration() {
        const timeDiff = (
            (luxon.DateTime.now().ts - deserializeDateTime(this.lastStageChange).ts) /
            1000
        ).toFixed(0);
        return Math.round(timeDiff / 60);
    }
}
