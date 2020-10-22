odoo.define('hr_holidays.dashboard.view_custo', function(require) {
    'use strict';

    const core = require('web.core');
    const { CalendarPopover } = require('web.CalendarPopover');
    const CalendarController = require("web.CalendarController");
    const CalendarRenderer = require("web.CalendarRenderer");
    const CalendarView = require("web.CalendarView");
    const viewRegistry = require('web.view_registry');

    const _t = core._t;
    const QWeb = core.qweb;

    class TimeOffCalendarPopover extends CalendarPopover {
        /**
         * @override
         * @returns {Boolean}
         */
        get isEventDeletable() {
            const state = this.props.record.state;
            return state && ['validate', 'refuse'].indexOf(state) === -1;
        }
        /**
         * @override
         * @returns {Boolean}
         */
        get isEventEditable() {
            return this.props.record.state !== undefined;
        }
        /**
         * @override
         * @returns {Object}
         */
        get displayedFields() {
            return [];
        }
        /**
         * @returns {string}
         */
        get displayName() {
            if (this.props.modelName === 'hr.leave.report.calendar') {
                const duration = this.props.record.display_name.split(':').slice(-1);
                return `${this.env._t('Time Off :')} ${duration}`;
            } else {
                return this.props.record.display_name;
            }
        }
    }
    TimeOffCalendarPopover.template = 'hr_holidays.CalendarPopover';

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

    class TimeOffPopoverRenderer extends CalendarRenderer {
        get _displayCalendarMini() {
            return false;
        }
        _getPopoverData(event) {
            const data = super._getPopoverData(...arguments);
            const state = event.extendedProps.record.state;
            let calendarIcon;
            if (state === 'validate') {
                calendarIcon = 'fa-calendar-check-o';
            } else if (state === 'refuse') {
                calendarIcon = 'fa-calendar-times-o';
            } else if(state) {
                calendarIcon = 'fa-calendar-o';
            }

            return Object.assign(data, {
                title: data.title.split(':').slice(0, -1).join(':'),
                calendarIcon,
            });
        }
    }
    TimeOffPopoverRenderer.components = {
        ...TimeOffPopoverRenderer.components,
        CalendarPopover: TimeOffCalendarPopover,
    };

    class TimeOffCalendarRenderer extends TimeOffPopoverRenderer {
        /**
         * @override
         */
        async willStart() {
            await super.willStart();
            this.timeoffs = await this.fetchTimeoffs();
        }
        /**
         * @override
         */
        async willUpdateProps() {
            await super.willUpdateProps(...arguments);
            this.timeoffs = await this.fetchTimeoffs();
        }
        /**
         * @returns {Promise}
         */
        fetchTimeoffs() {
            return this.env.services.rpc({
                model: 'hr.leave.type',
                method: 'get_days_all_request',
                context: this.props.context,
            });
        }
    }
    TimeOffCalendarRenderer.template = 'hr_holidays.CalendarView';

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
