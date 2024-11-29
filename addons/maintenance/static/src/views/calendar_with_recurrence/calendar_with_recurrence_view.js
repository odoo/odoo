import { calendarView } from '@web/views/calendar/calendar_view';
import { CalendarWithRecurrenceModel } from './calendar_with_recurrence_model';
import { CalendarWithRecurrenceRenderer } from './calendar_with_recurrence_renderer';
import { registry } from '@web/core/registry';

const CalendarWithRecurrenceView = {
    ...calendarView,
    Model: CalendarWithRecurrenceModel,
    Renderer: CalendarWithRecurrenceRenderer,
};

registry.category('views').add('calendar_with_recurrence', CalendarWithRecurrenceView);
