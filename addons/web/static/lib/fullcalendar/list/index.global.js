/*!
FullCalendar List View Plugin v6.1.15
Docs & License: https://fullcalendar.io/docs/list-view
(c) 2024 Adam Shaw
*/
FullCalendar.List = (function (exports, core, internal$1, preact) {
    'use strict';

    class ListViewHeaderRow extends internal$1.BaseComponent {
        constructor() {
            super(...arguments);
            this.state = {
                textId: internal$1.getUniqueDomId(),
            };
        }
        render() {
            let { theme, dateEnv, options, viewApi } = this.context;
            let { cellId, dayDate, todayRange } = this.props;
            let { textId } = this.state;
            let dayMeta = internal$1.getDateMeta(dayDate, todayRange);
            // will ever be falsy?
            let text = options.listDayFormat ? dateEnv.format(dayDate, options.listDayFormat) : '';
            // will ever be falsy? also, BAD NAME "alt"
            let sideText = options.listDaySideFormat ? dateEnv.format(dayDate, options.listDaySideFormat) : '';
            let renderProps = Object.assign({ date: dateEnv.toDate(dayDate), view: viewApi, textId,
                text,
                sideText, navLinkAttrs: internal$1.buildNavLinkAttrs(this.context, dayDate), sideNavLinkAttrs: internal$1.buildNavLinkAttrs(this.context, dayDate, 'day', false) }, dayMeta);
            // TODO: make a reusable HOC for dayHeader (used in daygrid/timegrid too)
            return (preact.createElement(internal$1.ContentContainer, { elTag: "tr", elClasses: [
                    'fc-list-day',
                    ...internal$1.getDayClassNames(dayMeta, theme),
                ], elAttrs: {
                    'data-date': internal$1.formatDayString(dayDate),
                }, renderProps: renderProps, generatorName: "dayHeaderContent", customGenerator: options.dayHeaderContent, defaultGenerator: renderInnerContent, classNameGenerator: options.dayHeaderClassNames, didMount: options.dayHeaderDidMount, willUnmount: options.dayHeaderWillUnmount }, (InnerContent) => ( // TODO: force-hide top border based on :first-child
            preact.createElement("th", { scope: "colgroup", colSpan: 3, id: cellId, "aria-labelledby": textId },
                preact.createElement(InnerContent, { elTag: "div", elClasses: [
                        'fc-list-day-cushion',
                        theme.getClass('tableCellShaded'),
                    ] })))));
        }
    }
    function renderInnerContent(props) {
        return (preact.createElement(preact.Fragment, null,
            props.text && (preact.createElement("a", Object.assign({ id: props.textId, className: "fc-list-day-text" }, props.navLinkAttrs), props.text)),
            props.sideText && ( /* not keyboard tabbable */preact.createElement("a", Object.assign({ "aria-hidden": true, className: "fc-list-day-side-text" }, props.sideNavLinkAttrs), props.sideText))));
    }

    const DEFAULT_TIME_FORMAT = internal$1.createFormatter({
        hour: 'numeric',
        minute: '2-digit',
        meridiem: 'short',
    });
    class ListViewEventRow extends internal$1.BaseComponent {
        render() {
            let { props, context } = this;
            let { options } = context;
            let { seg, timeHeaderId, eventHeaderId, dateHeaderId } = props;
            let timeFormat = options.eventTimeFormat || DEFAULT_TIME_FORMAT;
            return (preact.createElement(internal$1.EventContainer, Object.assign({}, props, { elTag: "tr", elClasses: [
                    'fc-list-event',
                    seg.eventRange.def.url && 'fc-event-forced-url',
                ], defaultGenerator: () => renderEventInnerContent(seg, context) /* weird */, seg: seg, timeText: "", disableDragging: true, disableResizing: true }), (InnerContent, eventContentArg) => (preact.createElement(preact.Fragment, null,
                buildTimeContent(seg, timeFormat, context, timeHeaderId, dateHeaderId),
                preact.createElement("td", { "aria-hidden": true, className: "fc-list-event-graphic" },
                    preact.createElement("span", { className: "fc-list-event-dot", style: {
                            borderColor: eventContentArg.borderColor || eventContentArg.backgroundColor,
                        } })),
                preact.createElement(InnerContent, { elTag: "td", elClasses: ['fc-list-event-title'], elAttrs: { headers: `${eventHeaderId} ${dateHeaderId}` } })))));
        }
    }
    function renderEventInnerContent(seg, context) {
        let interactiveAttrs = internal$1.getSegAnchorAttrs(seg, context);
        return (preact.createElement("a", Object.assign({}, interactiveAttrs), seg.eventRange.def.title));
    }
    function buildTimeContent(seg, timeFormat, context, timeHeaderId, dateHeaderId) {
        let { options } = context;
        if (options.displayEventTime !== false) {
            let eventDef = seg.eventRange.def;
            let eventInstance = seg.eventRange.instance;
            let doAllDay = false;
            let timeText;
            if (eventDef.allDay) {
                doAllDay = true;
            }
            else if (internal$1.isMultiDayRange(seg.eventRange.range)) { // TODO: use (!isStart || !isEnd) instead?
                if (seg.isStart) {
                    timeText = internal$1.buildSegTimeText(seg, timeFormat, context, null, null, eventInstance.range.start, seg.end);
                }
                else if (seg.isEnd) {
                    timeText = internal$1.buildSegTimeText(seg, timeFormat, context, null, null, seg.start, eventInstance.range.end);
                }
                else {
                    doAllDay = true;
                }
            }
            else {
                timeText = internal$1.buildSegTimeText(seg, timeFormat, context);
            }
            if (doAllDay) {
                let renderProps = {
                    text: context.options.allDayText,
                    view: context.viewApi,
                };
                return (preact.createElement(internal$1.ContentContainer, { elTag: "td", elClasses: ['fc-list-event-time'], elAttrs: {
                        headers: `${timeHeaderId} ${dateHeaderId}`,
                    }, renderProps: renderProps, generatorName: "allDayContent", customGenerator: options.allDayContent, defaultGenerator: renderAllDayInner, classNameGenerator: options.allDayClassNames, didMount: options.allDayDidMount, willUnmount: options.allDayWillUnmount }));
            }
            return (preact.createElement("td", { className: "fc-list-event-time" }, timeText));
        }
        return null;
    }
    function renderAllDayInner(renderProps) {
        return renderProps.text;
    }

    /*
    Responsible for the scroller, and forwarding event-related actions into the "grid".
    */
    class ListView extends internal$1.DateComponent {
        constructor() {
            super(...arguments);
            this.computeDateVars = internal$1.memoize(computeDateVars);
            this.eventStoreToSegs = internal$1.memoize(this._eventStoreToSegs);
            this.state = {
                timeHeaderId: internal$1.getUniqueDomId(),
                eventHeaderId: internal$1.getUniqueDomId(),
                dateHeaderIdRoot: internal$1.getUniqueDomId(),
            };
            this.setRootEl = (rootEl) => {
                if (rootEl) {
                    this.context.registerInteractiveComponent(this, {
                        el: rootEl,
                    });
                }
                else {
                    this.context.unregisterInteractiveComponent(this);
                }
            };
        }
        render() {
            let { props, context } = this;
            let { dayDates, dayRanges } = this.computeDateVars(props.dateProfile);
            let eventSegs = this.eventStoreToSegs(props.eventStore, props.eventUiBases, dayRanges);
            return (preact.createElement(internal$1.ViewContainer, { elRef: this.setRootEl, elClasses: [
                    'fc-list',
                    context.theme.getClass('table'),
                    context.options.stickyHeaderDates !== false ?
                        'fc-list-sticky' :
                        '',
                ], viewSpec: context.viewSpec },
                preact.createElement(internal$1.Scroller, { liquid: !props.isHeightAuto, overflowX: props.isHeightAuto ? 'visible' : 'hidden', overflowY: props.isHeightAuto ? 'visible' : 'auto' }, eventSegs.length > 0 ?
                    this.renderSegList(eventSegs, dayDates) :
                    this.renderEmptyMessage())));
        }
        renderEmptyMessage() {
            let { options, viewApi } = this.context;
            let renderProps = {
                text: options.noEventsText,
                view: viewApi,
            };
            return (preact.createElement(internal$1.ContentContainer, { elTag: "div", elClasses: ['fc-list-empty'], renderProps: renderProps, generatorName: "noEventsContent", customGenerator: options.noEventsContent, defaultGenerator: renderNoEventsInner, classNameGenerator: options.noEventsClassNames, didMount: options.noEventsDidMount, willUnmount: options.noEventsWillUnmount }, (InnerContent) => (preact.createElement(InnerContent, { elTag: "div", elClasses: ['fc-list-empty-cushion'] }))));
        }
        renderSegList(allSegs, dayDates) {
            let { theme, options } = this.context;
            let { timeHeaderId, eventHeaderId, dateHeaderIdRoot } = this.state;
            let segsByDay = groupSegsByDay(allSegs); // sparse array
            return (preact.createElement(internal$1.NowTimer, { unit: "day" }, (nowDate, todayRange) => {
                let innerNodes = [];
                for (let dayIndex = 0; dayIndex < segsByDay.length; dayIndex += 1) {
                    let daySegs = segsByDay[dayIndex];
                    if (daySegs) { // sparse array, so might be undefined
                        let dayStr = internal$1.formatDayString(dayDates[dayIndex]);
                        let dateHeaderId = dateHeaderIdRoot + '-' + dayStr;
                        // append a day header
                        innerNodes.push(preact.createElement(ListViewHeaderRow, { key: dayStr, cellId: dateHeaderId, dayDate: dayDates[dayIndex], todayRange: todayRange }));
                        daySegs = internal$1.sortEventSegs(daySegs, options.eventOrder);
                        for (let seg of daySegs) {
                            innerNodes.push(preact.createElement(ListViewEventRow, Object.assign({ key: dayStr + ':' + seg.eventRange.instance.instanceId /* are multiple segs for an instanceId */, seg: seg, isDragging: false, isResizing: false, isDateSelecting: false, isSelected: false, timeHeaderId: timeHeaderId, eventHeaderId: eventHeaderId, dateHeaderId: dateHeaderId }, internal$1.getSegMeta(seg, todayRange, nowDate))));
                        }
                    }
                }
                return (preact.createElement("table", { className: 'fc-list-table ' + theme.getClass('table') },
                    preact.createElement("thead", null,
                        preact.createElement("tr", null,
                            preact.createElement("th", { scope: "col", id: timeHeaderId }, options.timeHint),
                            preact.createElement("th", { scope: "col", "aria-hidden": true }),
                            preact.createElement("th", { scope: "col", id: eventHeaderId }, options.eventHint))),
                    preact.createElement("tbody", null, innerNodes)));
            }));
        }
        _eventStoreToSegs(eventStore, eventUiBases, dayRanges) {
            return this.eventRangesToSegs(internal$1.sliceEventStore(eventStore, eventUiBases, this.props.dateProfile.activeRange, this.context.options.nextDayThreshold).fg, dayRanges);
        }
        eventRangesToSegs(eventRanges, dayRanges) {
            let segs = [];
            for (let eventRange of eventRanges) {
                segs.push(...this.eventRangeToSegs(eventRange, dayRanges));
            }
            return segs;
        }
        eventRangeToSegs(eventRange, dayRanges) {
            let { dateEnv } = this.context;
            let { nextDayThreshold } = this.context.options;
            let range = eventRange.range;
            let allDay = eventRange.def.allDay;
            let dayIndex;
            let segRange;
            let seg;
            let segs = [];
            for (dayIndex = 0; dayIndex < dayRanges.length; dayIndex += 1) {
                segRange = internal$1.intersectRanges(range, dayRanges[dayIndex]);
                if (segRange) {
                    seg = {
                        component: this,
                        eventRange,
                        start: segRange.start,
                        end: segRange.end,
                        isStart: eventRange.isStart && segRange.start.valueOf() === range.start.valueOf(),
                        isEnd: eventRange.isEnd && segRange.end.valueOf() === range.end.valueOf(),
                        dayIndex,
                    };
                    segs.push(seg);
                    // detect when range won't go fully into the next day,
                    // and mutate the latest seg to the be the end.
                    if (!seg.isEnd && !allDay &&
                        dayIndex + 1 < dayRanges.length &&
                        range.end <
                            dateEnv.add(dayRanges[dayIndex + 1].start, nextDayThreshold)) {
                        seg.end = range.end;
                        seg.isEnd = true;
                        break;
                    }
                }
            }
            return segs;
        }
    }
    function renderNoEventsInner(renderProps) {
        return renderProps.text;
    }
    function computeDateVars(dateProfile) {
        let dayStart = internal$1.startOfDay(dateProfile.renderRange.start);
        let viewEnd = dateProfile.renderRange.end;
        let dayDates = [];
        let dayRanges = [];
        while (dayStart < viewEnd) {
            dayDates.push(dayStart);
            dayRanges.push({
                start: dayStart,
                end: internal$1.addDays(dayStart, 1),
            });
            dayStart = internal$1.addDays(dayStart, 1);
        }
        return { dayDates, dayRanges };
    }
    // Returns a sparse array of arrays, segs grouped by their dayIndex
    function groupSegsByDay(segs) {
        let segsByDay = []; // sparse array
        let i;
        let seg;
        for (i = 0; i < segs.length; i += 1) {
            seg = segs[i];
            (segsByDay[seg.dayIndex] || (segsByDay[seg.dayIndex] = []))
                .push(seg);
        }
        return segsByDay;
    }

    const OPTION_REFINERS = {
        listDayFormat: createFalsableFormatter,
        listDaySideFormat: createFalsableFormatter,
        noEventsClassNames: internal$1.identity,
        noEventsContent: internal$1.identity,
        noEventsDidMount: internal$1.identity,
        noEventsWillUnmount: internal$1.identity,
        // noEventsText is defined in base options
    };
    function createFalsableFormatter(input) {
        return input === false ? null : internal$1.createFormatter(input);
    }

    var css_248z = ":root{--fc-list-event-dot-width:10px;--fc-list-event-hover-bg-color:#f5f5f5}.fc-theme-standard .fc-list{border:1px solid var(--fc-border-color)}.fc .fc-list-empty{align-items:center;background-color:var(--fc-neutral-bg-color);display:flex;height:100%;justify-content:center}.fc .fc-list-empty-cushion{margin:5em 0}.fc .fc-list-table{border-style:hidden;width:100%}.fc .fc-list-table tr>*{border-left:0;border-right:0}.fc .fc-list-sticky .fc-list-day>*{background:var(--fc-page-bg-color);position:sticky;top:0}.fc .fc-list-table thead{left:-10000px;position:absolute}.fc .fc-list-table tbody>tr:first-child th{border-top:0}.fc .fc-list-table th{padding:0}.fc .fc-list-day-cushion,.fc .fc-list-table td{padding:8px 14px}.fc .fc-list-day-cushion:after{clear:both;content:\"\";display:table}.fc-theme-standard .fc-list-day-cushion{background-color:var(--fc-neutral-bg-color)}.fc-direction-ltr .fc-list-day-text,.fc-direction-rtl .fc-list-day-side-text{float:left}.fc-direction-ltr .fc-list-day-side-text,.fc-direction-rtl .fc-list-day-text{float:right}.fc-direction-ltr .fc-list-table .fc-list-event-graphic{padding-right:0}.fc-direction-rtl .fc-list-table .fc-list-event-graphic{padding-left:0}.fc .fc-list-event.fc-event-forced-url{cursor:pointer}.fc .fc-list-event:hover td{background-color:var(--fc-list-event-hover-bg-color)}.fc .fc-list-event-graphic,.fc .fc-list-event-time{white-space:nowrap;width:1px}.fc .fc-list-event-dot{border:calc(var(--fc-list-event-dot-width)/2) solid var(--fc-event-border-color);border-radius:calc(var(--fc-list-event-dot-width)/2);box-sizing:content-box;display:inline-block;height:0;width:0}.fc .fc-list-event-title a{color:inherit;text-decoration:none}.fc .fc-list-event.fc-event-forced-url:hover a{text-decoration:underline}";
    internal$1.injectStyles(css_248z);

    var plugin = core.createPlugin({
        name: '@fullcalendar/list',
        optionRefiners: OPTION_REFINERS,
        views: {
            list: {
                component: ListView,
                buttonTextKey: 'list',
                listDayFormat: { month: 'long', day: 'numeric', year: 'numeric' }, // like "January 1, 2016"
            },
            listDay: {
                type: 'list',
                duration: { days: 1 },
                listDayFormat: { weekday: 'long' }, // day-of-week is all we need. full date is probably in headerToolbar
            },
            listWeek: {
                type: 'list',
                duration: { weeks: 1 },
                listDayFormat: { weekday: 'long' },
                listDaySideFormat: { month: 'long', day: 'numeric', year: 'numeric' },
            },
            listMonth: {
                type: 'list',
                duration: { month: 1 },
                listDaySideFormat: { weekday: 'long' }, // day-of-week is nice-to-have
            },
            listYear: {
                type: 'list',
                duration: { year: 1 },
                listDaySideFormat: { weekday: 'long' }, // day-of-week is nice-to-have
            },
        },
    });

    var internal = {
        __proto__: null,
        ListView: ListView
    };

    core.globalPlugins.push(plugin);

    exports.Internal = internal;
    exports["default"] = plugin;

    Object.defineProperty(exports, '__esModule', { value: true });

    return exports;

})({}, FullCalendar, FullCalendar.Internal, FullCalendar.Preact);
