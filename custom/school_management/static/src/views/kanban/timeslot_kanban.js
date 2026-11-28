/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { _t } from "@web/core/l10n/translation";

export class TimeslotKanbanController extends KanbanController {
    setup() {
        super.setup(...arguments);
        const displayName = this.env.config.getDisplayName ? this.env.config.getDisplayName() : this.env.config.displayName;
        if (!displayName || displayName === "New" || displayName === _t("New")) {
            this.env.config.setDisplayName("Timeslots");
        }
    }
}

export class TimeslotKanbanRenderer extends KanbanRenderer {
    static template = "school_management.TimeslotKanbanRenderer";

    formatHour(value) {
        if (value === undefined || value === null || isNaN(value)) {
            return "00:00";
        }
        let h = Math.floor(value);
        let m = Math.round((value - h) * 60);
        if (m === 60) {
            h += 1;
            m = 0;
        }
        const hh = String(h).padStart(2, "0");
        const mm = String(m).padStart(2, "0");
        return `${hh}:${mm}`;
    }

    get timeslotColumns() {
        const list = this.props.list;
        if (!list) {
            return [];
        }

        // Handle grouped view
        const groups = list.isGrouped ? (list.groups || []) : [];
        const validGroups = groups
            .filter((g) => g.count > 0 && g.list && g.list.records && g.list.records.length > 0)
            .sort((a, b) => {
                const vA = parseInt(a.value ?? "99", 10);
                const vB = parseInt(b.value ?? "99", 10);
                return vA - vB;
            });

        // Compute median and max session counts across all visible records
        const allRecords = validGroups.flatMap((g) => g.list.records);
        const counts = allRecords
            .map((r) => r.data.slot_count || 0)
            .sort((a, b) => a - b);

        let median = 0;
        if (counts.length > 0) {
            const mid = Math.floor(counts.length / 2);
            median = counts.length % 2 !== 0 ? counts[mid] : (counts[mid - 1] + counts[mid]) / 2;
        }
        const maxSessions = counts.length > 0 ? Math.max(...counts, 1) : 1;

        return validGroups.map((group) => {
            // Sort column strictly by start time, then end time. Never by name.
            const sortedRecords = [...group.list.records].sort((a, b) => {
                const sA = a.data.start_hour ?? 0;
                const sB = b.data.start_hour ?? 0;
                const eA = a.data.end_hour ?? 0;
                const eB = b.data.end_hour ?? 0;
                return sA - sB || eA - eB;
            });

            // Detect overlaps within this day column (start < other.end and end > other.start)
            const overlapIds = new Set();
            for (let i = 0; i < sortedRecords.length; i++) {
                for (let j = i + 1; j < sortedRecords.length; j++) {
                    const r1 = sortedRecords[i].data;
                    const r2 = sortedRecords[j].data;
                    const r1Active = r1.active !== false;
                    const r2Active = r2.active !== false;
                    if (r1Active && r2Active && r1.start_hour < r2.end_hour && r1.end_hour > r2.start_hour) {
                        overlapIds.add(sortedRecords[i].id);
                        overlapIds.add(sortedRecords[j].id);
                    }
                }
            }

            const cards = sortedRecords.map((record) => {
                const data = record.data;
                const slotCount = data.slot_count || 0;
                const barPercent = maxSessions > 0 ? Math.min(100, Math.max(1, (slotCount / maxSessions) * 100)) : 0;

                // Outliers using median of visible session counts
                let barColor = "#6366f1"; // Normal: primary indigo
                if (slotCount > 2 * median) {
                    barColor = "#d97706"; // Above 2x median: Amber
                } else if (slotCount < 0.1 * median || slotCount < 5) {
                    barColor = "#94a3b8"; // Under 10% median or under 5 sessions: Muted slate
                }

                // Format duration: whole hour as '1h', never '1h 00m'
                const startStr = this.formatHour(data.start_hour);
                const endStr = this.formatHour(data.end_hour);
                const durMins = Math.round(((data.end_hour || 0) - (data.start_hour || 0)) * 60);
                const h = Math.floor(durMins / 60);
                const m = durMins % 60;
                let durStr = "";
                if (m === 0) {
                    durStr = `${h}h`;
                } else if (h === 0) {
                    durStr = `${m}m`;
                } else {
                    durStr = `${h}h ${m}m`;
                }
                // En dash \u2013 and middle dot \u00b7
                const timeDisplay = `${startStr}\u2013${endStr} \u00b7 ${durStr}`;

                // Real custom title (only when slot has a real name that is not "{Weekday} {start} - {end}")
                const dayName = group.displayName || "";
                const gen1 = `${dayName} ${startStr} - ${endStr}`;
                const gen2 = `${dayName} ${startStr}\u2013${endStr}`;
                const curName = (data.name || "").trim();
                let customTitle = null;
                if (curName && curName !== gen1 && curName !== gen2 && !curName.startsWith(dayName)) {
                    customTitle = curName;
                } else if (data.custom_title) {
                    customTitle = data.custom_title;
                }

                const hasOverlap = overlapIds.has(record.id) || !!data.has_overlap;
                const isActive = data.active !== false;
                const isMorning = (data.end_hour || 0) <= 12.0;

                return {
                    record,
                    id: record.id,
                    timeDisplay,
                    customTitle,
                    slotCount,
                    barPercent,
                    barColor,
                    hasOverlap,
                    isActive,
                    isMorning,
                };
            });

            // Split into Morning and Afternoon groups
            const morningCards = cards.filter((c) => c.isMorning);
            const afternoonCards = cards.filter((c) => !c.isMorning);
            const hasMorning = morningCards.length > 0;
            const hasAfternoon = afternoonCards.length > 0;
            // Omit group label if column has no morning or no afternoon cards
            const showPeriodLabels = hasMorning && hasAfternoon;

            // Total sessions sum for this day
            const totalSessions = cards.reduce((sum, c) => sum + c.slotCount, 0);
            const slotsCount = cards.length;
            const slotsText = slotsCount === 1 ? "slot" : "slots";
            const sessionsText = `${totalSessions.toLocaleString()} sessions`;
            const headerSummary = `${slotsCount} ${slotsText} \u00b7 ${sessionsText}`;

            return {
                group,
                key: group.id || String(group.value),
                displayName: group.displayName,
                headerSummary,
                morningCards,
                afternoonCards,
                hasMorning,
                hasAfternoon,
                showPeriodLabels,
            };
        });
    }

    onCardClick(record) {
        if (this.props.openRecord) {
            this.props.openRecord(record);
        }
    }

    onCardKeyDown(record, ev) {
        if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            if (this.props.openRecord) {
                this.props.openRecord(record);
            }
        }
    }
}

export const timeslotKanbanView = {
    ...kanbanView,
    Controller: TimeslotKanbanController,
    Renderer: TimeslotKanbanRenderer,
};

registry.category("views").add("timeslot_kanban", timeslotKanbanView);
