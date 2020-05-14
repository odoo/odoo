odoo.define('hr_timesheet.timesheet_uom_timer', function (require) {
"use strict";

const fieldRegistry = require('web.field_registry');
const TimesheetUom = require('hr_timesheet.timesheet_uom');
const { _lt } = require('web.core');
const session = require('web.session');

/**
 * Extend float time widget to add the using of a timer for duration
 * (unit_amount) field.
 */
const FieldTimesheetTimeTimer = TimesheetUom.FieldTimesheetTime.extend({
    init: function () {
        this._super.apply(this, arguments);
        this.isTimerRunning = this.record.data.is_timer_running;
    },

    _render: function () {
        this._super.apply(this, arguments);
        const my_timesheets = this.record.getContext().my_timesheet_display_timer;
        const display_timer = this.record.data.display_timer;
        if (my_timesheets && display_timer) {
            const title = this.isTimerRunning ? _lt('Stop') : _lt('Play');
            const name = this.isTimerRunning ? 'action_timer_stop' : 'action_timer_start';
            const label = this.isTimerRunning ? _lt('Stop') : _lt('Start');

            const button = $('<button>', {
                'class': 'o_icon_button o-timer-button mr8',
                'title': title,
                'name': name,
                'aria-label': label,
                'aria-pressed': this.isTimerRunning,
                'type': 'button',
                'role': 'button',
            });
            button.html('<i/>');
            button.find('i')
                .addClass('fa')
                .toggleClass('fa-stop-circle o-timer-stop-button', this.isTimerRunning)
                .toggleClass('fa-play-circle o-timer-play-button', !this.isTimerRunning)
                .attr('title', title);
            button.on('click', this._onToggleButton.bind(this));
            this.$el.prepend(button);
        }
    },

    _onToggleButton: async function (event) {
        const context = this.record.getContext();
        const prevent_deletion = this.attrs.options && this.attrs.options.prevent_deletion || false;
        event.stopPropagation();
        const result = await this._rpc({
            model: this.model,
            method: this._getActionButton(),
            context: $.extend({}, context, {prevent_deletion: prevent_deletion}),
            args: [this.res_id]
        });

        this.trigger_up('field_changed', {
            dataPointID: this.dataPointID,
            changes: {
                'is_timer_running': !this.isTimerRunning,
            },
        });
        this.trigger_up('timer_changed', {
            id: this.res_id,
            is_timer_running: !this.isTimerRunning
        });
    },

    _getActionButton: function () {
        return this.isTimerRunning ? 'action_timer_stop' : 'action_timer_start';
    }

});

/**
 * Binding depending on Company Preference
 *
 * determine wich widget will be the timesheet one.
 * Simply match the 'timesheet_uom' widget key with the correct
 * implementation (float_time, float_toggle, ...). The default
 * value will be 'float_factor'.
**/
const widgetName = 'timesheet_uom' in session ?
         session.timesheet_uom.timesheet_widget : 'float_factor';

let FieldTimesheetUom = null;

if (widgetName === 'float_toggle') {
    FieldTimesheetUom = TimesheetUom.FieldTimesheetToggle;
} else if (widgetName === 'float_time') {
    FieldTimesheetUom = FieldTimesheetTimeTimer;
} else {
    FieldTimesheetUom = (
            fieldRegistry.get(widgetName) &&
            fieldRegistry.get(widgetName).extend({})
        ) || TimesheetUom.FieldTimesheetFactor;
}
fieldRegistry.add('timesheet_uom_timer', FieldTimesheetUom);


return {
    FieldTimesheetTimeTimer,
};

});
