odoo.define('/web/static/src/js/libs/fullcalendar.js', function () {
    "use strict";

    function createYearCalendarView(FullCalendar) {
        const {
            Calendar,
            createElement,
            EventApi,
            memoizeRendering,
            View,
        } = FullCalendar;

        class YearView extends View {
            constructor() {
                super(...arguments);
                this.months = null;
                this.renderSubCalendarsMem = memoizeRendering(
                    this.renderSubCalendars, this.unrenderSubCalendars);
                this.events = [];
            }

            //----------------------------------------------------------------------
            // Getters
            //----------------------------------------------------------------------

            get currentDate() {
                return this.context.calendar.state.currentDate;
            }

            //----------------------------------------------------------------------
            // Public
            //----------------------------------------------------------------------

            /**
             * @override
             */
            destroy() {
                this.renderSubCalendarsMem.unrender();
                super.destroy();
            }
            /**
             * Removes the selection on sub calendar.
             * Selections on sub calendars are not propagated to this view so
             * this view cannot manage them.
             */
            unselect() {
                for (const { calendar } of this.months) {
                    calendar.unselect();
                }
            }
            /**
             * @override
             */
            render() {
                this.renderSubCalendarsMem(this.context);
                super.render(...arguments);
            }
            /**
             * Renders the main layout (the 4x3 month grid)
             */
            renderSubCalendars() {
                this.el.classList.add('fc-scroller');
                if (!this.context.options.selectable) {
                    this.el.classList.add('fc-readonly-year-view');
                }
                this.months = [];
                for (let monthNumber = 0; monthNumber < 12; monthNumber++) {
                    const monthDate = new Date(this.currentDate.getFullYear(), monthNumber);
                    const monthShortName = moment(monthDate).format('MMM').toLowerCase();
                    const container = createElement('div', { class: 'fc-month-container' });
                    this.el.appendChild(container);
                    const el = createElement('div', {
                        class: `fc-month fc-month-${monthShortName}`,
                    });
                    container.appendChild(el);
                    const calendar = this._createMonthCalendar(el, monthDate);
                    this.months.push({ el, calendar });
                    calendar.render();
                }
            }
            /**
             * Removes the main layout (the 4x3 month grid).
             * Called when view is switched/destroyed.
             */
            unrenderSubCalendars() {
                for (const { el, calendar } of this.months) {
                    calendar.destroy();
                    el.remove();
                }
            }
            /**
             * Renders events in sub calendars.
             * Called every time event source changed (when changing the date,
             *   when changing filters, adding/removing filters).
             */
            renderEvents() {
                // `renderDates` also renders events so if it's called just before
                // then do not execute this as it will do a re-render.
                if (this.datesRendered) {
                    this.datesRendered = false;
                    return;
                }
                this.events = this._computeEvents();
                for (const { calendar } of this.months) {
                    calendar.refetchEvents();
                }
                this._setCursorOnEventDates();
            }
            /**
             * Renders dates and events in sub calendars.
             * Called when the year of the date changed to render a new
             * 4*3 grid of month calendar based on the new year.
             */
            renderDates() {
                this.events = this._computeEvents();
                for (const [monthNumber, { calendar }] of Object.entries(this.months)) {
                    const monthDate = new Date(this.currentDate.getFullYear(), monthNumber);
                    calendar.gotoDate(monthDate);
                }
                this._setCursorOnEventDates();
                this.datesRendered = true;
            }

            //----------------------------------------------------------------------
            // Private
            //----------------------------------------------------------------------

            /**
             * @private
             */
            _computeEvents() {
                const calendar = this.context.calendar;
                return calendar.getEvents().map(event => {
                    const endUTC = calendar.dateEnv.toDate(event._instance.range.end);
                    const end = new Date(event._instance.range.end);
                    if (endUTC.getHours() > 0 || endUTC.getMinutes() > 0 ||
                        endUTC.getSeconds() > 0 || endUTC.getMilliseconds() > 0) {
                        end.setDate(end.getDate() + 1);
                    }
                    // clone event data to not trigger rerendering and issues
                    const instance = Object.assign({}, event._instance, {
                        range: { start: new Date(event._instance.range.start), end },
                    });
                    const def = Object.assign({}, event._def, {
                        rendering: 'background',
                        allDay: true,
                    });
                    return new EventApi(this.context.calendar, def, instance);
                });
            }
            /**
             * Create a month calendar for the date `monthDate` and mount it on container.
             *
             * @private
             * @param {HTMLElement} container
             * @param {Date} monthDate
             */
            _createMonthCalendar(container, monthDate) {
                return new Calendar(container, Object.assign({}, this.context.options, {
                    defaultDate: monthDate,
                    defaultView: 'dayGridMonth',
                    header: { left: false, center: 'title', right: false },
                    titleFormat: { month: 'short', year: 'numeric' },
                    height: 0,
                    contentHeight: 0,
                    weekNumbers: false,
                    showNonCurrentDates: false,
                    views: {
                        dayGridMonth: {
                            columnHeaderText: (date) => moment(date).format("ddd")[0],
                        },
                    },
                    selectMinDistance: 5, // needed to not trigger select when click
                    dateClick: this._onYearDateClick.bind(this),
                    datesRender: undefined,
                    events: (info, successCB) => {
                        successCB(this.events);
                    },
                    windowResize: undefined,
                }));
            }
            /**
             * Sets fc-has-event class on every dates that have at least one event.
             *
             * @private
             */
            _setCursorOnEventDates() {
                for (const el of this.el.querySelectorAll('.fc-has-event')) {
                    el.classList.remove('fc-has-event');
                }
                for (const event of Object.values(this.events)) {
                    let currentDate = moment(event._instance.range.start);
                    while (currentDate.isBefore(event._instance.range.end, 'day')) {
                        const formattedDate = currentDate.format('YYYY-MM-DD');
                        const el = this.el.querySelector(`.fc-day-top[data-date="${formattedDate}"]`);
                        if (el) {
                            el.classList.add('fc-has-event');
                        }
                        currentDate.add(1, 'days');
                    }
                }
            }

            //----------------------------------------------------------------------
            // Handlers
            //----------------------------------------------------------------------

            /**
             * @private
             * @param {*} info
             */
            _onYearDateClick(info) {
                const calendar = this.context.calendar;
                const events = this.events
                    .filter(event => {
                        const start = moment(event.start);
                        const end = moment(event.end);
                        const inclusivity = start.isSame(end, 'day') ? '[]' : '[)';
                        return moment(info.date).isBetween(start, end, 'day', inclusivity);
                    })
                    .map(event => {
                        return Object.assign({}, event._def, event._instance.range);
                    });
                const yearDateInfo = Object.assign({}, info, {
                    view: this,
                    monthView: info.view,
                    events,
                    selectable: this.context.options.selectable,
                });
                calendar.publiclyTrigger('yearDateClick', [yearDateInfo]);
            }
        }

        return FullCalendar.createPlugin({
            views: {
                dayGridYear: {
                    class: YearView,
                    duration: { years: 1 },
                    defaults: {
                        fixedWeekCount: true,
                    },
                },
            },
        });
    }

    return {
        createYearCalendarView,
    };
});
