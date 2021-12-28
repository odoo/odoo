odoo.define('hr_holidays.employee.dashboard.views', function(require) {
    'use strict';

    var core = require('web.core');
    const config = require('web.config');
    var CalendarController = require("web.CalendarController");
    var CalendarRenderer = require("web.CalendarRenderer");
    var CalendarPopover = require('web.CalendarPopover');
    var CalendarView = require("web.CalendarView");
    var dialogs = require('web.view_dialogs');
    var viewRegistry = require('web.view_registry');

    var _t = core._t;
    var QWeb = core.qweb;

    // TODO in master: Split the timeoff calendar components into several files to reuse or extend them here

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

    var TimeOffPopoverRenderer = CalendarRenderer.extend({
        template: "TimeOff.CalendarView.extend",
        /**
         * We're overriding this to display the weeknumbers on the year view
         *
         * @override
         * @private
         */
        _getFullCalendarOptions: function () {
            const oldOptions = this._super(...arguments);
            // Parameters
            oldOptions.views.dayGridYear.weekNumbers = true;
            oldOptions.views.dayGridYear.weekNumbersWithinDays = false;
            return oldOptions;
        },

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
        /**
         * @override
         * @private
         */
        _renderCalendar: function() {
            this._super.apply(this, arguments);
            let weekNumbers = this.$el.find('.fc-week-number');
            weekNumbers.each( function() {
                let weekRow = this.parentNode;
                // By default, each month has 6 weeks displayed, hide the week number if there is no days for the week
                if(!weekRow.children[1].classList.length && !weekRow.children[weekRow.children.length-1].classList.length) {
                    this.innerHTML = '';
                }
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
                    context: self.state.context,
                });
            }).then(function (result) {
                self.$el.parent().find('.o_calendar_mini').hide();
                self.$el.parent().find('.o_timeoff_container').remove();

                // Do not display header if there is no element to display
                if (result.length > 0) {
                    if (config.device.isMobile) {
                        result.forEach((data) => {
                            const elem = QWeb.render('hr_holidays.dashboard_calendar_header_mobile', {
                                timeoff: data,
                            });
                            self.$el.find('.o_calendar_filter_item[data-value=' + data[4] + '] .o_cw_filter_title').append(elem);
                        });
                    } else {
                        const elem = QWeb.render('hr_holidays.dashboard_calendar_header', {
                            timeoffs: result,
                        });
                        self.$el.before(elem);
                    }
                }
            });
        },
    });

    var TimeOffCalendarEmployeeController = CalendarController.extend({

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
            let self = this;

            self._rpc({
                model: 'ir.ui.view',
                method: 'get_view_id',
                args: ['hr_holidays.hr_leave_view_form_dashboard_new_time_off'],
            }).then(function(ids) {
                self.timeOffDialog = new dialogs.FormViewDialog(self, {
                    res_model: "hr.leave",
                    view_id: ids,
                    context: {
                        'default_employee_id': self.context.employee_id[0],
                        'default_date_from': moment().format('YYYY-MM-DD'),
                        'default_date_to': moment().add(1, 'days').format('YYYY-MM-DD'),
                        'lang': self.context.lang,
                    },
                    title: _t("New time off"),
                    disable_multiple_selection: true,
                    on_saved: function() {
                        self.reload();
                    },
                });
                self.timeOffDialog.open();
            });
        },

        /**
         * Action: create a new allocation request
         *
         * @private
         */
        _onNewAllocation: function () {
            let self = this;

            self._rpc({
                model: 'ir.ui.view',
                method: 'get_view_id',
                args: ['hr_holidays.hr_leave_allocation_view_form_manager_dashboard'],
            }).then(function(ids) {
                self.allocationDialog = new dialogs.FormViewDialog(self, {
                    res_model: "hr.leave.allocation",
                    view_id: ids,
                    context: {
                        'default_employee_ids': self.context.employee_id,
                        'default_state': 'confirm',
                        'lang': self.context.lang,
                    },
                    title: _t("New Allocation"),
                    disable_multiple_selection: true,
                    on_saved: function() {
                        self.reload();
                    },
                });
                self.allocationDialog.open();
            });
        },

        _onOpenCreate: function () {
            this.context['default_employee_id'] = this.context.employee_id[0];
            this._super(...arguments);
        },

        /**
         * @override
         */
         _setEventTitle: function () {
            return _t('Time Off Request');
        },
    });

    var TimeOffCalendarEmployeeView = CalendarView.extend({
        config: _.extend({}, CalendarView.prototype.config, {
            Controller: TimeOffCalendarEmployeeController,
            Renderer: TimeOffCalendarRenderer,
        }),
    });

    viewRegistry.add('time_off_employee_calendar', TimeOffCalendarEmployeeView);
});
