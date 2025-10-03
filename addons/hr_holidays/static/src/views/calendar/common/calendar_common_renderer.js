import { onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";
import { CalendarCommonRenderer } from '@web/views/calendar/calendar_common/calendar_common_renderer';
import { useMandatoryDays } from '../../hooks';
import { TimeOffCalendarCommonPopover } from './calendar_common_popover';


export class TimeOffCalendarCommonRenderer extends CalendarCommonRenderer {
    static components = {
        ...TimeOffCalendarCommonRenderer,
        Popover: TimeOffCalendarCommonPopover,
    };
    setup() {
        super.setup();
        this.mandatoryDays = useMandatoryDays(this.props);
        onWillStart(async () => {
            this.isManager = (await user.hasGroup("hr_holidays.group_hr_holidays_user"));
        });
    }

    /**
     * @override
     */
    get options() {
        return {
            ...super.options,
            eventDataTransform: (eventData) => {
                const record = (eventData.id && this.props.model.records[eventData.id])
                if (record && !record.rawRecord?.request_unit_hours) {
                    // disable resizing if full-day leave or half-day leave
                    eventData.durationEditable = false;
                }
                return eventData;
            },
        }
    }

    getDayCellClassNames(info) {
        return [...super.getDayCellClassNames(info), ...this.mandatoryDays(info)];
    }

    onClick(info) {
        // To open record view
        return this.onDblClick(info)
    }
}
