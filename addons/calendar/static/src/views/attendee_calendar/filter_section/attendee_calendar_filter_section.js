import { CalendarFilterSection } from "@web/views/calendar/calendar_filter_section/calendar_filter_section";
import { getColor } from "@web/views/calendar/utils";
import { MultiRecordSelector, multiRecordSelectorProps } from "@web/core/record_selectors/multi_record_selector";
import { user } from "@web/core/user";
import { t, useProps } from "@odoo/owl";

export class AttendeeCalendarFilterMultiRecordSelector extends MultiRecordSelector {
    props = useProps({
        ...multiRecordSelectorProps,
        colors: t.object().optional({}),
    });

    get isAvatarModel() {
        return false;
    }

    /**
     * Change tags color to match their partner calendar color.
     */
    getTags(props, displayNames) {
        return super.getTags(props, displayNames).map((tag) => ({
            ...tag,
            color: props.colors[tag.id],
        }));
    }
}

export class AttendeeCalendarFilterSection extends CalendarFilterSection {
    static template = "calendar.AttendeeCalendarFilterSection";
    static components = {
        ...CalendarFilterSection.components,
        AttendeeCalendarFilterMultiRecordSelector,
    }

    get isAttendeeSection() {
        return this.section.fieldName === "partner_ids";
    }

    get activePartnerFilters() {
        return (this.section.filters || []).filter(
            (filter) => filter.active && filter.value !== user.partnerId
        );
    }

    get partnerColors() {
        return Object.fromEntries(
            this.activePartnerFilters.map((f) => [f.value, getColor(f.colorIndex)])
        );
    }

    /**
     * Domain specifying which partners can be selected in the record selector.
     * Excluding the current user and already-selected attendees.
     */
    get partnersDomain() {
        return [
            [
                "id",
                "not in",
                [user.partnerId, ...this.activePartnerFilters.map((filter) => filter.value)],
            ],
        ];
    }

    async onFilterUpdate(partnerIds) {
        await this.props.model.updatePartnerFilters(
            this.section.fieldName,
            partnerIds,
        );
    }
}
