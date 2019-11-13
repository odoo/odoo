odoo.define('hr_holidays.dashboard.view_custo', function(require) {
    'use strict';

    const core = require('web.core');
    const CalendarController = require("web.CalendarController");
    const CalendarRenderer = require("web.CalendarRenderer");
    const CalendarView = require("web.CalendarView");
    const viewRegistry = require('web.view_registry');

    const _t = core._t;
    const QWeb = core.qweb;


    const TimeOffCalendarController = CalendarController.extend({
        events: Object.assign({}, CalendarController.prototype.events, {
            'click .btn-time-off': '_onNewTimeOff',
            'click .btn-allocation': '_onNewAllocation',
        }),

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

         /**
         * Render the buttons and add new button about
         * times off and allocations request
         *
         * @override
         */

        renderButtons: function ($node) {
            this._super(...arguments);

            $(QWeb.render('hr_holidays.dashboard.calendar.button', {
                time_off: _t('New Time Off Request'),
                request: _t('New Allocation Request'),
            })).appendTo(this.$buttons);

            if ($node) {
                this.$buttons.appendTo($node);
            } else {
                this.$('.o_calendar_buttons').replaceWith(this.$buttons);
            }
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Action: create a new time off request
         *
         * @private
         */
        _onNewTimeOff: function () {
            this.do_action('hr_holidays.hr_leave_action_my_request', {
                on_close: () => {
                    this.reload();
                }
            });
        },

        /**
         * Action: create a new allocation request
         *
         * @private
         */
        _onNewAllocation: function () {
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'hr.leave.allocation',
                name: 'New Allocation Request',
                views: [[false, 'form']],
                context: {'form_view_ref': 'hr_holidays.hr_leave_allocation_view_form_dashboard'},
                target: 'new',
            }, {
                on_close: () => {
                    this.reload();
                }
            });
        },
    });
    class TimeOffCalendarRenderer extends CalendarRenderer {
        _render() {
            const self = this;
            super._render(...arguments);
            self.env.services.rpc({
                model: 'hr.leave.type',
                method: 'get_days_all_request',
                context: self.context,
            }).then(function (result) {
                self.el.parentElement.querySelectorAll('.o_timeoff_container').forEach(node => {
                    self.el.parentElement.removeChild(node);
                });
                const elem = self.env.qweb.renderToString('hr_holidays.dashboard_calendar_header', {
                    timeoffs: result,
                });
                self.el.insertAdjacentHTML('beforebegin', elem);
            });
        }
    }
    const TimeOffCalendarView = CalendarView.extend({
        config: Object.assign({}, CalendarView.prototype.config, {
            Controller: TimeOffCalendarController,
            Renderer: TimeOffCalendarRenderer,
        }),
    });

    viewRegistry.add('time_off_calendar', TimeOffCalendarView);
});
