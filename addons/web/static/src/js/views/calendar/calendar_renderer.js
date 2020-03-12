odoo.define('web.CalendarRenderer', function (require) {
    "use strict";

    const OwlAbstractRenderer = require('web.AbstractRendererOwl');
    const CalendarPopover = require('web.CalendarPopover');
    var { ComponentAdapter } = require('web.OwlCompatibility');
    const config = require('web.config');
    const core = require('web.core');
    const Dialog = require('web.Dialog');
    const fieldUtils = require('web.field_utils');
    const FieldManagerMixin = require('web.FieldManagerMixin');
    const relationalFields = require('web.relational_fields');
    const session = require('web.session');

    const { useRef, onMounted, onPatched } = owl.hooks;
    const { Component } = owl;
    const _t = core._t;

    const scales = {
        day: 'agendaDay',
        week: 'agendaWeek',
        month: 'month'
    };

    const SidebarFilterM2O = relationalFields.FieldMany2One.extend({
        _getSearchBlacklist() {
            return this._super(...arguments).concat(this.filter_ids || []);
        },
    });
    /**
     * Owl Component Adapter for relationalFields.FieldMany2One (Odoo Widget)
     * TODO: Remove this adapter when relationalFields.FieldMany2One is a Component
     */
    class SidebarFilterM2OAdapter extends ComponentAdapter {
        constructor(parent, props) {
            super(...arguments);
        }

        patched() {
            this.widget._reset(this.widget.record);
        }
    }


    class CalendarMini extends Component {
        mounted() {
            $(this.el).datepicker({
                'onSelect': (datum, obj) => {
                    this.trigger('changeDate', {
                        date: moment(new Date(+obj.currentYear, +obj.currentMonth, +obj.currentDay))
                    });
                },
                'showOtherMonths': true,
                'dayNamesMin': this.props.fc_options.dayNamesShort,
                'monthNames': this.props.fc_options.monthNamesShort,
                'firstDay': this.props.fc_options.firstDay,
            });
        }
    }

    CalendarMini.template = 'Calendar.sidebar.calendarMini';

    class SidebarFilter extends Component {
        constructor(parent, props) {
            super(...arguments);
            FieldManagerMixin.init.call(this);

            this.isSwipeEnabled = true;
            this.uniqueId = _.uniqueId; // underscore method used in template
            this.SidebarFilterM2O = SidebarFilterM2O;
            this.SidebarFilterM2ORef = useRef(`SidebarM2O_${props.fieldName}`);

            onMounted(() => this._render());

            onPatched(() => this._render());

        }
        /**
         * @override
         */
        async willStart() {
            await super.willStart(...arguments);

            if (this.props.write_model || this.props.write_field) {
                const m2oRecordID = await this.model.makeRecord(this.props.write_model, [{
                    name: this.props.write_field,
                    relation: this.props.fields[this.props.fieldName].relation,
                    type: 'many2one',
                }]);
                this.m2oRecord = this.model.get(m2oRecordID);
            }
        }

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        getSidebarM2OOptions() {
            return {
                mode: 'edit',
                attrs: {
                    placeholder: `+ ${_t(`Add ${this.props.title}`)}`,
                    can_create: false
                },
            };
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        _render() {
            if (this.SidebarFilterM2ORef && this.SidebarFilterM2ORef.comp) {
                this.SidebarFilterM2ORef.comp.widget.filter_ids = _.without(this.props.filters.map(f => f.value), 'all');
            }
            // Dispose of filter popover
            $(this.el).find('.o_calendar_filter_item').popover('dispose');
            // Show filter popover
            if (this.props.avatar_field) {
                this.props.filters.forEach((f) => {
                    if (f.value !== 'all') {
                        const selector = `.o_calendar_filter_item[data-value='${f.value}']`;
                        $(this.el).find(selector).popover({
                            animation: false,
                            trigger: 'hover',
                            html: true,
                            placement: 'top',
                            title: f.label,
                            delay: { show: 300, hide: 0 },
                            content: () => {
                                return $('<img>', {
                                    src: `/web/image/${this.props.avatar_model}/${f.value}/${this.props.avatar_field}`,
                                    class: 'mx-auto',
                                });
                            },
                        });
                    }
                });
            }
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {OdooEvent} event
         */
        async _onFieldChanged(event) {
            event.stopPropagation();
            const createValues = { 'user_id': session.uid };
            const value = event.detail.changes[this.props.write_field].id;
            createValues[this.props.write_field] = value;
            await this.rpc({
                model: this.props.write_model,
                method: 'create',
                args: [createValues],
            });
            this.trigger('changeFilter', {
                'fieldName': this.props.fieldName,
                'value': value,
                'active': true,
            });
        }
        /**
         * @private
         * @param {MouseEvent} e
         */
        _onFilterActive(e) {
            const input = e.currentTarget;
            const value = input.closest('.o_calendar_filter_item').getAttribute('data-value');
            this.trigger('changeFilter', {
                'fieldName': this.props.fieldName,
                'value': value === 'all' ? value : parseInt(value),
                'active': input.checked,
            });
        }
        /**
         * @private
         * @param {MouseEvent} e
         */
        _onFilterRemove(e) {
            const self = this;
            const filter = (e.currentTarget).closest('.o_calendar_filter_item');
            Dialog.confirm(this, _t("Do you really want to delete this filter from favorites ?"), {
                confirm_callback: function () {
                    self.rpc({
                        model: self.props.write_model,
                        method: 'unlink',
                        args: [[parseInt(filter.getAttribute('data-id'))]],
                    }).then(function () {
                        self.trigger('changeFilter', {
                            'fieldName': self.props.fieldName,
                            'id': parseInt(filter.getAttribute('data-id')),
                            'active': false,
                            'value': parseInt(filter.getAttribute('data-value')),
                        });
                    });
                },
            });
        }
    }

    SidebarFilter.template = 'Calendar.sidebar.filter';
    SidebarFilter.components = { SidebarFilterM2OAdapter };
    // copy methods of FieldManagerMixin into SidebarFilter
    // We need something like: https://hacks.mozilla.org/2015/08/es6-in-depth-subclassing/
    _.defaults(SidebarFilter.prototype, FieldManagerMixin);

    class SidebarFilters extends Component {
        constructor(parent, props) {
            super(...arguments);
            const arrFilters = _.toArray(this.props.filters);
            this.filterRefs = [];
            arrFilters.forEach((filter) => {
                const key = `filter_${filter.fieldName}`;
                this.filterRefs.push(useRef(key));
            });
        }

        hasDisplay(filter) {
            return filter.filters.find(function (f) { return f.display == null || f.display; })
        }
    }

    SidebarFilters.template = 'Calendar.sidebar.filters';
    SidebarFilters.components = { SidebarFilter };

    class OwlCalendarRenderer extends OwlAbstractRenderer {

        constructor(parent, props) {
            super(...arguments);
            this.model = props.model;
            this.filters = [];
            this.color_map = {};
            this.hideDate = props.hideDate;
            this.hideTime = props.hideTime;
            this.canDelete = props.canDelete;
            this.getColorBound = this.getColor.bind(this);

            onMounted(() => this._render());

            onPatched(() => this._render());
        }
        willUnmount() {
            if (this.$calendar) {
                this.$calendar.fullCalendar('destroy');
            }
            if (this.$small_calendar) {
                this.$small_calendar.datepicker('destroy');
                $('#ui-datepicker-div:empty').remove();
            }
        }
        /**
         * @override
         */
        mounted() {
            this._initCalendar();
            // TODO: MSH: Remove jQuery wrap here
            this.$small_calendar = $(this.el.querySelector(".o_calendar_mini"));
            this.sidebar = this.el.querySelector('.o_calendar_sidebar');
            this.sidebar_container = this.el.querySelector(".o_calendar_sidebar_container");
            if (config.device.isMobile) {
                this._bindSwipe();
            }
            if (config.device.isMobile) {
                this.el.style.height = (window.screen.height - this.el.getBoundingClientRect().top) + "px";
            }
            var scrollTop = this.calendar.querySelector('.fc-scroller').scrollTop;
            if (scrollTop) {
                this.$calendar.fullCalendar('reinitView');
            } else {
                this.$calendar.fullCalendar('render');
            }
        }

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * Note: this is not dead code, it is called by two template
         *
         * @param {any} key
         * @returns {integer}
         */
        getColor(key) {
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
            const index = (((Object.keys(this.color_map).length + 1) * 5) % 24) + 1;
            this.color_map[key] = index;
            return index;
        }
        // TODO: MSH: following two methods are not called
        /**
         * @override
         */
        getLocalState() {
            debugger;
            const fcScroller = this.calendar.querySelector('.fc-scroller');
            return {
                scrollPosition: fcScroller.scrollTop,
            };
        }
        /**
         * @override
         */
        setLocalState(localState) {
            debugger;
            if (localState.scrollPosition) {
                const fcScroller = this.calendar.querySelector('.fc-scroller');
                fcScroller.scrollTop = localState.scrollPosition;
            }
        }


        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @private
         * Bind handlers to enable swipe navigation
         *
         * @private
         */
        _bindSwipe() {
            const self = this;
            let touchStartX;
            let touchEndX;
            this.$calendar.on('touchstart', function (event) {
                touchStartX = event.originalEvent.touches[0].pageX;
            });
            this.$calendar.on('touchend', function (event) {
                touchEndX = event.originalEvent.changedTouches[0].pageX;
                if (!self.isSwipeEnabled) {
                    return;
                }
                if (touchStartX - touchEndX > 100) {
                    self.trigger('next');
                } else if (touchStartX - touchEndX < -100) {
                    self.trigger('prev');
                }
            });
        }
        /**
         * @param {any} event
         * @returns {string} the html for the rendered event
         */
        _eventRender(event) {
            const qwebContext = {
                event: event,
                record: event.record,
                color: this.getColor(event.color_index),
            };
            this.qweb_context = qwebContext;
            if (_.isEmpty(qwebContext.record)) {
                return '';
            } else {
                return this.env.qweb.renderToString("calendar-box", qwebContext);
            }
        }

        /**
         * @private
         * @param {any} record
         * @param {any} fieldName
         * @returns {string}
         */
        _format(record, fieldName) {
            const field = this.props.fields[fieldName];
            if (field.type === "one2many" || field.type === "many2many") {
                return fieldUtils.format[field.type]({ data: record[fieldName] }, field);
            } else {
                return fieldUtils.format[field.type](record[fieldName], field, { forceString: true });
            }
        }
        /**
         * Returns the time format from database parameters (only hours and minutes).
         * FIXME: this looks like a weak heuristic...
         *
         * @private
         * @returns {string}
         */
        _getDbTimeFormat() {
            return _t.database.parameters.time_format.search('%H') !== -1 ? 'HH:mm' : 'hh:mm a';
        }
        /**
         * Prepare context to display in the popover.
         *
         * @private
         * @param {Object} eventData
         * @returns {Object} context
         */
        _getPopoverContext(eventData) {
            const context = {
                canDelete: this.canDelete,
                displayFields: this.props.displayFields,
                event: eventData,
                eventDate: {},
                eventTime: {},
                fields: this.props.fields,
                hideDate: this.hideDate,
                hideTime: this.hideTime,
                modelName: this.model,
            };

            const start = moment(eventData.r_start || eventData.start);
            const end = moment(eventData.r_end || eventData.end);
            const isSameDayEvent = start.clone().add(1, 'minute').isSame(end.clone().subtract(1, 'minute'), 'day');

            // Do not display timing if the event occur across multiple days. Otherwise use user's timing preferences
            if (!this.hideTime && !eventData.record.allday && isSameDayEvent) {
                // Fetch user's preferences
                const dbTimeFormat = _t.database.parameters.time_format.search('%H') != -1 ? 'HH:mm' : 'hh:mm a';

                context.eventTime.time = start.clone().format(dbTimeFormat) + ' - ' + end.clone().format(dbTimeFormat);

                // Calculate duration and format text
                const durationHours = moment.duration(end.diff(start)).hours();
                const durationHoursKey = (durationHours === 1) ? 'h' : 'hh';
                const durationMinutes = moment.duration(end.diff(start)).minutes();
                const durationMinutesKey = (durationMinutes === 1) ? 'm' : 'mm';

                const localeData = moment.localeData(); // i18n for 'hours' and "minutes" strings
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

                if (eventData.record.allday && isSameDayEvent) {
                    context.eventDate.duration = _t("All day");
                } else if (eventData.record.allday && !isSameDayEvent) {
                    const daysLocaleData = moment.localeData();
                    const days = moment.duration(end.diff(start)).days();
                    context.eventDate.duration = daysLocaleData.relativeTime(days, true, 'dd');
                }
            }

            return context;
        }
        /**
         * Prepare the parameters for the popover.
         * This allow the parameters to be extensible.
         *
         * @private
         * @param {Object} eventData
         */
        _getPopoverParams(eventData) {
            return {
                animation: false,
                delay: {
                    show: 50,
                    hide: 100
                },
                trigger: 'manual',
                html: true,
                title: eventData.record.display_name,
                template: this.env.qweb.renderToString('CalendarView.event.popover.placeholder', { color: this.getColor(eventData.color_index) }),
                container: eventData.allDay ? '.fc-view' : '.fc-scroller',
            };
        }
        /**
         * Initialize the main calendar
         *
         * @private
        */
        _initCalendar() {
            const self = this;

            this.calendar = this.el.querySelector(".o_calendar_widget");
            this.$calendar = $(this.calendar);

            // This seems like a workaround but apparently passing the locale
            // in the options is not enough. We should initialize it beforehand
            const locale = moment.locale();
            $.fullCalendar.locale(locale);

            //Documentation here : http://arshaw.com/fullcalendar/docs/
            const fcOptions = Object.assign({}, this.props.fc_options, {
                eventDrop: (event) => {
                    this.trigger('dropRecord', event);
                },
                eventResize: (event) => {
                    this._unselectEvent();
                    this.trigger('updateRecord', event);
                },
                eventClick: (eventData, ev) => {
                    this._unselectEvent();
                    const event = this.calendar.querySelector(`[data-event-id='${eventData.id}']`);
                    event.classList.add('o_cw_custom_highlight');
                    this._renderEventPopover(eventData, $(ev.currentTarget));
                },
                select: function (startDate, endDate) {
                    self.isSwipeEnabled = false;
                    // Clicking on the view, dispose any visible popover. Otherwise create a new event.
                    if (self.el.querySelector('.o_cw_popover')) {
                        self._unselectEvent();
                    } else {
                        const data = {start: startDate, end: endDate};
                        if (self.props.context.default_name) {
                            data.title = self.props.context.default_name;
                        }
                        self.trigger('openCreate', data);
                    }
                    self.$calendar.fullCalendar('unselect');
                },
                eventRender: function (event, element, view) {
                    self.isSwipeEnabled = false;
                    const $render = $(self._eventRender(event));
                    element.find('.fc-content').html($render.html());
                    element.addClass($render.attr('class'));
                    element.attr('data-event-id', event.id);

                    // Add background if doesn't exist
                    if (!element.find('.fc-bg').length) {
                        element.find('.fc-content').after($('<div/>', {class: 'fc-bg'}));
                    }

                    // For month view: Show background for all-day/multidate events only
                    if (view.name === 'month' && event.record) {
                        const start = event.r_start || event.start;
                        const end = event.r_end || event.end;
                        // Detect if the event occurs in just one day
                        // note: add & remove 1 min to avoid issues with 00:00
                        const isSameDayEvent = start.clone().add(1, 'minute').isSame(end.clone().subtract(1, 'minute'), 'day');
                        if (!event.record.allday && isSameDayEvent) {
                            // For month view: do not show background for non allday, single day events
                            element.addClass('o_cw_nobg');
                            if (event.showTime && !self.hideTime) {
                                const displayTime = start.format(self._getDbTimeFormat());
                                element.find('.fc-content .fc-time').text(displayTime);
                            }
                        }
                    }

                    // On double click, edit the event
                    element.on('dblclick', function () {
                        self.trigger('edit-event', {id: event.id});
                    });
                },
                eventAfterAllRender: function () {
                    self.isSwipeEnabled = true;
                },
                viewRender: (view) => {
                    // compute mode from view.name which is either 'month', 'agendaWeek' or 'agendaDay'
                    const mode = view.name === 'month' ? 'month' : (view.name === 'agendaWeek' ? 'week' : 'day');
                    this.trigger('viewUpdated', {
                        mode: mode,
                        title: view.title,
                    });
                },
                // Add/Remove a class on hover to style multiple days events.
                // The css ":hover" selector can't be used because these events
                // are rendered using multiple elements.
                eventMouseover: (eventData) => {
                    const event = this.calendar.querySelector(`[data-event-id='${eventData.id}']`);
                    event && event.classList.add('o_cw_custom_hover');
                },
                eventMouseout: (eventData) => {
                    const event = this.calendar.querySelector(`[data-event-id='${eventData.id}']`);
                    event && event.classList.remove('o_cw_custom_hover');
                },
                eventDragStart: (eventData) => {
                    const event = this.calendar.querySelector(`[data-event-id='${eventData.id}']`);
                    event.classList.add('o_cw_custom_hover');
                    this._unselectEvent();
                },
                eventResizeStart: (eventData) => {
                    const event = this.calendar.querySelector(`[data-event-id='${eventData.id}']`);
                    event.classList.add('o_cw_custom_hover');
                    this._unselectEvent();
                },
                eventLimitClick: () => {
                    this._unselectEvent();
                    return 'popover';
                },
                windowResize: () => {
                    this._render();
                },
                views: {
                    day: {
                        columnFormat: 'LL'
                    },
                    week: {
                        columnFormat: 'ddd D'
                    },
                    month: {
                        columnFormat: config.device.isMobile ? 'ddd' : 'dddd'
                    }
                },
                height: 'parent',
                unselectAuto: false,
                isRTL: _t.database.parameters.direction === "rtl",
                locale: locale, // reset locale when fullcalendar has already been instanciated before now
            });

            this.$calendar.fullCalendar(fcOptions);
        }
        /**
         * Finalise the popover
         *
         * @param {jQueryElement} $popoverElement
         * @param {web.CalendarPopover} calendarPopover
         * @private
         */
        _onPopoverShown($popoverElement, calendarPopover) {
            const $popover = $($popoverElement.data('bs.popover').tip);
            $popover.find('.o_cw_popover_close').on('click', this._unselectEvent.bind(this));
        }
        /**
         * Render the calendar view, this is the main entry point.
         *
         * @override method from AbstractRenderer
         * @private
         */
        _render() {
            const $calendar = this.$calendar;
            const fcView = this.calendar.querySelector('.fc-view');
            const scrollPosition = fcView.scrollLeft;

            fcView.scrollLeft = 0;
            $calendar.fullCalendar('unselect');

            if (scales[this.props.scale] !== $calendar.data('fullCalendar').getView().type) {
                $calendar.fullCalendar('changeView', scales[this.props.scale]);
            }

            if (this.target_date !== this.props.target_date.toString()) {
                $calendar.fullCalendar('gotoDate', moment(this.props.target_date));
                this.target_date = this.props.target_date.toString();
            }

            this.$small_calendar.datepicker("setDate", this.props.highlight_date.toDate())
                .find('.o_selected_range')
                .removeClass('o_color o_selected_range');
            let $a;
            switch (this.props.scale) {
                case 'month': $a = this.$small_calendar.find('td'); break;
                case 'week': $a = this.$small_calendar.find('tr:has(.ui-state-active)'); break;
                case 'day': $a = this.$small_calendar.find('a.ui-state-active'); break;
            }
            $a.addClass('o_selected_range');
            setTimeout(function () {
                $a.not('.ui-state-active').addClass('o_color');
            });

            fcView.scrollLeft = scrollPosition;

            this._unselectEvent();
            this._renderEvents();
            this.el.querySelector('.o_calendar_view').prepend(this.calendar);
        }
        /**
         * Render all events
         *
         * @private
        */
        _renderEvents() {
            this.$calendar.fullCalendar('removeEvents');
            this.$calendar.fullCalendar('addEventSource', this.props.data);
        }
        /**
         * Render event popover
         *
         * @private
         * @param {Object} eventData
         * @param {jQueryElement} $eventElement
         */
        _renderEventPopover(eventData, $eventElement) {
            const self = this;
            // Initialize popover widget
            const calendarPopover = new this.config.CalendarPopover(this, this._getPopoverContext(eventData));
            $eventElement.popover(
                this._getPopoverParams(eventData)
            ).on('shown.bs.popover', function () {
                const popover = $(this).data('bs.popover').tip;
                calendarPopover.mount(popover.querySelector('.o_cw_body'));
                self._onPopoverShown($(this), calendarPopover);
            }).popover('show');
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Remove highlight classes and dispose of popovers
         *
         * @private
        */
        _unselectEvent() {
            $(this.el).find('.fc-event').removeClass('o_cw_custom_highlight');
            $(this.el).find('.o_cw_popover').popover('dispose');
        }
        /**
         * @private
         * @param {OdooEvent} event
         */
        _onEditEvent(event) {
            this._unselectEvent();
            this.trigger('openEvent', {
                _id: event.detail.id,
                title: event.detail.title,
            });
        }
        /**
         * @private
         * @param {OdooEvent} event
         */
        _onDeleteEvent(event) {
            this._unselectEvent();
            this.trigger('deleteRecord', { id: event.detail.id});
        }
    }

    OwlCalendarRenderer.prototype.config = {
        CalendarPopover,
    };
    OwlCalendarRenderer.template = "web.OwlCalendarView";
    OwlCalendarRenderer.components = { CalendarMini, SidebarFilters };

    return OwlCalendarRenderer;

});
