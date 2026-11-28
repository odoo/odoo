/** @odoo-module **/

export class GanttModel {
    constructor(orm, resModel, archInfo) {
        this.orm = orm;
        this.resModel = resModel;
        this.archInfo = archInfo;

        this.currentDate = new Date();
        this.scale = archInfo.defaultScale || "week";
        this.domain = [];
        this.searchDomain = [];

        this.loading = false;
        this.todayStr = this.formatDateISO(new Date());

        this.openShifts = { total_hours: 0, hours_label: "", slots: [] };
        this.resources = [];
        this.slots = [];
        this.toScheduleCount = 0;
        this.days = [];
    }

    formatDateISO(d) {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, "0");
        const day = String(d.getDate()).padStart(2, "0");
        return `${y}-${m}-${day}`;
    }

    getWeekBounds(baseDate) {
        // Week starts on Sunday and ends on Saturday (matching target Planning Gantt)
        const d = new Date(baseDate);
        const dayOfWeek = d.getDay(); // 0 is Sunday, 1 is Monday ... 6 is Saturday
        const sunday = new Date(d);
        sunday.setDate(d.getDate() - dayOfWeek);
        sunday.setHours(0, 0, 0, 0);

        const saturday = new Date(sunday);
        saturday.setDate(sunday.getDate() + 6);
        saturday.setHours(23, 59, 59, 999);

        return {
            start: this.formatDateISO(sunday),
            end: this.formatDateISO(saturday),
            startDate: sunday,
            endDate: saturday,
        };
    }

    getWeekNumber(d) {
        const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
        const dayNum = date.getUTCDay() || 7;
        date.setUTCDate(date.getUTCDate() + 4 - dayNum);
        const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
        return Math.ceil(((date - yearStart) / 86400000 + 1) / 7);
    }

    get rangeLabel() {
        const bounds = this.getWeekBounds(this.currentDate);
        const s = bounds.startDate;
        const e = bounds.endDate;
        const weekNum = this.getWeekNumber(s);
        const sMonth = s.toLocaleDateString("en-US", { month: "short" });
        const eMonth = e.toLocaleDateString("en-US", { month: "short" });
        const sDay = s.getDate();
        const eDay = e.getDate();

        if (sMonth === eMonth) {
            return `Week ${weekNum} · ${sMonth} ${sDay} - ${sMonth} ${eDay}`;
        } else {
            return `Week ${weekNum} · ${sMonth} ${sDay} - ${eMonth} ${eDay}`;
        }
    }

    computeDays() {
        const bounds = this.getWeekBounds(this.currentDate);
        const days = [];
        const curr = new Date(bounds.startDate);

        for (let i = 0; i < 7; i++) {
            const dateStr = this.formatDateISO(curr);
            const isToday = (dateStr === this.todayStr);
            days.push({
                date: new Date(curr),
                dateStr: dateStr,
                dayName: curr.toLocaleDateString("en-US", { weekday: "long" }),
                dayShort: curr.toLocaleDateString("en-US", { weekday: "short" }),
                dayNumber: curr.getDate(),
                isToday: isToday,
                isWeekend: (i === 0 || i === 6),
            });
            curr.setDate(curr.getDate() + 1);
        }
        this.days = days;
    }

    async load(domain = []) {
        this.loading = true;
        this.searchDomain = domain || [];
        this.computeDays();

        const bounds = this.getWeekBounds(this.currentDate);
        try {
            const res = await this.orm.call(
                this.resModel,
                "get_gantt_data",
                [bounds.start, bounds.end, this.searchDomain]
            );

            if (res) {
                this.todayStr = res.today || this.formatDateISO(new Date());
                this.openShifts = res.open_shifts || { total_hours: 0, hours_label: "", slots: [] };
                this.resources = res.resources || [];
                this.slots = res.slots || [];
                this.toScheduleCount = res.to_schedule_count || 0;
            }
        } catch (err) {
            console.error("Failed to load Gantt data:", err);
        } finally {
            this.loading = false;
        }
    }

    prev() {
        const d = new Date(this.currentDate);
        d.setDate(d.getDate() - 7);
        this.currentDate = d;
        return this.load(this.searchDomain);
    }

    next() {
        const d = new Date(this.currentDate);
        d.setDate(d.getDate() + 7);
        this.currentDate = d;
        return this.load(this.searchDomain);
    }

    today() {
        this.currentDate = new Date();
        return this.load(this.searchDomain);
    }

    async publishWeek() {
        const bounds = this.getWeekBounds(this.currentDate);
        const res = await this.orm.call(
            this.resModel,
            "action_publish_week_shifts",
            [bounds.start, bounds.end]
        );
        await this.load(this.searchDomain);
        return res;
    }

    async copyPreviousWeek() {
        const bounds = this.getWeekBounds(this.currentDate);
        const res = await this.orm.call(
            this.resModel,
            "action_copy_previous_week_shifts",
            [bounds.start]
        );
        await this.load(this.searchDomain);
        return res;
    }
}
