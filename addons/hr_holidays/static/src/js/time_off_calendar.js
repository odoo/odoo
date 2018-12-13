odoo.define('hr_holidays.dashboard.view_custo', function(require) {
    'use strict';

    var core = require('web.core');
    var CalendarController = require("web.CalendarController");
    var CalendarView = require("web.CalendarView");
    var viewRegistry = require('web.view_registry');

    var _t = core._t;
    var QWeb = core.qweb;


    var TimeOffCalendarController = CalendarController.extend({
        events: _.extend({}, CalendarController.prototype.events, {
            'click .o_header_calendar_button_prev': '_onPrev',
            'click .o_header_calendar_button_next': '_onNext',
            'click .btn-time-off': '_onNewTimeOff',
            'click .btn-allocation': '_onNewAllocation',
        }),

        /**
         * @override
         */
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self.$el.find('.o_calendar_sidebar_container').remove();
                self._renderSummaryTimeOff();
                self.$(".o_calendar_widget").fullCalendar('option', 'contentHeight', 500);
            });
        },

        /**
         * Override to add correct date in header of calendar
         *
         * @override
         */
        update: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self._updateSummaryTimeOff();
            });
        },

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
            this.$buttons = $(QWeb.render('hr_holidays.dashboard.calendar.button', {
                time_off: _t('New Time Off Request'),
                request: _t('New Allocation Request'),
            }));

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
         * Create a header for calendar with previous and next month button.
         * Add month and year on the header
         *
         * @private
         */
        _renderCalendarHeader: function () {
            this.$el.find('.fc-week-number').remove();

            if (!this.$('#header_calendar_leaves').length) {
                var current_month = this.model.data.target_date.format('MMMM YYYY');
                var header = $(QWeb.render('hr_holidays.dashboard.calendar.header', {
                    current_month: current_month,
                }));

                this.$el.find('.fc-widget-header').find('thead').prepend(header);
            }
        },

        /**
         * Create a summary of all time off and requests allocations
         *
         * @private
         */
        _renderSummaryTimeOff: function () {
            var leave_state = '<div class="o_form_view"><div class="o_form_sheet_bg"><div class="o_form_sheet"><div id="counter_leaves" class="row">';
            leave_state += '</div></div></div></div>';
            this.$el.find('.o_calendar_container').before(
                $(leave_state)
            );

            this._updateSummaryTimeOff();
        },

        /**
         * Create a summary of all time off and requests allocations
         *
         * @private
         */
        _updateSummaryTimeOff: function () {
            var self = this;

            this._renderCalendarHeader();

            return this._rpc({
                model: 'hr.leave.type',
                method: 'get_days_all_request',
                args: [this.context],
            })
            .then(function (leaves) {
                $('#counter_leaves').children().remove();
                for (var leave in leaves){
                    var leave_box = $('<div class="col text-center border-right"><h1 class="text-nowrap"></h1><h3></h3></div>');
                    var content = leaves[leave][1];
                    var leave_count = leave_box.find('h1');
                    leave_box.append(leave_count.text(
                        leaves[leave][2] !== 'no' ? content.virtual_remaining_leaves + " / " + content.max_leaves : -content.virtual_remaining_leaves
                    ));
                    var leave_name = leave_box.find('h3');
                    leave_name.text(leaves[leave][0]);
                    leave_box.append(leave_name);
                    $('#counter_leaves').append(leave_box);
                }
                $('#counter_leaves').children().last().removeClass('border-right');

                self.$el.find('.o_calendar_container').appendTo(self.$el.find('.o_form_sheet'));
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
        _onNewTimeOff: function () {
            var self = this;
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'hr.leave',
                view_type: 'form',
                views: [[false,'form']],
                target: 'new',
            }, {
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
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'hr.leave.allocation',
                view_type: 'form',
                views: [[false,'form']],
                target: 'new',
            }), {
                on_close: function () {
                    self.reload();
                }
            };
        },
    });
    var TimeOffCalendarView = CalendarView.extend({
        config: _.extend({}, CalendarView.prototype.config, {
            Controller: TimeOffCalendarController,
        }),
    });

    viewRegistry.add('time_off_calendar', TimeOffCalendarView);
});