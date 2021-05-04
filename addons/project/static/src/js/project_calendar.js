/** @odoo-module **/

import CalendarController from 'web.CalendarController';
import CalendarView from 'web.CalendarView';
import viewRegistry from 'web.view_registry';

const ProjectCalendarController = CalendarController.extend({
    _renderButtonsParameters() {
        return Object.assign({}, this._super(...arguments), {scaleDrop: true});
    },
});

export const ProjectCalendarView = CalendarView.extend({
    config: Object.assign({}, CalendarView.prototype.config, {
        Controller: ProjectCalendarController,
    }),
});

viewRegistry.add('project_calendar', ProjectCalendarView);
