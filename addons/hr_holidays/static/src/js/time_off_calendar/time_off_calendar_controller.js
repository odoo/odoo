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
        if(timeoffState && !['validate', 'refuse'].includes(timeoffState)) {
            options.deletable = true;
            options.removeButtonText = _t("Delete");
            options.on_remove = () => {
                Dialog.confirm(self, _t("Are you sure you want to delete this record ?"), {
                    confirm_callback: () => {
                        self.model.deleteRecords(self._getEventId(event), self.modelName).then(() => {
                            self.reload();
                        });
                    }
                });
            };
        }
        return options;
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
            model: 'ir.ui.view',
            method: 'get_view_id',
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
        };
    },

    _getAllocationContext() {
        return {
            'default_state': 'confirm',
        };
    },

});
