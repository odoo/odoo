odoo.define('web.CalendarRenderer', function (require) {
"use strict";

var AbstractRenderer = require('web.AbstractRenderer');
var CalendarPopover = require('web.CalendarPopover');
var config = require('web.config');
var core = require('web.core');
var Dialog = require('web.Dialog');
var field_utils = require('web.field_utils');
var FieldManagerMixin = require('web.FieldManagerMixin');
var relational_fields = require('web.relational_fields');
var session = require('web.session');
var Widget = require('web.Widget');

var _t = core._t;
var qweb = core.qweb;

var scales = {
    day: 'timeGridDay',
    week: 'timeGridWeek',
    month: 'dayGridMonth'
};

var SidebarFilterM2O = relational_fields.FieldMany2One.extend({
    _getSearchBlacklist: function () {
        return this._super.apply(this, arguments).concat(this.filter_ids || []);
    },
});

var SidebarFilter = Widget.extend(FieldManagerMixin, {
    template: 'CalendarView.sidebar.filter',
    custom_events: _.extend({}, FieldManagerMixin.custom_events, {
        field_changed: '_onFieldChanged',
    }),
    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} options
     * @param {string} options.fieldName
     * @param {Object[]} options.filters A filter is an object with the
     *   following keys: id, value, label, active, avatar_model, color,
     *   can_be_removed
     * @param {Object} [options.favorite] this is an object with the following
     *   keys: fieldName, model, fieldModel
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        FieldManagerMixin.init.call(this);

        this.title = options.title;
        this.fields = options.fields;
        this.fieldName = options.fieldName;
        this.write_model = options.write_model;
        this.write_field = options.write_field;
        this.avatar_field = options.avatar_field;
        this.avatar_model = options.avatar_model;
        this.filters = options.filters;
        this.label = options.label;
        this.getColor = options.getColor;
    },
    /**
     * @override
     */
    willStart: function () {
        var self = this;
        var defs = [this._super.apply(this, arguments)];

        if (this.write_model || this.write_field) {
            var def = this.model.makeRecord(this.write_model, [{
                name: this.write_field,
                relation: this.fields[this.fieldName].relation,
                type: 'many2one',
            }]).then(function (recordID) {
                self.many2one = new SidebarFilterM2O(self,
                    self.write_field,
                    self.model.get(recordID),
                    {
                        mode: 'edit',
                        attrs: {
                            string: _t(self.fields[self.fieldName].string),
                            placeholder: "+ " + _.str.sprintf(_t("Add %s"), self.title),
                            can_create: false
                        },
                    });
            });
            defs.push(def);
        }
        return Promise.all(defs);

    },
    /**
     * @override
     */
    start: function () {
        this._super();
        if (this.many2one) {
            this.many2one.appendTo(this.$el);
            this.many2one.filter_ids = _.without(_.pluck(this.filters, 'value'), 'all');
        }
        this.$el.on('click', '.o_remove', this._onFilterRemove.bind(this));
        this.$el.on('click', '.o_calendar_filter_items input', this._onFilterActive.bind(this));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} event
     */
    _onFieldChanged: function (event) {
        var self = this;
        event.stopPropagation();
        var createValues = {'user_id': session.uid};
        var value = event.data.changes[this.write_field].id;
        createValues[this.write_field] = value;
        this._rpc({
                model: this.write_model,
                method: 'create',
                args: [createValues],
            })
            .then(function () {
                self.trigger_up('changeFilter', {
                    'fieldName': self.fieldName,
                    'value': value,
                    'active': true,
                });
            });
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onFilterActive: function (e) {
        var $input = $(e.currentTarget);
        this.trigger_up('changeFilter', {
            'fieldName': this.fieldName,
            'value': $input.closest('.o_calendar_filter_item').data('value'),
            'active': $input.prop('checked'),
        });
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onFilterRemove: function (e) {
        var self = this;
        var $filter = $(e.currentTarget).closest('.o_calendar_filter_item');
        Dialog.confirm(this, _t("Do you really want to delete this filter from favorites ?"), {
            confirm_callback: function () {
                self._rpc({
                        model: self.write_model,
                        method: 'unlink',
                        args: [[$filter.data('id')]],
                    })
                    .then(function () {
                        self.trigger_up('changeFilter', {
                            'fieldName': self.fieldName,
                            'id': $filter.data('id'),
                            'active': false,
                            'value': $filter.data('value'),
                        });
                    });
            },
        });
    },
});

return AbstractRenderer.extend({
    template: "CalendarView",
    config: {
        CalendarPopover: CalendarPopover,
    },
    custom_events: _.extend({}, AbstractRenderer.prototype.custom_events || {}, {
        edit_event: '_onEditEvent',
        delete_event: '_onDeleteEvent',
    }),

    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} state
     * @param {Object} params
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.displayFields = params.displayFields;
        this.model = params.model;
        this.filters = [];
        this.color_map = {};
        this.hideDate = params.hideDate;
        this.hideTime = params.hideTime;
        this.canDelete = params.canDelete;
        this._isInDOM = false;
    },
    /**
     * @override
     * @returns {Promise}
     */
    start: function () {
        this._initSidebar();
        this._initCalendar();
        return this._super();
    },
    /**
     * @override
     */
    on_attach_callback: function () {
        this._super(...arguments);
        this._isInDOM = true;
        // BUG Test ????
        // this.$el.height($(window).height() - this.$el.offset().top);
        this.calendar.render();
        this._renderCalendar();
    },
    /**
     * Called when the field is detached from the DOM.
     */
    on_detach_callback: function () {
        this._super(...arguments);
        this._isInDOM = false;
    },
    /**
     * @override
     */
    destroy: function () {
        if (this.calendar) {
            this.calendar.destroy();
        }
        if (this.$small_calendar) {
            this.$small_calendar.datepicker('destroy');
            $('#ui-datepicker-div:empty').remove();
        }
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Note: this is not dead code, it is called by the calendar-box template
     *
     * @param {any} record
     * @param {any} fieldName
     * @param {any} imageField
     * @returns {string[]}
     */
    getAvatars: function (record, fieldName, imageField) {
        var field = this.state.fields[fieldName];

        if (!record[fieldName]) {
            return [];
        }
        if (field.type === 'one2many' || field.type === 'many2many') {
            return _.map(record[fieldName], function (id) {
                return '<img src="/web/image/'+field.relation+'/'+id+'/'+imageField+'" />';
            });
        } else if (field.type === 'many2one') {
            return ['<img src="/web/image/'+field.relation+'/'+record[fieldName][0]+'/'+imageField+'" />'];
        } else {
            var value = this._format(record, fieldName);
            var color = this.getColor(value);
            if (isNaN(color)) {
                return ['<span class="o_avatar_square" style="background-color:'+color+';"/>'];
            }
            else {
                return ['<span class="o_avatar_square o_calendar_color_'+color+'"/>'];
            }
        }
    },
    /**
     * Note: this is not dead code, it is called by two template
     *
     * @param {any} key
     * @returns {integer}
     */
    getColor: function (key) {
        if (!key) {
            return;
        }
        if (this.color_map[key]) {
            return this.color_map[key];
        }
        // check if the key is a css color
        if (typeof key === 'string' && key.match(/^((#[A-F0-9]{3})|(#[A-F0-9]{6})|((hsl|rgb)a?\(\s*(?:(\s*\d{1,3}%?\s*),?){3}(\s*,[0-9.]{1,4})?\))|)$/i)) {
            return this.color_map[key] = key;
        }
        if (typeof key === 'number' && !(key in this.color_map)) {
            return this.color_map[key] = key;
        }
        var index = (((_.keys(this.color_map).length + 1) * 5) % 24) + 1;
        this.color_map[key] = index;
        return index;
    },
    /**
     * @override
     */
    getLocalState: function () {
        var fcScroller = this.calendarElement.querySelector('.fc-scroller');
        return {
            scrollPosition: fcScroller.scrollTop,
        };
    },
    /**
     * @override
     */
    setLocalState: function (localState) {
        if (localState.scrollPosition) {
            var fcScroller = this.calendarElement.querySelector('.fc-scroller');
            fcScroller.scrollTop = localState.scrollPosition;
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Convert the new format of Event from FullCalendar V4 to a Event FullCalendar V3
     * @param fc4Event
     * @return {Object} FullCalendar V3 Object Event
     * @private
     */
    _convertEventToFC3Event: function (fc4Event) {
        var event = fc4Event;
        if (!moment.isMoment(fc4Event.start)) {
            event = {
                id: fc4Event.id,
                title: fc4Event.title,
                start: moment(fc4Event.start).utcOffset(0, true),
                end: fc4Event.end && moment(fc4Event.end).utcOffset(0, true),
                allDay: fc4Event.allDay,
                color: fc4Event.color,
            };
            if (fc4Event.extendedProps) {
                event = Object.assign({}, event, {
                    r_start: fc4Event.extendedProps.r_start && moment(fc4Event.extendedProps.r_start).utcOffset(0, true),
                    r_end: fc4Event.extendedProps.r_end && moment(fc4Event.extendedProps.r_end).utcOffset(0, true),
                    record: fc4Event.extendedProps.record,
                    attendees: fc4Event.extendedProps.attendees,
                });
            }
        }
        return event;
    },
    /**
     * @param {any} event
     * @returns {string} the html for the rendered event
     */
    _eventRender: function (event) {
        var qweb_context = {
            event: event,
            record: event.extendedProps.record,
            color: this.getColor(event.extendedProps.color_index),
        };
        this.qweb_context = qweb_context;
        if (_.isEmpty(qweb_context.record)) {
            return '';
        } else {
            return qweb.render("calendar-box", qweb_context);
        }
    },
    /**
     * @private
     * @param {any} record
     * @param {any} fieldName
     * @returns {string}
     */
    _format: function (record, fieldName) {
        var field = this.state.fields[fieldName];
        if (field.type === "one2many" || field.type === "many2many") {
            return field_utils.format[field.type]({data: record[fieldName]}, field);
        } else {
            return field_utils.format[field.type](record[fieldName], field, {forceString: true});
        }
    },
    /**
     * Return the Object options for FullCalendar
     *
     * @private
     * @param {Object} fcOptions
     * @return {Object}
     */
    _getFullCalendarOptions: function (fcOptions) {
        var self = this;
        return Object.assign({}, this.state.fc_options, {
            plugins: [
                'moment',
                'interaction',
                'dayGrid',
                'timeGrid'
            ],
            eventDrop: function (eventDropInfo) {
                var event = self._convertEventToFC3Event(eventDropInfo.event);
                self.trigger_up('dropRecord', event);
            },
            eventResize: function (eventResizeInfo) {
                self._unselectEvent();
                var event = self._convertEventToFC3Event(eventResizeInfo.event);
                self.trigger_up('updateRecord', event);
            },
            eventClick: function (eventClickInfo) {
                var eventData = eventClickInfo.event;
                self._unselectEvent();
                $(self.calendarElement).find(_.str.sprintf('[data-event-id=%s]', eventData.id)).addClass('o_cw_custom_highlight');
                self._renderEventPopover(eventData, $(eventClickInfo.el));
            },
            select: function (selectionInfo) {
                // Clicking on the view, dispose any visible popover. Otherwise create a new event.
                if (self.$('.o_cw_popover').length) {
                    self._unselectEvent();
                } else {
                    var data = {start: selectionInfo.start, end: selectionInfo.end, allDay: selectionInfo.allDay};
                    if (self.state.context.default_name) {
                        data.title = self.state.context.default_name;
                    }
                    self.trigger_up('openCreate', self._convertEventToFC3Event(data));
                }
                self.calendar.unselect();
            },
            eventRender: function (info) {
                var event = info.event;
                var element = $(info.el);
                var view = info.view;
                var $render = $(self._eventRender(event));
                element.find('.fc-content').html($render.html());
                element.addClass($render.attr('class'));
                element.attr('data-event-id', event.id);

                // Add background if doesn't exist
                if (!element.find('.fc-bg').length) {
                    element.find('.fc-content').after($('<div/>', {class: 'fc-bg'}));
                }

                if (view.type === 'dayGridMonth' && event.extendedProps.record) {
                    var start = event.extendedProps.r_start || event.start;
                    var end = event.extendedProps.r_end || event.end;
                    // Detect if the event occurs in just one day
                    // note: add & remove 1 min to avoid issues with 00:00
                    var isSameDayEvent = moment(start).clone().add(1, 'minute').isSame(moment(end).clone().subtract(1, 'minute'), 'day');
                    if (!event.extendedProps.record.allday && isSameDayEvent) {
                        // For month view: do not show background for non allday, single day events
                        element.addClass('o_cw_nobg');
                        if (event.extendedProps.showTime && !self.hideTime) {
                            const displayTime = moment(start).clone().format(self._getDbTimeFormat());
                            element.find('.fc-content .fc-time').text(displayTime);
                        }
                    }
                }

                // On double click, edit the event
                element.on('dblclick', function () {
                    self.trigger_up('edit_event', {id: event.id});
                });
            },
            datesRender: function (info) {
                // compute mode from view.type which is either 'dayGridMonth', 'timeGridWeek' or 'timeGridDay'
                var mode = info.view.type === 'dayGridMonth' ? 'month' : (info.view.type === 'timeGridWeek' ? 'week' : 'day');
                self.trigger_up('viewUpdated', {
                    mode: mode,
                    title: info.view.title,
                });
            },
            // Add/Remove a class on hover to style multiple days events.
            // The css ":hover" selector can't be used because these events
            // are rendered using multiple elements.
            eventMouseEnter: function (mouseEnterInfo) {
                $(self.calendarElement).find(_.str.sprintf('[data-event-id=%s]', mouseEnterInfo.event.id)).addClass('o_cw_custom_hover');
            },
            eventMouseLeave: function (mouseLeaveInfo) {
                if (!mouseLeaveInfo.event.id) {
                    return;
                }
                $(self.calendarElement).find(_.str.sprintf('[data-event-id=%s]', mouseLeaveInfo.event.id)).removeClass('o_cw_custom_hover');
            },
            eventDragStart: function (mouseDragInfo) {
                $(self.calendarElement).find(_.str.sprintf('[data-event-id=%s]', mouseDragInfo.event.id)).addClass('o_cw_custom_hover');
                self._unselectEvent();
            },
            eventResizeStart: function (mouseResizeInfo) {
                $(self.calendarElement).find(_.str.sprintf('[data-event-id=%s]', mouseResizeInfo.event.id)).addClass('o_cw_custom_hover');
                self._unselectEvent();
            },
            eventLimitClick: function () {
                self._unselectEvent();
                return 'popover';
            },
            windowResize: function () {
                self._render();
            },
            views: {
                timeGridDay: {
                    columnHeaderFormat: 'LL'
                },
                timeGridWeek: {
                    columnHeaderFormat: 'ddd D'
                },
                dayGridMonth: {
                    columnHeaderFormat: 'dddd'
                }
            },
            height: 'parent',
            unselectAuto: false,
            dir: _t.database.parameters.direction,
        }, fcOptions);
    },
    /**
     * Initialize the main calendar
     *
     * @private
     */
    _initCalendar: function () {
        this.calendarElement = this.$(".o_calendar_widget")[0];
        var locale = moment.locale();

        var fcOptions = this._getFullCalendarOptions({
            locale: locale, // reset locale when fullcalendar has already been instanciated before now
        });

        this.calendar = new FullCalendar.Calendar(this.calendarElement, fcOptions);
    },
    /**
     * Initialize the mini calendar in the sidebar
     *
     * @private
     */
    _initCalendarMini: function () {
        var self = this;
        this.$small_calendar = this.$(".o_calendar_mini");
        this.$small_calendar.datepicker({
            'onSelect': function (datum, obj) {
                self.trigger_up('changeDate', {
                    date: moment(new Date(+obj.currentYear , +obj.currentMonth, +obj.currentDay))
                });
            },
            'showOtherMonths': true,
            'dayNamesMin' : this.state.fc_options.dayNamesShort,
            'monthNames': this.state.fc_options.monthNamesShort,
            'firstDay': this.state.fc_options.firstDay,
        });
    },
    /**
     * Initialize the sidebar
     *
     * @private
     */
    _initSidebar: function () {
        this.$sidebar = this.$('.o_calendar_sidebar');
        this.$sidebar_container = this.$(".o_calendar_sidebar_container");
        this._initCalendarMini();
    },
    /**
     * Finalise the popover
     *
     * @param {jQueryElement} $popoverElement
     * @param {web.CalendarPopover} calendarPopover
     * @private
     */
    _onPopoverShown: function ($popoverElement, calendarPopover) {
        var $popover = $($popoverElement.data('bs.popover').tip);
        $popover.find('.o_cw_popover_close').on('click', this._unselectEvent.bind(this));
        $popover.find('.o_cw_body').replaceWith(calendarPopover.$el);
    },
    /**
     * Render the calendar view, this is the main entry point.
     *
     * @override method from AbstractRenderer
     * @private
     * @returns {Promise}
     */
    _render: function () {
        this.$('.o_calendar_view')[0].prepend(this.calendarElement);
        if (this._isInDOM) {
            this._renderCalendar();
        }
        this.$small_calendar.datepicker("setDate", this.state.highlight_date.toDate())
                            .find('.o_selected_range')
                            .removeClass('o_color o_selected_range');
        var $a;
        switch (this.state.scale) {
            case 'month': $a = this.$small_calendar.find('td'); break;
            case 'week': $a = this.$small_calendar.find('tr:has(.ui-state-active)'); break;
            case 'day': $a = this.$small_calendar.find('a.ui-state-active'); break;
        }
        $a.addClass('o_selected_range');
        setTimeout(function () {
            $a.not('.ui-state-active').addClass('o_color');
        });

        var filterProm = this._renderFilters();

        return Promise.all([filterProm, this._super.apply(this, arguments)]);
    },
    /**
     * Render the specific code for the FullCalendar when it's in the DOM
     *
     * @private
     */
    _renderCalendar() {
        this.calendar.unselect();

        if (scales[this.state.scale] !== this.calendar.view.type) {
            this.calendar.changeView(scales[this.state.scale]);
        }

        if (this.target_date !== this.state.target_date.toString()) {
            this.calendar.gotoDate(moment(this.state.target_date).toDate());
            this.target_date = this.state.target_date.toString();
        }

        this._unselectEvent();
        this._renderEvents();
        // this._scrollToScrollTime();
    },
    /**
     * Render all events
     *
     * @private
     */
    _renderEvents: function () {
        this.calendar.getEvents().forEach(function(event) {
            event.remove();
        });
        this.calendar.addEventSource(this.state.data);
    },
    /**
     * Render all filters
     *
     * @private
     * @returns {Promise} resolved when all filters have been rendered
     */
    _renderFilters: function () {
        // Dispose of filter popover
        this.$('.o_calendar_filter_item').popover('dispose');
        _.each(this.filters || (this.filters = []), function (filter) {
            filter.destroy();
        });
        if (this.state.fullWidth) {
            return Promise.resolve();
        }
        return this._renderFiltersOneByOne();
    },
    /**
     * Renders each filter one by one, waiting for the first filter finished to
     * be rendered and appended to render the next one.
     * We need to do like this since render a filter is asynchronous, we don't
     * know which one will be appened at first and we want tp force them to be
     * rendered in order.
     *
     * @param {number} filterIndex if not set, 0 by default
     * @returns {Promise} resolved when all filters have been rendered
     */
    _renderFiltersOneByOne: function (filterIndex) {
        filterIndex = filterIndex || 0;
        var arrFilters = _.toArray(this.state.filters);
        var prom;
        if (filterIndex < arrFilters.length) {
            var options = arrFilters[filterIndex];
            if (!_.find(options.filters, function (f) {return f.display == null || f.display;})) {
                return this._renderFiltersOneByOne(filterIndex + 1);
            }

            var self = this;
            options.getColor = this.getColor.bind(this);
            options.fields = this.state.fields;
            var sidebarFilter = new SidebarFilter(self, options);
            prom = sidebarFilter.appendTo(this.$sidebar).then(function () {
                // Show filter popover
                if (options.avatar_field) {
                    _.each(options.filters, function (filter) {
                        if (!['all', false].includes(filter.value)) {
                            var selector = _.str.sprintf('.o_calendar_filter_item[data-value=%s]', filter.value);
                            sidebarFilter.$el.find(selector).popover({
                                animation: false,
                                trigger: 'hover',
                                html: true,
                                placement: 'top',
                                title: filter.label,
                                delay: {show: 300, hide: 0},
                                content: function () {
                                    return $('<img>', {
                                        src: _.str.sprintf('/web/image/%s/%s/%s', options.avatar_model, filter.value, options.avatar_field),
                                        class: 'mx-auto',
                                    });
                                },
                            });
                        }
                    });
                }
                return self._renderFiltersOneByOne(filterIndex + 1);
            });
            this.filters.push(sidebarFilter);
        }
        return Promise.resolve(prom);
    },
    /**
     * Returns the time format from database parameters (only hours and minutes).
     * FIXME: this looks like a weak heuristic...
     *
     * @private
     * @returns {string}
     */
    _getDbTimeFormat: function () {
        return _t.database.parameters.time_format.search('%H') !== -1 ? 'HH:mm' : 'hh:mm a';
    },
    /**
     * Prepare context to display in the popover.
     *
     * @private
     * @param {Object} eventData
     * @returns {Object} context
     */
    _getPopoverContext: function (eventData) {
        var context = {
            hideDate: this.hideDate,
            hideTime: this.hideTime,
            eventTime: {},
            eventDate: {},
            fields: this.state.fields,
            displayFields: this.displayFields,
            event: eventData,
            modelName: this.model,
            canDelete: this.canDelete,
        };

        var start = moment((eventData.extendedProps && eventData.extendedProps.r_start) || eventData.start);
        var end = moment((eventData.extendedProps && eventData.extendedProps.r_end) || eventData.end);
        var isSameDayEvent = start.clone().add(1, 'minute').isSame(end.clone().subtract(1, 'minute'), 'day');

        // Do not display timing if the event occur across multiple days. Otherwise use user's timing preferences
        if (!this.hideTime && !eventData.extendedProps.record.allday && isSameDayEvent) {
            var dbTimeFormat = this._getDbTimeFormat();

            context.eventTime.time = start.clone().format(dbTimeFormat) + ' - ' + end.clone().format(dbTimeFormat);

            // Calculate duration and format text
            var durationHours = moment.duration(end.diff(start)).hours();
            var durationHoursKey = (durationHours === 1) ? 'h' : 'hh';
            var durationMinutes = moment.duration(end.diff(start)).minutes();
            var durationMinutesKey = (durationMinutes === 1) ? 'm' : 'mm';

            var localeData = moment.localeData(); // i18n for 'hours' and "minutes" strings
            context.eventTime.duration = (durationHours > 0 ? localeData.relativeTime(durationHours, true, durationHoursKey) : '')
                    + (durationHours > 0 && durationMinutes > 0 ? ', ' : '')
                    + (durationMinutes > 0 ? localeData.relativeTime(durationMinutes, true, durationMinutesKey) : '');
        }

        if (!this.hideDate) {
            if (!isSameDayEvent && start.isSame(end, 'month')) {
                // Simplify date-range if an event occurs into the same month (eg. '4-5 August 2019')
                context.eventDate.date = start.clone().format('MMMM D') + '-' + end.clone().format('D, YYYY');
            } else {
                context.eventDate.date = isSameDayEvent ? start.clone().format('dddd, LL') : start.clone().format('LL') + ' - ' + end.clone().format('LL');
            }

            if (eventData.extendedProps.record.allday && isSameDayEvent) {
                context.eventDate.duration = _t("All day");
            } else if (eventData.extendedProps.record.allday && !isSameDayEvent) {
                var daysLocaleData = moment.localeData();
                var days = moment.duration(end.diff(start)).days();
                context.eventDate.duration = daysLocaleData.relativeTime(days, true, 'dd');
            }
        }

        return context;
    },
    /**
     * Prepare the parameters for the popover.
     * This allow the parameters to be extensible.
     *
     * @private
     * @param {Object} eventData
     */
    _getPopoverParams: function (eventData) {
        return {
            animation: false,
            delay: {
                show: 50,
                hide: 100
            },
            trigger: 'manual',
            html: true,
            title: eventData.extendedProps.record.display_name,
            template: qweb.render('CalendarView.event.popover.placeholder', {color: this.getColor(eventData.extendedProps.color_index)}),
            container: eventData.allDay ? '.fc-view' : '.fc-scroller',
        }
    },
    /**
     * Render event popover
     *
     * @private
     * @param {Object} eventData
     * @param {jQueryElement} $eventElement
     */
    _renderEventPopover: function (eventData, $eventElement) {
        var self = this;

        // Initialize popover widget
        var calendarPopover = new self.config.CalendarPopover(self, self._getPopoverContext(eventData));
        calendarPopover.appendTo($('<div>')).then(() => {
            $eventElement.popover(
                self._getPopoverParams(eventData)
            ).on('shown.bs.popover', function () {
                self._onPopoverShown($(this), calendarPopover);
            }).popover('show');
        });
    },
    /**
     * Scroll to the time set in the FullCalendar parameter
     * @private
     */
    _scrollToScrollTime: function () {
        var scrollTime = this.calendar.getOption('scrollTime');
        this.calendar.scrollToTime(scrollTime);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Remove highlight classes and dispose of popovers
     *
     * @private
     */
    _unselectEvent: function () {
        this.$('.fc-event').removeClass('o_cw_custom_highlight');
        this.$('.o_cw_popover').popover('dispose');
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onEditEvent: function (event) {
        this._unselectEvent();
        this.trigger_up('openEvent', {
            _id: event.data.id,
            title: event.data.title,
        });
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onDeleteEvent: function (event) {
        this._unselectEvent();
        this.trigger_up('deleteRecord', {id: parseInt(event.data.id, 10)});
    },
});

});
