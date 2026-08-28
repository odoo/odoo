import { onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";
import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { useMandatoryDays, useExpectedHours } from "../../hooks";

export class TimeOffCalendarCommonRenderer extends CalendarCommonRenderer {
    setup() {
        super.setup();
        this.mandatoryDays = useMandatoryDays(this.props);
        this.expectedHours = useExpectedHours(this.props);
        onWillStart(async () => {
            this.isManager = await user.hasGroup("hr_holidays.group_hr_holidays_user");
        });
    }

    get options() {
        return {
            ...super.options,
            dayCellDidMount: this.onDayCellDidMount.bind(this),
        };
    }

    onDayCellDidMount(info) {
        const hoursStr = this.expectedHours(info);
        if (hoursStr) {
            info.el.dataset.tooltip = _t("Expected hours");
            
            const hoverBadge = document.createElement("div");
            hoverBadge.className = "o_expected_hours_hover";
            hoverBadge.innerText = hoursStr;
            info.el.appendChild(hoverBadge);
        }
    }

    getDayCellClassNames(info) {
        return [...super.getDayCellClassNames(info), ...this.mandatoryDays(info)];
    }

    onClick(info) {
        // To open record view
        return this.onDblClick(info);
    }
}
