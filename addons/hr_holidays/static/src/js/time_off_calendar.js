odoo.define('hr_holidays.dashboard.view_custo', function(require) {
    'use strict';

    var core = require('web.core');
    var CalendarPopover = require('web.CalendarPopover');
    var CalendarController = require("web.CalendarController");
    var CalendarRenderer = require("web.CalendarRenderer");
    var CalendarView = require("web.CalendarView");
    var viewRegistry = require('web.view_registry');

    var _t = core._t;
    var QWeb = core.qweb;

    var TimeOffCalendarPopover = CalendarPopover.extend({
        template: 'hr_holidays.calendar.popover',

        init: function (parent, eventInfo) {
            this._super.apply(this, arguments);
            const state = this.event.extendedProps.record.state;
            this.canDelete = state && ['validate', 'refuse'].indexOf(state) === -1;
            this.canEdit = state !== undefined;
            this.displayFields = [];

            if (this.modelName === "hr.leave.report.calendar") {
                const duration = this.event.extendedProps.record.display_name.split(':').slice(-1);
                this.display_name = _.str.sprintf(_t("Time Off : %s"), duration);
            } else {
                this.display_name = this.event.extendedProps.record.display_name;
            }
        },
    });

    var TimeOffCalendarController = CalendarController.extend({
        events: _.extend({}, CalendarController.prototype.events, {
            'click .btn-time-off': '_onNewTimeOff',
            'click .btn-allocation': '_onNewAllocation',
        }),

        /**
         * @override
         */
        start: function () {
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

        renderButtons: function ($node) {
            this._super.apply(this, arguments);

            $(QWeb.render('hr_holidays.dashboard.calendar.button', {
                time_off: _t('New Time Off'),
                request: _t('New Allocation'),
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

    var TimeOffPopoverRenderer = CalendarRenderer.extend({
        config: _.extend({}, CalendarRenderer.prototype.config, {
            CalendarPopover: TimeOffCalendarPopover,
        }),

        _getPopoverParams: function (eventData) {
            let params = this._super.apply(this, arguments);
            let calendarIcon;
            let state = eventData.extendedProps.record.state;

            if (state === 'validate') {
                calendarIcon = 'fa-calendar-check-o';
            } else if (state === 'refuse') {
                calendarIcon = 'fa-calendar-times-o';
            } else if(state) {
                calendarIcon = 'fa-calendar-o';
            }

            params['title'] = eventData.extendedProps.record.display_name.split(':').slice(0, -1).join(':');
            params['template'] = QWeb.render('hr_holidays.calendar.popover.placeholder', {color: this.getColor(eventData.color_index), calendarIcon: calendarIcon});
            return params;
        },

        _render: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self.$el.parent().find('.o_calendar_mini').hide();
            });
        },
    });

    var TimeOffCalendarRenderer = TimeOffPopoverRenderer.extend({
        _render: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                return self._rpc({
                    model: 'hr.leave.type',
                    method: 'get_days_all_request',
                    context: self.context,
                });
            }).then(function (result) {
                self.$el.parent().find('.o_calendar_mini').hide();
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

    /**
     * Calendar shown in the "Everyone" menu
     */
    var TimeOffCalendarAllView = CalendarView.extend({
        config: _.extend({}, CalendarView.prototype.config, {
            Renderer: TimeOffPopoverRenderer,
        }),
    });

    viewRegistry.add('time_off_calendar', TimeOffCalendarView);
    viewRegistry.add('time_off_calendar_all', TimeOffCalendarAllView);
});
