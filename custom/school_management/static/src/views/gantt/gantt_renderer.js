/** @odoo-module **/

import { Component } from "@odoo/owl";

export class GanttRenderer extends Component {
    static template = "school_management.GanttRenderer";
    static props = {
        model: Object,
        onOpenSlot: Function,
        onCreateSlot: Function,
    };

    getDays() {
        return this.props.model.days || [];
    }

    getOpenShifts() {
        return this.props.model.openShifts || { total_hours: 0, hours_label: "", slots: [] };
    }

    getResources() {
        return this.props.model.resources || [];
    }

    getSlotsForCell(resourceId, dateStr) {
        const allSlots = this.props.model.slots || [];
        return allSlots.filter((s) => {
            const matchesResource = resourceId ? (s.resource_id === resourceId) : (!s.resource_id);
            // Handle multi-day span or single day
            if (s.start_date && s.end_date) {
                return matchesResource && s.start_date <= dateStr && dateStr <= s.end_date;
            }
            return matchesResource && s.start_date === dateStr;
        });
    }

    isStartOfSpan(slot, dateStr) {
        return slot.start_date === dateStr;
    }

    getSlotColorClass(colorIndex) {
        const idx = (colorIndex || 0) % 12;
        return `o_gantt_color_${idx}`;
    }

    onCellClick(resourceId, dateStr, ev) {
        if (ev.target.closest(".o_gantt_pill")) {
            return;
        }
        this.props.onCreateSlot(resourceId, dateStr);
    }

    onPillClick(slot, ev) {
        ev.stopPropagation();
        this.props.onOpenSlot(slot.id);
    }
}
