import { registry } from "@web/core/registry";
import { Base } from "./related_models";

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

    computeAvailabilities(usages = {}) {
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

    get currentSlot() {
        const now = DateTime.now();
        const interval = this.interval_time;
        const todayAvailabilities = this.availabilities[now.toFormat("yyyy-MM-dd")];
        for (const slot of Object.values(todayAvailabilities)) {
            if (slot.datetime < now && slot.datetime.plus({ minutes: interval }) > now) {
                return slot;
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
            const getDateTime = (hour) =>
                DateTime.fromObject({
                    year: dateNow.year,
                    month: dateNow.month,
                    day: dateNow.day,
                    hour: Math.floor(hour),
                    minute: Math.round((hour % 1) * 60),
                });
            const dayOfWeek = (dateNow.weekday - 1).toString();
            const date = DateTime.now().plus({ days: i }).toFormat("yyyy-MM-dd");
            const attToday = this.attendance_ids.filter((a) => a.dayofweek === dayOfWeek);
            slots[date] = [];

            for (const attendance of attToday) {
                const dateOpening = getDateTime(attendance.hour_from);
                const dateClosing = getDateTime(attendance.hour_to);

                let start = dateOpening;
                while (start >= dateOpening && start <= dateClosing && interval > 0) {
                    const sqlDatetime = start.toFormat("yyyy-MM-dd HH:mm:ss");

                    if (slots[date][sqlDatetime]) {
                        slots[date][sqlDatetime].order_ids.add(...(usage[sqlDatetime] || []));
                    } else {
                        slots[date][sqlDatetime] = {
                            periode: attendance.day_period,
                            datetime: start,
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
