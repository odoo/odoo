odoo.define('timer.timer_toggle_button', function (require) {
"use strict";

const fieldRegistry = require('web.field_registry');
const { FieldToggleBoolean } = require("web.basic_fields");
const { _lt } = require('web.core');

/**
 * The TimerToggleButton is used to display correctly the button
 * to start or stop a timer for a timesheet in kanban, list and grid
 * views.
 */
const TimerToggleButton = FieldToggleBoolean.extend({
    /**
     * @override
     * @private
     */
    _render: function () {
        // When the is_timer_running field is false, then the button is used to start the timer
        const title = this.value ? _lt('Stop') : _lt('Play');
        const name = this.value ? 'action_timer_stop' : 'action_timer_start';
        const label = this.value ? _lt('Stop') : _lt('Start');

        this.$('i')
            .addClass('fa')
            .toggleClass('fa-stop-circle o-timer-stop-button', this.value)
            .toggleClass('fa-play-circle o-timer-play-button', !this.value)
            .attr('title', title);

        this.$el.addClass('o-timer-button');
        this.$el.attr('title', title);
        this.$el.attr('name', name);
        this.$el.attr('aria-label', label);
        this.$el.attr('aria-pressed', this.value);
        this.$el.attr('type', 'button');
        this.$el.attr('role', 'button');
    },
    /**
     * Toggle the button
     *
     * When the user click on this button,
     *  -   the action "action_timer_start" is called
     *      into the account.analytic.line model,
     *      if the value of is_timer_running field is set on false.
     *  -   the action "action_timer_stop" is called
     *      into the account.analytic.line model,
     *      if the value of is_timer_running field is set on true.
     * Then we change the value of the is_timer_running.
     * @override
     * @private
     * @param {MouseEvent} event
     */
    _onToggleButton: async function (event) {
        const context = this.record.getContext();
        event.stopPropagation();
        const result = await this._rpc({
            model: this.model,
            method: this._getActionButton(),
            context: context,
            args: [this.res_id]
        });

        this.trigger_up('timer_changed', {
            id: this.res_id,
            is_timer_running: !this.value
        });

        this._setValue(!this.value);
    },
    _getActionButton: function () {
        return this.value ? 'action_timer_stop' : 'action_timer_start';
    }
});

fieldRegistry.add('timer_toggle_button', TimerToggleButton);

return TimerToggleButton;

});
