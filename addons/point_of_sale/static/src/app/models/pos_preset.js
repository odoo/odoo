import { registry } from "@web/core/registry";
import { range } from "@web/core/utils/numbers";
import { Base } from "./related_models";
import { serializeDate } from "@web/core/l10n/dates";
import { serializeLocalDateTime } from "@point_of_sale/utils";

const { DateTime } = luxon;

export class PosPreset extends Base {
    static pythonModel = "pos.preset";

    initState() {
        super.initState();
        this.uiState = {
            availabilities: {},
        };

        // This will compute availabilities locally
        // when selecting a preset it will be updated with the server data
        this.computeAvailabilities();
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
        const sqlDate = serializeDate(dateNow);
        return Object.values(this.uiState.availabilities[sqlDate]).find(
            (s) => !s.isFull && s.datetime > dateNow
        );
    }

    get availabilities() {
        return this.uiState.availabilities;
    }

    get slotsUsage() {
        return this.orders.reduce((acc, order) => {
            if (order.preset_time) {
                const sqlDatetime = serializeLocalDateTime(order.preset_time);

                if (!acc[sqlDatetime]) {
                    acc[sqlDatetime] = [];
                }

                acc[sqlDatetime].push(order.id);
            }
            return acc;
        }, {});
    }

    computeAvailabilities(usages = {}) {
        this.generateSlots();

        for (const [date, slots] of Object.entries(this.uiState.availabilities)) {
            for (const [datetime, slot] of Object.entries(slots)) {
                const usage = usages[datetime];
                slot.order_ids = new Set([...slot.order_ids, ...(usage || [])]);
                slot.isFull = slot.order_ids.size >= this.slots_per_interval;
            }

            this.uiState.availabilities[date] = Object.entries(slots).map(([time, slot]) => ({
                time,
                ...slot,
            }));
        }

        return this.uiState.availabilities;
    }

    get currentSlot() {
        const now = DateTime.now();
        const interval = this.interval_time;
        const todayAvailabilities = this.availabilities[serializeDate(now)];
        for (const slot of Object.values(todayAvailabilities)) {
            if (slot.datetime < now && slot.datetime.plus({ minutes: interval }) > now) {
                return slot;
            }
        }
        return false;
    }

    generateSlots() {
        const now = DateTime.now();
        const usage = this.slotsUsage;
        const interval = this.interval_time;
        const slots = {};

        // Compute slots for next 7 days
        for (const i of range(7)) {
            const dateNow = now.plus({ days: i });
            const getDateTime = (hour) =>
                DateTime.fromObject({
                    year: dateNow.year,
                    month: dateNow.month,
                    day: dateNow.day,
                    hour: Math.floor(hour),
                    minute: Math.round((hour % 1) * 60),
                });
            const dayOfWeek = (dateNow.weekday - 1).toString();
            const date = serializeDate(dateNow);
            const attToday = this.attendance_ids.filter((a) => a.dayofweek === dayOfWeek);
            slots[date] = [];

            for (const attendance of attToday) {
                const dateOpening = getDateTime(attendance.hour_from);
                const dateClosing = getDateTime(attendance.hour_to);

                let start = dateOpening;
                while (start >= dateOpening && start <= dateClosing && interval > 0) {
                    if (start >= now) {
                        const sqlDatetime = serializeLocalDateTime(start);
                        if (slots[date][sqlDatetime]) {
                            slots[date][sqlDatetime].order_ids.add(...(usage[sqlDatetime] || []));
                        } else {
                            slots[date][sqlDatetime] = {
                                periode: attendance.day_period,
                                datetime: start,
                                order_ids: new Set(usage[sqlDatetime] || []),
                            };
                        }
                    }
                    start = start.plus({ minutes: interval });
                }
            }
        }

        this.uiState.availabilities = slots;
    }
}

registry.category("pos_available_models").add(PosPreset.pythonModel, PosPreset);
