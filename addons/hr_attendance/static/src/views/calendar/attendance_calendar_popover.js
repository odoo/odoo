import { parseXML } from "@web/core/utils/xml";
import { CARD_ATTRIBUTE } from "@web/views/card/card_arch_parser";
import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";

// icons for known attendance fields shown in the popover
const FIELD_ICONS = {
    work_entry_type_id: `<i class="oi oi-fw text-400" data-icon="label"/>`,
    break_duration: `<i class="oi oi-fw text-400" data-icon="pause_circle"/>`,
};

/**
 * Customised calendar event popover for attendance records.
 *
 * Differences from the base CalendarCommonPopover:
 *  - date line is suppressed (the week view already makes the date obvious)
 *  - compact stale-source warning shown at the top when source_stale is set
 *  - popup body order: warning → time type → time + duration → break
 */
export class AttendanceCalendarPopover extends CalendarCommonPopover {
    computeDateTimeAndDuration() {
        super.computeDateTimeAndDuration();
        this.date = null; // suppress the date line
    }

    getDefaultPopoverBody() {
        const fieldNodes = Object.values(this.props.model.meta.popoverFieldNodes);

        // build a labelled field row; uses a per-field icon when available
        function buildFieldItem(fn) {
            const widget = `widget="${fn.widget || fn.type}"`;
            const options = `options='${JSON.stringify(fn.options)}'`;
            const readonly = fn.readonly ? `readonly="${fn.readonly}"` : "";
            const fieldTag = `<field name="${fn.name}" ${options} ${widget} ${readonly}/>`;
            const icon = FIELD_ICONS[fn.name] ||
                (fn.options.icon
                    ? `<i class="oi oi-fw text-400" title="${fn.string}" data-icon="${fn.options.icon}"/>`
                    : `<span class="fw-bold">${fn.string}</span>`);
            return `<div class="d-flex align-items-baseline gap-2">${icon}${fieldTag}</div>`;
        }

        const items = [];

        // invisible fields must come first so their values are available for
        // invisible expressions on other nodes in the same card template
        for (const fn of fieldNodes) {
            if (["1", "True"].includes(fn.invisible)) {
                items.push(`<field name="${fn.name}" invisible="1"/>`);
            }
        }

        // 1. stale-source warning — compact, at the very top
        items.push(`
            <div class="alert alert-warning py-1 px-2 mb-0 small" invisible="not source_stale">
                <i class="oi oi-fw me-1" data-icon="warning"/>
                <span invisible="source_attendance_id">Source deleted</span>
                <span invisible="not source_attendance_id">Source modified</span>
            </div>
        `);

        // 2. time type
        const wetNode = fieldNodes.find(
            (fn) => fn.name === "work_entry_type_id" && !["1", "True"].includes(fn.invisible)
        );
        if (wetNode) {
            items.push(buildFieldItem(wetNode));
        }

        // 3. time range + duration
        if (this.time) {
            const duration = this.timeDuration
                ? ` <small class="fw-bold">(${this.timeDuration})</small>`
                : "";
            items.push(`
                <div class="d-flex align-items-baseline gap-2">
                    <i class="oi oi-fw text-400" data-icon="schedule"/>
                    <span class="fw-bold">${this.time}</span>${duration}
                </div>
            `);
        }

        // 4. break duration
        const breakNode = fieldNodes.find(
            (fn) => fn.name === "break_duration" && !["1", "True"].includes(fn.invisible)
        );
        if (breakNode) {
            items.push(buildFieldItem(breakNode));
        }

        return parseXML(`<t t-name="${CARD_ATTRIBUTE}" class="gap-3">${items.join("")}</t>`);
    }
}
