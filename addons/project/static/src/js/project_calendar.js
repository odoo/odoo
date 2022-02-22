/** @odoo-module **/

import CalendarController from 'web.CalendarController';
import CalendarModel from 'web.CalendarModel';
import CalendarView from 'web.CalendarView';
import viewRegistry from 'web.view_registry';
import { ProjectControlPanel } from '@project/js/project_control_panel';

const ProjectCalendarController = CalendarController.extend({
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

const ProjectCalendarModel = CalendarModel.extend({
    /**
     * @private
     * @override
     */
    _getFullCalendarOptions: function () {
        const options = this._super(...arguments);
        options.eventDurationEditable = false;
        return options;
    }
})

export const ProjectCalendarView = CalendarView.extend({
    config: Object.assign({}, CalendarView.prototype.config, {
        Controller: ProjectCalendarController,
        ControlPanel: ProjectControlPanel,
        Model: ProjectCalendarModel,
    }),

    /**
    * @override
    */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);
        this.controllerParams.displayName += " - Tasks by Deadline";
    }
});

viewRegistry.add('project_calendar', ProjectCalendarView);
