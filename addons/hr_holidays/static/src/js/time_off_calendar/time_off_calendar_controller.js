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
            this._rpc({
                model: 'hr.leave.stress.day',
                method: 'get_stress_days',
                args: [this.model.data.start_date, this.model.data.end_date],
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
        const viewId = await this._rpc({
            model: 'hr.leave',
            method: 'action_new_time_off',
            args: ['hr_holidays.hr_leave_view_form_dashboard_new_time_off'],
        });

        this.timeOffDialog = new dialogs.FormViewDialog(this, {
            res_model: "hr.leave",
            view_id: viewId,
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
        const viewXmlId = this._getFormViewId();

        const viewId = await this._rpc({
            model: 'ir.ui.view',
            method: 'get_view_id',
            args: [viewXmlId],
        });

        this.allocationDialog = new dialogs.FormViewDialog(this, {
            res_model: "hr.leave.allocation",
            view_id: viewId,
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
        return {
            'default_date_from': moment().format('YYYY-MM-DD'),
            'default_date_to': moment().add(1, 'days').format('YYYY-MM-DD'),
            'lang': this.context.lang,
        };
    },

    _getAllocationContext() {
        return {
            'default_state': 'confirm',
            'lang': this.context.lang,
        };
    },

});
