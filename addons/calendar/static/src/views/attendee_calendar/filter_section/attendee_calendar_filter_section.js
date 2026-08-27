import { AvatarTag } from "@web/core/tags_list/avatar_tag";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { TagsList } from "@web/core/tags_list/tags_list";
import { user } from "@web/core/user";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { CalendarFilterSection } from "@web/views/calendar/calendar_filter_section/calendar_filter_section";

export class AttendeeCalendarFilterSection extends CalendarFilterSection {
    static components = {
        AvatarTag,
        BadgeTag,
        Many2XAutocomplete,
        TagsList,
    };
    static template = "calendar.AttendeeCalendarFilterSection";
    static subTemplates = {};

    get activePartnerFilters() {
        return (this.section.filters || []).filter(
            (filter) => filter.active && filter.value !== user.partnerId
        );
    }

    get attendeeTags() {
        return this.activePartnerFilters.map((filter) => ({
            id: `${filter.type}-${filter.value}`,
            resId: filter.value,
            text: filter.label,
            colorIndex: filter.colorIndex,
            canEdit: true,
            img: `/web/image/res.partner/${filter.value}/avatar_128`,
            onDelete: () => this.onFilterTagDelete(filter),
        }));
    }

    get attendeeDomain() {
        return [
            [
                "id",
                "not in",
                [user.partnerId, ...this.activePartnerFilters.map((filter) => filter.value)],
            ],
        ];
    }

    async onFilterUpdate(records) {
        if (!records?.length) {
            return;
        }

        const currentRecords = this.activePartnerFilters.map((filter) => ({
            id: filter.value,
            display_name: filter.label,
        }));
        const currentIds = new Set(currentRecords.map((record) => record.id));
        const newRecords = records.filter((record) => !currentIds.has(record.id));

        await this.props.model.updateRecordFilters(this.section.fieldName, [
            ...currentRecords,
            ...newRecords,
        ]);
    }

    async onFilterTagDelete(filter) {
        if (filter.type === "user") {
            return await this.props.model.updateFilters(this.section.fieldName, [filter], false);
        }
        const records = this.activePartnerFilters
            .filter((currentFilter) => currentFilter.value !== filter.value)
            .map((currentFilter) => ({
                id: currentFilter.value,
                display_name: currentFilter.label,
            }));

        await this.props.model.updateRecordFilters(this.section.fieldName, records);
    }
}
