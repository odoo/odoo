odoo.define('hr_holidays.dashboard.view_custo', function(require) {
    'use strict';

    var core = require('web.core');
    var CalendarController = require("web.CalendarController");
    var CalendarRenderer = require("web.CalendarRenderer");
    var CalendarView = require("web.CalendarView");
    var viewRegistry = require('web.view_registry');

    var _t = core._t;
    var QWeb = core.qweb;


    var TimeOffCalendarController = CalendarController.extend({
        events: _.extend({}, CalendarController.prototype.events, {
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
            this._super.apply(this, arguments);

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
            var self = this;

            this.do_action('hr_holidays.hr_leave_action_my_request', {
                on_close: function () {
                    self.reload();
                }
            });
        },

        /**
         * Action: create a new allocation request
         *
         * @private
         */
        _onNewAllocation: function () {
            var self = this;
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'hr.leave.allocation',
                name: 'New Allocation Request',
                views: [[false,'form']],
                context: {'form_view_ref': 'hr_holidays.hr_leave_allocation_view_form_dashboard'},
                target: 'new',
            }, {
                on_close: function () {
                    self.reload();
                }
            });
        },
    });
    var TimeOffCalendarRenderer = CalendarRenderer.extend({
        _render: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                return self._rpc({
                    model: 'hr.leave.type',
                    method: 'get_days_all_request',
                    context: self.context,
                });
            }).then(function (result) {
                self.$el.parent().find('.o_timeoff_container').remove();
                var elem = QWeb.render('hr_holidays.dashboard_calendar_header', {
                    timeoffs: result,
                });
                self.$el.before(elem);
            });
        },
    });
    var TimeOffCalendarView = CalendarView.extend({
        config: _.extend({}, CalendarView.prototype.config, {
            Controller: TimeOffCalendarController,
            Renderer: TimeOffCalendarRenderer,
        }),
    });

    viewRegistry.add('time_off_calendar', TimeOffCalendarView);
});
