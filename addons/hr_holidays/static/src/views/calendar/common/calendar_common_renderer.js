/** @odoo-module */

import { CalendarCommonRenderer } from '@web/views/calendar/calendar_common/calendar_common_renderer';

import { useStressDays } from '../../hooks';
import { TimeOffCalendarCommonPopover } from './calendar_common_popover';


export class TimeOffCalendarCommonRenderer extends CalendarCommonRenderer {
    setup() {
        super.setup();
        this.stressDays = useStressDays(this.props);
    }

    onDayRender(info) {
        super.onDayRender(info);
        this.stressDays(info);
    }
}
TimeOffCalendarCommonRenderer.components = {
    ...TimeOffCalendarCommonRenderer,
    Popover: TimeOffCalendarCommonPopover,
}
