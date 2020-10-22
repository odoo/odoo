odoo.define('web.CalendarRenderer', function (require) {
"use strict";

const AbstractRenderer = require('web.AbstractRendererOwl');
const { CalendarPopover, CalendarYearPopover } = require('web.CalendarPopover');
const Dialog = require('web.Dialog');
const FieldManagerMixin = require('web.FieldManagerMixin');
const { createYearCalendarView } = require('/web/static/src/js/libs/fullcalendar.js');
const { adaptFullCalendarEvent, FullCalendarAdapter } = require('web.FullCalendarAdapter');
const { ComponentAdapter } = require('web.OwlCompatibility');
const patchMixin = require('web.patchMixin');
const { FieldMany2One } = require('web.relational_fields');
const session = require('web.session');
const { generateID } = require('web.utils');
const Widget = require('web.Widget');

const {
    Component,
    hooks: {
        useRef,
        useState,
    },
} = owl;

/**
 * Checks if two dates are the same date.
 * We consider day+0 and day+1 at midnight to be the same days
 *
 * @param {Date} a
 * @param {Date} b
 */
function isSameDayEvent(a, b) {
    // Detect if the event occurs in just one day
    // note: add & remove 1 min to avoid issues with 00:00
    return moment(a).add(1, 'minute')
        .isSame(moment(b).subtract(1, 'minute'), 'day');
}

const FilterSelectorM2O = FieldMany2One.extend({
    init(parent, write_field, state, options) {
        this._super(...arguments);
        this.filter_ids = options.filter_ids;
    },
    _getSearchBlacklist() {
        return this._super(...arguments).concat(this.filter_ids || []);
    },
});

const FilterSelector = Widget.extend(FieldManagerMixin, {
    custom_events: _.extend({}, FieldManagerMixin.custom_events, {
        field_changed: '_onFieldChanged',
    }),
    /**
     * @constructor
     */
    init(parent, env, props) {
        this._super(...arguments);
        FieldManagerMixin.init.call(this);
        this.env = env;
        this.props = props;
        this.field = null;
    },
    /**
     * @override
     */
    async willStart() {
        await this._super(...arguments);
        await this._updateField();
    },
    /**
     * @override
     */
    async start() {
        this._super(...arguments);
        await this.field.appendTo(this.el);
    },
    async update(nextProps) {
        this.props = nextProps;
        await this._updateField();
        await this.field.appendTo(this.el);
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        this.field.destroy();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    async _updateField() {
        if (this.field) {
            this.field.destroy();
            this.field = null;
        }
        const recordId = await this.model.makeRecord(this.props.write_model, [{
            name: this.props.write_field,
            relation: this.props.fields[this.props.fieldName].relation,
            type: 'many2one',
        }]);
        this.field = new FilterSelectorM2O(this,
            this.props.write_field,
            this.model.get(recordId),
            {
                mode: 'edit',
                attrs: {
                    string: this.env._t(this.props.fields[this.props.fieldName].string),
                    placeholder: `+ ${this.env._t('Add')} ${this.props.title}`,
                    can_create: false,
                },
                filter_ids: this.props.filters
                    .map(x => x.value)
                    .filter(x => x !== 'all'),
            }
        );
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    async _onFieldChanged(ev) {
        ev.stopPropagation();
        const value = ev.data.changes[this.props.write_field].id;
        const createValues = {
            user_id: session.uid,
            [this.props.write_field]: value,
        };
        await this._rpc({
            model: this.props.write_model,
            method: 'create',
            args: [createValues],
        });
        this.trigger_up('changeFilter', {
            'fieldName': this.props.fieldName,
            'value': value,
            'active': true,
        });
    },
});

class FilterSelectorAdapter extends ComponentAdapter {
    constructor(parent, props) {
        props.Component = FilterSelector;
        super(...arguments);
    }
    get widgetArgs() {
        return [this.env, this.props];
    }
    async updateWidget(nextProps) {
        await this.widget.update(nextProps);
    }
    renderWidget() {
    }
}

class FilterSection extends Component {
    constructor() {
        super(...arguments);

        this.state = useState({
            isOpened: true,
        });
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    get _nextIdForLabel() {
        return `o_calendar_filter_item_${generateID()}`;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onToggle() {
        this.state.isOpened = !this.state.isOpened;
    }
    /**
     * @private
     * @param {number|string} value
     * @param {MouseEvent} ev
     */
    _onFilterToggle(value, ev) {
        this.trigger('changeFilter', {
            'fieldName': this.props.fieldName,
            'value': value,
            'active': ev.currentTarget.checked,
        });
    }
    /**
     * @private
     * @param {number|string} value
     * @param {number} [id]
     */
    _onFilterRemove(value, id) {
        const dialogTitle = this.env.
            _t('Do you really want to delete this filter from favorites ?');
        Dialog.confirm(this, dialogTitle, {
            confirm_callback: async () => {
                await this.env.services.rpc({
                    model: this.props.write_model,
                    method: 'unlink',
                    args: [[id]],
                });
                this.trigger('changeFilter', {
                    fieldName: this.props.fieldName,
                    id,
                    active: false,
                    value,
                });
            },
        });
    }
}
FilterSection.components = {
    FilterSelectorAdapter,
};
FilterSection.template = 'web.CalendarFilterSection';

class CalendarRenderer extends AbstractRenderer {
    constructor() {
        super(...arguments);

        this.calendarMiniRef = useRef('calendarMini');
        this.colorMap = {};
        this.scrollPosition = null;
        this.shouldUpdateCalendarMini = false;
        this.state = useState({
            displayPopover: false,
            popoverTarget: null,
            popoverProps: {
            },
        });
    }

    /**
     * @override
     */
    mounted() {
        super.mounted();

        if (this._displayCalendarMini) {
            $(this.calendarMiniRef.el).datepicker({
                'onSelect': this._onCalendarMiniSelect.bind(this),
                'showOtherMonths': true,
                'dayNamesMin' : this.props.fc_options.dayNamesShort.map(x => x[0]),
                'monthNames': this.props.fc_options.monthNamesShort,
                'firstDay': this.props.fc_options.firstDay,
            });
            this._updateCalendarMini();
        }

        const scrollerEl = this.el.querySelector('.o_calendar_widget .fc-scroller');
        if (this.scrollPosition && scrollerEl) {
            scrollerEl.scrollTop = this.scrollPosition;
        }
    }
    /**
     * @override
     */
    patched() {
        super.patched();

        if (this.shouldUpdateCalendarMini) {
            this._updateCalendarMini();
        }

        if (this.state.displayPopover && this.props.scale !== 'year') {
            for (const el of this._findEventElementsById(this.state.popoverProps.eventId)) {
                el.classList.add('o_cw_custom_highlight');
            }
        }
    }
    /**
     * @override
     */
    willUnmount() {
        super.willUnmount();

        const scrollerEl = this.el.querySelector('.o_calendar_widget .fc-scroller');
        if (scrollerEl) {
            this.scrollPosition = scrollerEl.scrollTop;
        }

        $(this.calendarMiniRef.el).datepicker('destroy');
        $('#ui-datepicker-div:empty').remove();
    }
    async willUpdateProps(nextProps) {
        await super.willUpdateProps(...arguments);

        const dateOrViewChanged =
            !this.props.target_date.isSame(nextProps.target_date, 'day') ||
            this.props.scalesInfo[this.props.scale] !== nextProps.scalesInfo[nextProps.scale];
        this.shouldUpdateCalendarMini = this._displayCalendarMini && dateOrViewChanged;

        if (dateOrViewChanged) {
            this._unselectEvent();
        }
    }

    //--------------------------------------------------------------------------
    // Getters
    //--------------------------------------------------------------------------

    /**
     * Returns the time format from database parameters (only hours and minutes).
     * FIXME: this looks like a weak heuristic...
     *
     * @private
     * @returns {string}
     */
    get _dbTimeFormat() {
        return this.env._t.database.parameters.time_format
            .search('%H') !== -1 ? 'HH:mm' : 'hh:mm a';
    }
    get _displayCalendarMini() {
        return true;
    }
    /**
     * Returns the props/options for FullCalendar
     *
     * @private
     * @return {Object}
     */
    get _fullCalendarProps() {
        const options = Object.assign({}, this.props.fc_options, {
            events: (_, onSuccess) => {
                onSuccess(this.props.data);
            },
            dir: this.env._t.database.parameters.direction,
            height: 'parent',
            locale: moment.locale(),
            plugins: [
                'moment',
                'interaction',
                'dayGrid',
                'timeGrid'
            ],
            unselectAuto: false,
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
            eventClick: this._onCalendarEventClick.bind(this),
            eventDragStart: this._onCalendarEventDragStart.bind(this),
            eventDrop: this._onCalendarEventDrop.bind(this),
            eventLimitClick: this._onCalendarEventLimitClick.bind(this),
            eventMouseEnter: this._onCalendarEventMouseEnter.bind(this),
            eventMouseLeave: this._onCalendarEventMouseLeave.bind(this),
            eventRender: this._onCalendarEventRender.bind(this),
            eventResize: this._onCalendarEventResize.bind(this),
            eventResizeStart: this._onCalendarEventResizeStart.bind(this),
            datesRender: this._onCalendarDatesRender.bind(this),
            select: this._onCalendarSelect.bind(this),
            yearDateClick: this._onCalendarYearDateClick.bind(this),
        });
        options.plugins.push(createYearCalendarView(FullCalendar, options));
        return options;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @param {any} event
     * @param {moment} displayTime
     * @returns {string} the html for the rendered event
     */
    _eventRender(event, displayTime) {
        const context = {
            event: event,
            record: event.extendedProps.record,
            color: this._getColor(event.extendedProps.color_index),
            displayTime,
        };
        if (!context.record || !Object.keys(context.record).length) {
            return '';
        } else {
            return this.env.qweb.renderToString("web.CalendarView.event", context);
        }
    }
    /**
     * @private
     * @param {any} key
     * @returns {integer}
     */
    _getColor(key) {
        if (!key) {
            return;
        }
        if (this.colorMap[key]) {
            return this.colorMap[key];
        }
        // check if the key is a css color
        const colorRegex = /^((#[A-F0-9]{3})|(#[A-F0-9]{6})|((hsl|rgb)a?\(\s*(?:(\s*\d{1,3}%?\s*),?){3}(\s*,[0-9.]{1,4})?\))|)$/i;
        if ((typeof key === 'string' && key.match(colorRegex)) ||
            (typeof key === 'number' && !(key in this.colorMap))
        ) {
            this.colorMap[key] = key;
        } else {
            const index = (((Object.keys(this.colorMap).length + 1) * 5) % 24) + 1;
            this.colorMap[key] = index;
        }
        return this.colorMap[key];
    }
    /**
     * Returns event's formatted date for popovers.
     *
     * @private
     * @param {moment} start
     * @param {moment} end
     * @param {boolean} showDayName
     * @param {boolean} allDay
     */
    _getFormattedDate(start, end, showDayName, allDay) {
        const isSameDay = isSameDayEvent(start, end);
        const isSameMonth = start.isSame(end, 'month');
        if (allDay) {
            // cancel correction done in _recordToCalendarEvent
            end = end.clone().subtract(1, 'day');
        }
        if (isSameDay) {
            return start.format(showDayName ? 'dddd, LL' : 'LL');
        } else if (isSameMonth) {
            // Simplify date-range if an event occurs into the same month (eg. '4-5 August 2019')
            return start.format('MMMM D') + '-' + end.format('D, YYYY');
        } else {
            return start.format('LL') + ' - ' + end.format('LL');
        }
    }
    /**
     * Prepare data to display in the popover.
     *
     * @private
     * @param {Object} event
     * @returns {Object}
     */
    _getPopoverData(event) {
        const data = {
            eventId: parseInt(event.id, 10),
            title: event.extendedProps.record.display_name,
            color: event.extendedProps.color_index,
            date: {
                hide: this.props.hideDate,
                value: null,
                duration: null,
            },
            time: {
                hide: this.props.hideTime,
                value: null,
                duration: null,
            },
            fields: this.props.fields,
            displayFields: this.props.displayFields,
            record: event.extendedProps.record,
            modelName: this.props.model,
            deletable: this.props.canDelete,
        };

        const start = moment((event.extendedProps &&
            event.extendedProps.r_start) || event.start);
        const end = moment((event.extendedProps &&
            event.extendedProps.r_end) || event.end);
        const localeData = moment.localeData();

        // Do not display timing if the event occur across multiple days.
        // Otherwise use user's timing preferences
        if (!this.props.hideTime &&
            !event.extendedProps.record.allday && isSameDayEvent(start, end)
        ) {
            const dbTimeFormat = this._dbTimeFormat;
            data.time.value =
                `${start.format(dbTimeFormat)} - ${end.format(dbTimeFormat)}`;

            // Calculate duration and format text
            const durationHours = moment.duration(end.diff(start)).hours();
            const durationHoursKey = (durationHours === 1) ? 'h' : 'hh';
            const durationMinutes = moment.duration(end.diff(start)).minutes();
            const durationMinutesKey = (durationMinutes === 1) ? 'm' : 'mm';
            // i18n for 'hours' and "minutes" strings
            const durationParts = [];
            if (durationHours > 0) {
                durationParts.push(
                    localeData.relativeTime(durationHours, true, durationHoursKey)
                );
            }
            if (durationMinutes > 0) {
                durationParts.push(
                    localeData.relativeTime(durationMinutes, true, durationMinutesKey)
                );
            }
            data.time.duration = durationParts.join(', ');
        }

        if (!this.props.hideDate) {
            if (event.extendedProps.record.allday && isSameDayEvent(start, end)) {
                data.date.duration = this.env._t("All day");
            } else if (event.extendedProps.record.allday && !isSameDayEvent(start, end)) {
                const days = moment.duration(end.diff(start)).days();
                data.date.duration = localeData.relativeTime(days, true, 'dd');
            }

            data.date.value = this._getFormattedDate(start, end, true,
                event.extendedProps.record.allday);
        }

        return data;
    }
    /**
     * @param {string} filterKey
     * @private
     */
    _getSidebarFilterProps(filterKey) {
        return Object.assign({}, this.props.filters[filterKey], {
            fields: this.props.fields,
            getColor: this._getColor.bind(this),
        });
    }
    /**
     * @private
     * @param {Date} date
     * @param {Array} events
     * @returns {Object}
     */
    _getYearPopoverData(date, events) {
        const groupKeys = [];
        const groupedEvents = {};
        for (const event of events) {
            const start = moment(event.extendedProps.r_start);
            const end = moment(event.extendedProps.r_end);
            const key = this._getFormattedDate(start, end, false, event.extendedProps.record.allday);
            if (!(key in groupedEvents)) {
                groupedEvents[key] = [];
                groupKeys.push({
                    key: key,
                    start: event.extendedProps.r_start,
                    end: event.extendedProps.r_end,
                    isSameDayEvent: isSameDayEvent(start, end),
                });
            }
            const record = event.extendedProps.record;
            groupedEvents[key].push({
                id: record.id,
                name: record.display_name,
            });
        }

        return {
            createable: this.props.canCreate,
            date,
            groupedEvents,
            groupKeys: groupKeys
                .sort((a, b) => {
                    if (a.isSameDayEvent) {
                        // if isSameDayEvent then put it before the others
                        return Number.MIN_SAFE_INTEGER;
                    } else if (b.isSameDayEvent) {
                        return Number.MAX_SAFE_INTEGER;
                    } else if (a.start.getTime() - b.start.getTime() === 0) {
                        return a.end.getTime() - b.end.getTime();
                    }
                    return a.start.getTime() - b.start.getTime();
                })
                .map(x => x.key),
        };
    }
    /**
     * Returns all HTMLElements that represent the event with the given id.
     *
     * @private
     * @param {Number} eventId
     */
    _findEventElementsById(eventId) {
        return this.el.querySelectorAll(`o_calendar_widget [data-event-id="${eventId}"]`);
    }
    /**
     * @private
     * @param {string} target
     * @param {Object} popoverProps
     */
    _selectEvent(target, popoverProps) {
        Object.assign(this.state, {
            displayPopover: true,
            popoverTarget: target,
            popoverProps: popoverProps,
        });
    }
    /**
     * @private
     */
    _updateCalendarMini() {
        const $calendarMini = $(this.calendarMiniRef.el);
        $calendarMini
            .datepicker("setDate", this.props.highlight_date.toDate())
            .find('.o_selected_range')
            .removeClass('o_color o_selected_range');
        let $a;
        switch (this.props.scale) {
            case 'year': $a = $calendarMini.find('td'); break;
            case 'month': $a = $calendarMini.find('td'); break;
            case 'week': $a = $calendarMini.find('tr:has(.ui-state-active)'); break;
            case 'day': $a = $calendarMini.find('a.ui-state-active'); break;
        }
        $a.addClass('o_selected_range');
        setTimeout(() => {
            $a.not('.ui-state-active').addClass('o_color');
        });
    }
    /**
     * Removes highlight classes and popover
     *
     * @private
     */
    _unselectEvent() {
        Object.assign(this.state, {
            displayPopover: false,
            popoverTarget: null,
            popoverProps: {
            },
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} info
     * @param {Object} info.event calendar event data
     * @param {Object} info.jsEvent interaction event
     */
    _onCalendarEventClick({ event, jsEvent: ev }) {
        ev.preventDefault();
        ev.stopPropagation();
        this._selectEvent(
            `.fc-event[data-event-id="${event.id}"]`,
            this._getPopoverData(event)
        );
    }
    /**
     * @private
     * @param {Object} info
     * @param {Object} info.event calendar event data
     */
    _onCalendarEventDragStart({ event }) {
        this._unselectEvent();
        for (const el of this._findEventElementsById(event.id)) {
            el.classList.add('o_cw_custom_hover');
        }
    }
    /**
     * @private
     * @param {Object} info
     * @param {Object} info.event calendar event data
     */
    _onCalendarEventDrop({ event }) {
        this.trigger('dropRecord', adaptFullCalendarEvent(event));
    }
    /**
     * @private
     */
    _onCalendarEventLimitClick() {
        this._unselectEvent();
        return 'popover';
    }
    /**
     * Add/Remove a class on hover to style multiple days events.
     * The css ":hover" selector can't be used because these events
     * are rendered using multiple elements.
     *
     * @private
     * @param {Object} info
     * @param {Object} info.event calendar event data
     */
    _onCalendarEventMouseEnter({ event }) {
        for (const el of this._findEventElementsById(event.id)) {
            el.classList.add('o_cw_custom_hover');
        }
    }
    /**
     * @private
     * @param {Object} info
     * @param {Object} info.event calendar event data
     */
    _onCalendarEventMouseLeave({ event }) {
        if (!event.id) {
            return;
        }
        for (const el of this._findEventElementsById(event.id)) {
            el.classList.remove('o_cw_custom_hover');
        }
    }
    /**
     * @private
     * @param {Object} info
     */
    _onCalendarEventRender({ event, el, view }) {
        el.setAttribute('data-event-id', event.id);
        if (this.props.scale === 'year') {
            const color = this._getColor(event.extendedProps.color_index);
            if (typeof color === 'string') {
                el.style.backgroundColor = color;
            } else if (typeof color === 'number') {
                el.classList.add(`o_calendar_color_${color}`);
            } else {
                el.classList.add('o_calendar_color_1');
            }
        } else {
            let displayTime = null;
            if (view.type === 'dayGridMonth' && event.extendedProps.record) {
                const start = event.extendedProps.r_start || event.start;
                const end = event.extendedProps.r_end || event.end;
                if (!event.extendedProps.record.allday && isSameDayEvent(start, end)) {
                    // For month view: do not show background for non allday, single day events
                    el.classList.add('o_cw_nobg');
                    if (event.extendedProps.showTime && !this.props.hideTime) {
                        displayTime = moment(start).format(this._dbTimeFormat);
                    }
                }
            }

            const fcContent = el.querySelector('.fc-content');
            const render = this._eventRender(event, displayTime);
            if (render) {
                const parser = new DOMParser();
                const renderEl = parser
                    .parseFromString(render, "application/xml")
                    .children[0];
                fcContent.innerHTML = renderEl.innerHTML;
                el.classList.add(...renderEl.classList.values());
                el.setAttribute('style', renderEl.getAttribute('style'));
            }

            // Add background if doesn't exist
            if (!el.querySelector('.fc-bg')) {
                const fcBg = document.createElement('div');
                fcBg.classList.add('fc-bg');
                fcContent.after(fcBg);
            }

            // On double click, edit the event
            el.addEventListener('dblclick', () => {
                this.trigger('edit_event', { id: event.id });
            });
        }
    }
    /**
     * @private
     * @param {Object} info
     * @param {Object} info.event calendar event data
     */
    _onCalendarEventResize({ event }) {
        this._unselectEvent();
        this.trigger('updateRecord', adaptFullCalendarEvent(event));
    }
    /**
     * @private
     * @param {Object} info
     * @param {Object} info.event calendar event data
     */
    _onCalendarEventResizeStart({ event }) {
        this._unselectEvent();
        for (const el of this._findEventElementsById(event.id)) {
            el.classList.add('o_cw_custom_hover');
        }
    }
    /**
     * @private
     * @param {Object} info
     * @param {Object} info.view current calendar view
     */
    _onCalendarDatesRender({ view }) {
        const viewToMode = Object.fromEntries(
            Object.entries(this.props.scalesInfo).map(([k, v]) => [v, k])
        );
        this.trigger('viewUpdated', {
            mode: viewToMode[view.type],
            title: view.title,
        });
    }
    /**
     * @private
     * @param {*} datum
     * @param {Object} obj
     */
    _onCalendarMiniSelect(datum, obj) {
        this.trigger('changeDate', {
            date: moment({
                year: +obj.currentYear,
                month: +obj.currentMonth,
                day: +obj.currentDay
            }),
        });
    }
    /**
     * @private
     * @param {Object} info
     * @param {Object} info.allDay tells if the event last all the day
     * @param {Object} info.start event start datetime
     * @param {Object} info.end event end datetime
     * @param {Object} info.view
     */
    _onCalendarSelect({ allDay, end, start, view }) {
        // Clicking on the view, dispose any visible popover.
        // Otherwise create a new event.
        if (this.state.displayPopover) {
            this._unselectEvent();
        }
        const data = { start, end, allDay };
        if (this.props.context.default_name) {
            data.title = this.props.context.default_name;
        }
        this.trigger('openCreate', adaptFullCalendarEvent(data));
        if (this.props.scale === 'year') {
            view.unselect();
        } else {
            view.context.calendar.unselect();
        }
    }
    /**
     * @private
     * @param {Object} info
     * @param {Date} info.date the date of the event clicked on
     * @param {Array} info.events list of event
     * @param {Object} info.view current calendar view (here dayGridYear)
     */
    _onCalendarYearDateClick({ date, events, view }) {
        this._unselectEvent();
        view.unselect();
        if (!events.length) {
            if (view.context.options.selectable) {
                const data = {
                    start: date,
                    allDay: true,
                };
                if (this.props.context.default_name) {
                    data.title = this.props.context.default_name;
                }
                this.trigger('openCreate', this._convertEventToFC3Event(data));
            }
        } else {
            const formattedDate = moment(date).format('YYYY-MM-DD');
            this._selectEvent(
                `.fc-day-top[data-date="${formattedDate}"]`,
                this._getYearPopoverData(date, events)
            );
        }
    }
    /**
     * @private
     * @param {CustomEvent} e
     */
    _onCreateEvent(e) {
        this._unselectEvent();
        const data = {
            start: e.detail,
            allDay: true,
        };
        if (this.props.context.default_name) {
            data.title = this.props.context.default_name;
        }
        this.trigger('openCreate', adaptFullCalendarEvent(data));
    }
    /**
     * @private
     * @param {CustomEvent} e
     */
    _onDeleteEvent(e) {
        this._unselectEvent();
        this.trigger('deleteRecord', {
            id: parseInt(e.detail.id, 10),
        });
    }
    /**
     * @private
     * @param {CustomEvent} e
     */
    _onEditEvent(e) {
        this._unselectEvent();
        this.trigger('openEvent', {
            _id: e.detail.id,
            title: e.detail.title,
        });
    }
    /**
     * @private
     * @param {CustomEvent} e
     */
    _onOpenEvent(e) {
        this._unselectEvent();
        this.trigger('openEvent', {
            _id: e.detail.id,
            title: e.detail.name,
        });
    }
    /**
     * @private
     * @param {CustomEvent} e
     */
    _onPopoverClose(e) {
        e.stopPropagation();
        e.preventDefault();
        this._unselectEvent();
    }
}
CalendarRenderer.components = {
    CalendarPopover,
    CalendarYearPopover,
    FilterSection,
    FullCalendarAdapter,
};
CalendarRenderer.template = 'web.CalendarView';

return patchMixin(CalendarRenderer);
});
