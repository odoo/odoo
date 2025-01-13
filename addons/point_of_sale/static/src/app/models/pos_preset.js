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
        const sqlDate = dateNow.toFormat("yyyy-MM-dd");
        return Object.values(this.uiState.availabilities[sqlDate]).find(
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

    computeAvailabilities(av) {
        this.generateSlots();

        if (av) {
            for (const [date, slots] of Object.entries(this.uiState.availabilities)) {
                for (const [datetime, slot] of Object.entries(slots)) {
                    const serverSlot = av[date][datetime];

                    slot.order_ids.forEach((orderId) => {
                        if (
                            !serverSlot.order_ids.includes(orderId) &&
                            !this.models["pos.order"].get(orderId)
                        ) {
                            slot.order_ids.delete(orderId);
                        }
                    });

                    slot.order_ids = new Set([...slot.order_ids, ...serverSlot.order_ids]);
                    slot.isFull = slot.order_ids.size >= this.slots_per_interval;
                }
            }
        }

        return this.uiState.availabilities;
    }

    get actualPreset() {
        const now = DateTime.now();
        const dayOfWeek = now.weekday - 1;
        const attToday = this.attendance_ids.filter((a) => a.dayofweek == dayOfWeek);
        if (attToday.length === 0) {
            return false;
        }
        for (const attendance of attToday) {
            const dateOpening = DateTime.fromObject({
                year: now.year,
                month: now.month,
                day: now.day,
                hour: Math.floor(attendance.hour_from),
                minute: (attendance.hour_from % 1) * 60,
            });
            const dateClosing = DateTime.fromObject({
                year: now.year,
                month: now.month,
                day: now.day,
                hour: Math.floor(attendance.hour_to),
                minute: (attendance.hour_to % 1) * 60,
            });
            if (dateOpening > now) {
                return false;
            }
            let start = dateOpening;
            while (start >= dateOpening && start <= dateClosing) {
                if (now > start && now < start.plus({ minutes: this.interval_time })) {
                    return { start: start, end: start.plus({ minutes: this.interval_time }) };
                }
                start = start.plus({ minutes: this.interval_time });
            }
        }
        return false;
    }

    generateSlots() {
        const usage = this.slotsUsage;
        const interval = this.interval_time;
        const slots = {};

        // Compute slots for next 7 days
        for (const i of [...Array(7).keys()]) {
            const dateNow = DateTime.now().plus({ days: i });
            const dayOfWeek = (dateNow.weekday - 1).toString();
            const date = DateTime.now().plus({ days: i }).toFormat("yyyy-MM-dd");
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
                    const sqlDatetime = start.toFormat("yyyy-MM-dd HH:mm:ss");

                    if (slots[date][sqlDatetime]) {
                        slots[date][sqlDatetime].order_ids.add(...(usage[sqlDatetime] || []));
                    } else {
                        slots[date][sqlDatetime] = {
                            periode: attendance.day_period,
                            datetime: start,
                            sql_datetime: sqlDatetime,
                            humain_readable: start.toFormat("HH:mm"),
                            order_ids: new Set(usage[sqlDatetime] || []),
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
