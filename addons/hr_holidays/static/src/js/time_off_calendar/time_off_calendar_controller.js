/** @odoo-module **/

import { _t, qweb as QWeb } from "web.core";
import CalendarController from "web.CalendarController";
import dialogs from "web.view_dialogs";
import Dialog from "web.Dialog";

export const TimeOffCalendarController = CalendarController.extend({
    events: Object.assign({}, CalendarController.prototype.events, {
        'click .btn-time-off': '_onNewTimeOff',
        'click .btn-allocation': '_onNewAllocation',
    }),

    /**
     * @override
     */
    start() {
        this.$el.addClass('o_timeoff_calendar');
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Render the buttons and add new button about
     * time off and allocations request
     *
     * @override
     */
    renderButtons($node) {
        this._super(...arguments);

        $(QWeb.render('hr_holidays.dashboard.calendar.button', {
            time_off: _t('New Time Off'),
            request: this._getAllocationButtonTitle(),
        })).appendTo(this.$buttons);

        if ($node) {
            this.$buttons.appendTo($node);
        } else {
            this.$('.o_calendar_buttons').replaceWith(this.$buttons);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getFormDialogOptions(self, event) {
        const options = this._super(...arguments);
        const eventId = parseInt(event.data._id)
        // Get the time off data from the event
        const timeoffData = event.target.state.data.find((timeOff) => timeOff.id === eventId);
        // Take the record associated to the timeoffData and read its state to hide or not the Delete button
        const timeoffState = timeoffData && timeoffData.record.state;
        const canCancel = timeoffData && timeoffData.record.can_cancel;
        if(canCancel || timeoffState && !['validate', 'refuse'].includes(timeoffState)) {
            options.deletable = true;
            options.removeButtonText = _t("Delete");
            options.on_remove = () => this._deleteLeave(timeoffData.record);
        }
        return options;
    },

    _onDeleteRecord(ev) {
        this._deleteLeave(ev.data.event.record);
    },

    _deleteLeave(timeoff) {
        const canCancel = timeoff.can_cancel;
        if (canCancel) {
            const context = Object.assign({}, this.context, {
                default_leave_id: timeoff.id,
            });
            const cancel_dialog = new dialogs.FormViewDialog(this, {
                title: _t('Delete Confirmation'),
                res_model: 'hr.holidays.cancel.leave',
                context: context,
            });
            cancel_dialog.on('execute_action', this, (ev) => {
                const action_name = ev.data.action_data.name || ev.data.action_data.special;
                const event_data = _.clone(ev.data);
                if (action_name === 'action_cancel_leave') {
                    ev.stopPropagation();
                    this.trigger_up('execute_action', event_data);
                    setTimeout(() => this.reload(), 300);
                    cancel_dialog.close();
                }
            });
            cancel_dialog.open();
        } else {
            Dialog.confirm(this, _t("Are you sure you want to delete this record ?"), {
                confirm_callback: () => {
                    this.model.deleteRecords(timeoff.id, this.modelName).then(() => {
                        this.reload();
                    });
                }
            });
        }
    },

    _update() {
        return this._super(...arguments).then(() => {
            const request_args = [
                this.res_id,
                this.model.data.start_date,
                this.model.data.end_date,
            ]
            if (this.context.employee_id)
                request_args[0] = this.context.employee_id;
            this._rpc({
                model: 'hr.employee',
                method: 'get_stress_days',
                args: request_args,
                context: this.context,
            }).then((stressDays) => {
                this.$el.find('td.fc-day').toArray().forEach((td) => {
                    if (stressDays[td.dataset.date]) {
                        td.classList.add('hr_stress_day_' + stressDays[td.dataset.date]);
                    }
                });
            });
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Action: create a new time off request
     *
     * @private
     */
    async _onNewTimeOff() {
        this.timeOffDialog = new dialogs.FormViewDialog(this, {
            res_model: "hr.leave",
            context: this._getTimeOffContext(),
            title: _t("New time off"),
            disable_multiple_selection: true,
            on_saved: () => this.reload()
        });
        this.timeOffDialog.open();
    },

    /**
     * Action: create a new allocation request
     *
     * @private
     */
    async _onNewAllocation() {
        this.allocationDialog = new dialogs.FormViewDialog(this, {
            res_model: "hr.leave.allocation",
            context: this._getAllocationContext(),
            title: _t("New Allocation"),
            disable_multiple_selection: true,
            on_saved: () => this.reload()
        });
        this.allocationDialog.open();
    },

    _onOpenCreate() {
        this._super(...arguments);
        if(this.previousOpen) {
            this.previousOpen.on('closed', this, (ev) => {
                // we reload as record can be created or modified (sent, unpublished, ...)
                this.reload();
            });
        }
    },

    /**
     * @override
     */
    _setEventTitle() {
        return _t('Time Off Request');
    },

    _getAllocationButtonTitle() {
        return _t('Allocation Request');
    },

    _getFormViewId() {
        return 'hr_holidays.hr_leave_allocation_view_form_dashboard';
    },

    _getTimeOffContext() {
        let date_from = moment();
        if (this.mode === "day") {
            date_from = this.model.data.start_date;
        }
        let date_to = moment(date_from);
        date_from = date_from.set({
            'hour': 0,
            'minute': 0,
            'second': 0
        });
        date_from.subtract(this.getSession().getTZOffset(date_from), 'minutes');
        date_from = date_from.locale('en').format('YYYY-MM-DD HH:mm:ss');
        date_to = date_to.set({
            'hour': 23,
            'minute': 59,
            'second': 59
        });
        date_to.subtract(this.getSession().getTZOffset(date_to), 'minutes');
        date_to = date_to.locale('en').format('YYYY-MM-DD HH:mm:ss');
        return {
            'default_date_from': date_from,
            'default_date_to': date_to,
            'lang': this.context.lang,
            'form_view_ref': 'hr_holidays.hr_leave_view_form_dashboard_new_time_off'
        };
    },

    _getAllocationContext() {
        return {
            'default_state': 'confirm',
            'lang': this.context.lang,
            'form_view_ref': this._getFormViewId()
        };
    },

});
