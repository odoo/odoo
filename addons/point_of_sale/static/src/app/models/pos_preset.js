import { registry } from "@web/core/registry";
import { Base } from "./related_models";
import { localization } from "@web/core/l10n/localization";

const { DateTime } = luxon;

export class PosPreset extends Base {
    static pythonModel = "pos.preset";

    setup() {
        super.setup(...arguments);

        this.uiState = {
            availabilities: {},
        };
    }

    get needsSlot() {
        return this.use_timing;
    }

    get needsName() {
        return this.identification === "name";
    }

    get needsPartner() {
        return this.identification === "address";
    }

    get orders() {
        return this.models["pos.order"].filter((o) => o.preset_id?.id === this.id);
    }

    get nextSlot() {
        const dateNow = DateTime.now();
        const formattedDate = dateNow.toFormat(localization.dateFormat);
        return Object.values(this.uiState.availabilities[formattedDate]).find(
            (s) => !s.isFull && s.datetime > dateNow
        );
    }

    get availabilities() {
        return this.uiState.availabilities;
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

    computeAvailabilities(usages) {
        this.generateSlots();

        const allSlots = Object.values(this.uiState.availabilities).reduce(
            (acc, curr) => Object.assign(acc, curr),
            {}
        );

        for (const [datetime, slot] of Object.entries(allSlots)) {
            const usage = usages[datetime];
            slot.order_ids = new Set([...slot.order_ids, ...(usage || [])]);
            slot.isFull = slot.order_ids.size >= this.slots_per_interval;
        }

        return this.uiState.availabilities;
    }

    generateSlots() {
        const usage = this.slotsUsage;
        const interval = this.interval_time;
        const slots = {};

        // Compute slots for next 7 days
        for (const i of [...Array(7).keys()]) {
            const dateNow = DateTime.now().plus({ days: i });
            const dayOfWeek = (dateNow.weekday - 1).toString();
            const date = DateTime.now().plus({ days: i }).toFormat(localization.dateFormat);
            const attToday = this.attendance_ids.filter((a) => a.dayofweek === dayOfWeek);
            slots[date] = [];

            for (const attendance of attToday) {
                const dateOpening = DateTime.fromObject({
                    year: dateNow.year,
                    month: dateNow.month,
                    day: dateNow.day,
                    hour: Math.floor(attendance.hour_from),
                    minute: (attendance.hour_from % 1) * 60,
                });
                const dateClosing = DateTime.fromObject({
                    year: dateNow.year,
                    month: dateNow.month,
                    day: dateNow.day,
                    hour: Math.floor(attendance.hour_to),
                    minute: (attendance.hour_to % 1) * 60,
                });

                let start = dateOpening;
                while (start >= dateOpening && start <= dateClosing && interval > 0) {
                    const formattedDateTime = start.toFormat(localization.dateTimeFormat);

                    if (slots[date][formattedDateTime]) {
                        slots[date][formattedDateTime].order_ids.add(
                            ...(usage[formattedDateTime] || [])
                        );
                    } else {
                        slots[date][formattedDateTime] = {
                            periode: attendance.day_period,
                            datetime: start,
                            order_ids: new Set(usage[formattedDateTime] || []),
                        };
                    }

                    start = start.plus({ minutes: interval });
                }
            }
        }

        this.uiState.availabilities = slots;
    }
}

registry.category("pos_available_models").add(PosPreset.pythonModel, PosPreset);
