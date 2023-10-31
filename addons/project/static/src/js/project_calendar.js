/** @odoo-module **/

import CalendarController from 'web.CalendarController';
import CalendarView from 'web.CalendarView';
import viewRegistry from 'web.view_registry';
import { ProjectControlPanel } from '@project/js/project_control_panel';

const ProjectCalendarController = CalendarController.extend({
    _renderButtonsParameters() {
        return Object.assign({}, this._super(...arguments), {scaleDrop: true});
    },

    /**
     * @private
     * @param {OdooEvent} event
     */
    _onChangeDate: function (event) {
        this._super.apply(this, arguments);
        this.model.setScale('month');
        this.model.setDate(event.data.date);
        this.reload();
    },
});

export const ProjectCalendarView = CalendarView.extend({
    config: Object.assign({}, CalendarView.prototype.config, {
        Controller: ProjectCalendarController,
        ControlPanel: ProjectControlPanel,
    }),
});

viewRegistry.add('project_calendar', ProjectCalendarView);
