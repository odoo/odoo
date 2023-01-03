/** @odoo-module */

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
    }

    getDayCellClassNames(info) {
        return [...super.getDayCellClassNames(info), ...this.mandatoryDays(info)];
    }
}
