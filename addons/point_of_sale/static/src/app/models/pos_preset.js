import { registry } from "@web/core/registry";
import { Base } from "./related_models";

const { DateTime } = luxon;

export class PosPreset extends Base {
    static pythonModel = "pos.preset";

    setup() {
        super.setup(...arguments);

        this.uiState = {
            availabilities: {},
        };
    }

    get orders() {
        return this.models["pos.order"].filter((o) => o.preset_id?.id === this.id);
    }

    get nextSlot() {
        const dateNow = DateTime.now();
        return Object.values(this.uiState.availabilities).find(
            (s) => s.order_ids.size < this.capacity_per_x_minutes && s.datetime > dateNow
        );
    }

    get availabilities() {
        const dateNow = DateTime.now();
        return Object.values(this.uiState.availabilities).filter(
            (s) => s.order_ids.size < this.capacity_per_x_minutes && s.datetime > dateNow
        );
    }

    get slotsUsage() {
        return (
            this.orders.reduce((acc, order) => {
                if (!acc[order.preset_time]) {
                    acc[order.preset_time] = [];
                }

                acc[order.preset_time].push(order.id);
                return acc;
            }, {}) || {}
        );
    }

    generateSlots() {
        const usage = this.slotsUsage;
        const interval = this.x_minutes;
        const dateTimeOpening = DateTime.fromSQL(this.hour_opening);
        const dateTimeClosing = DateTime.fromSQL(this.hour_closing);
        const slots = {};

        let start = dateTimeOpening;
        let keeper = 0;
        while (start <= dateTimeClosing && start >= dateTimeOpening) {
            const sqlDatetime = start.toFormat("yyyy-MM-dd HH:mm:ss");

            if (slots[sqlDatetime]) {
                slots[sqlDatetime].order_ids.add(...(usage[sqlDatetime] || []));
            } else {
                slots[sqlDatetime] = {
                    datetime: start,
                    sql_datetime: sqlDatetime,
                    humain_readable: start.toFormat("HH:mm"),
                    order_ids: new Set(usage[sqlDatetime] || []),
                };
            }

            start = start.plus({ minutes: interval });
            keeper += 1;
            if (keeper > 1000) {
                break;
            }
        }

        this.uiState.availabilities = slots;
    }
}

registry.category("pos_available_models").add(PosPreset.pythonModel, PosPreset);
