import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    BadgesSelectionField,
    badgesSelectionField,
} from "@web/views/fields/badges_selection/badges_selection_field";

export class HrHolidaysBadgeSelectionWithFilterField extends BadgesSelectionField {
    get options() {
        const { name, record } = this.props;
        const forceFullDuration = record.context?.force_full_duration;
        const isHalfDay = record.data.work_entry_type_request_unit === 'half_day';
        if (forceFullDuration && name === "request_duration" && !isHalfDay) {
            return record.fields[name].selection.filter(([value]) => value === "full");
        }
        return super.options;
    }
}

export const hrHolidaysBadgeSelectionFieldWithFilter = {
    ...badgesSelectionField,
    component: HrHolidaysBadgeSelectionWithFilterField,
    displayName: _t("Badges for Selection With Work Entry Request Unit Type Filter"),
};

registry.category("fields").add("selection_badge_with_filter", hrHolidaysBadgeSelectionFieldWithFilter);
