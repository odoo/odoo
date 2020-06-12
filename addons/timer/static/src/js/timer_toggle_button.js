odoo.define('timer.timer_toggle_button', function (require) {
    "use strict";

    const fieldRegistryOwl = require('web.field_registry_owl');
    const { FieldBoolean } = require('web.basic_fields_owl');

    /**
     * The TimerToggleButton is used to display correctly the button
     * to start or stop a timer for a timesheet in kanban, list and grid
     * views.
     */
    class TimerToggleButton extends FieldBoolean {

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

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
        async _onToggleButton(ev) {
            const context = this.record.getContext();
            const preventDeletion = this.attrs.options && this.attrs.options.prevent_deletion || false;
            await this.env.services.rpc({
                model: this.model,
                method: this.value ? 'action_timer_stop' : 'action_timer_start',
                context: Object.assign({}, context, { prevent_deletion: preventDeletion}),
                args: [this.resId]
            });

            this.trigger('timer_changed', {
                id: this.resId,
                is_timer_running: !this.value
            });

            this._setValue(!this.value);
        }
    }

    TimerToggleButton.template = 'timerToggleButton';

    fieldRegistryOwl.add('timer_toggle_button', TimerToggleButton);

    return TimerToggleButton;

});
