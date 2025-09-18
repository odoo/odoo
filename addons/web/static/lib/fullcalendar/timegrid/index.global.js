/*!
FullCalendar Time Grid Plugin v6.1.20
Docs & License: https://fullcalendar.io/docs/timegrid-view
(c) 2024 Adam Shaw
*/
FullCalendar.TimeGrid = (function (exports, core, internal$1, preact, internal$2) {
    'use strict';

    class AllDaySplitter extends internal$1.Splitter {
        getKeyInfo() {
            return {
                allDay: {},
                timed: {},
            };
        }
        getKeysForDateSpan(dateSpan) {
            if (dateSpan.allDay) {
                return ['allDay'];
            }
            return ['timed'];
        }
        getKeysForEventDef(eventDef) {
            if (!eventDef.allDay) {
                return ['timed'];
            }
            if (internal$1.hasBgRendering(eventDef)) {
                return ['timed', 'allDay'];
            }
            return ['allDay'];
        }
    }

    const DEFAULT_SLAT_LABEL_FORMAT = internal$1.createFormatter({
        hour: 'numeric',
        minute: '2-digit',
        omitZeroMinute: true,
        meridiem: 'short',
    });
    function TimeColsAxisCell(props) {
        let classNames = [
            'fc-timegrid-slot',
            'fc-timegrid-slot-label',
            props.isLabeled ? 'fc-scrollgrid-shrink' : 'fc-timegrid-slot-minor',
        ];
        return (preact.createElement(internal$1.ViewContextType.Consumer, null, (context) => {
            if (!props.isLabeled) {
                return (preact.createElement("td", { className: classNames.join(' '), "data-time": props.isoTimeStr }));
            }
            let { dateEnv, options, viewApi } = context;
            let labelFormat = // TODO: fully pre-parse
             options.slotLabelFormat == null ? DEFAULT_SLAT_LABEL_FORMAT :
                Array.isArray(options.slotLabelFormat) ? internal$1.createFormatter(options.slotLabelFormat[0]) :
                    internal$1.createFormatter(options.slotLabelFormat);
            let renderProps = {
                level: 0,
                time: props.time,
                date: dateEnv.toDate(props.date),
                view: viewApi,
                text: dateEnv.format(props.date, labelFormat),
            };
            return (preact.createElement(internal$1.ContentContainer, { elTag: "td", elClasses: classNames, elAttrs: {
                    'data-time': props.isoTimeStr,
                }, renderProps: renderProps, generatorName: "slotLabelContent", customGenerator: options.slotLabelContent, defaultGenerator: renderInnerContent, classNameGenerator: options.slotLabelClassNames, didMount: options.slotLabelDidMount, willUnmount: options.slotLabelWillUnmount }, (InnerContent) => (preact.createElement("div", { className: "fc-timegrid-slot-label-frame fc-scrollgrid-shrink-frame" },
                preact.createElement(InnerContent, { elTag: "div", elClasses: [
                        'fc-timegrid-slot-label-cushion',
                        'fc-scrollgrid-shrink-cushion',
                    ] })))));
        }));
    }
    function renderInnerContent(props) {
        return props.text;
    }

    class TimeBodyAxis extends internal$1.BaseComponent {
        render() {
            return this.props.slatMetas.map((slatMeta) => (preact.createElement("tr", { key: slatMeta.key },
                preact.createElement(TimeColsAxisCell, Object.assign({}, slatMeta)))));
        }
    }

    const DEFAULT_WEEK_NUM_FORMAT = internal$1.createFormatter({ week: 'short' });
    const AUTO_ALL_DAY_MAX_EVENT_ROWS = 5;
    class TimeColsView extends internal$1.DateComponent {
        constructor() {
            super(...arguments);
            this.allDaySplitter = new AllDaySplitter(); // for use by subclasses
            this.headerElRef = preact.createRef();
            this.rootElRef = preact.createRef();
            this.scrollerElRef = preact.createRef();
            this.state = {
                slatCoords: null,
            };
            this.handleScrollTopRequest = (scrollTop) => {
                let scrollerEl = this.scrollerElRef.current;
                if (scrollerEl) { // TODO: not sure how this could ever be null. weirdness with the reducer
                    scrollerEl.scrollTop = scrollTop;
                }
            };
            /* Header Render Methods
            ------------------------------------------------------------------------------------------------------------------*/
            this.renderHeadAxis = (rowKey, frameHeight = '') => {
                let { options } = this.context;
                let { dateProfile } = this.props;
                let range = dateProfile.renderRange;
                let dayCnt = internal$1.diffDays(range.start, range.end);
                // only do in day views (to avoid doing in week views that dont need it)
                let navLinkAttrs = (dayCnt === 1)
                    ? internal$1.buildNavLinkAttrs(this.context, range.start, 'week')
                    : {};
                if (options.weekNumbers && rowKey === 'day') {
                    return (preact.createElement(internal$1.WeekNumberContainer, { elTag: "th", elClasses: [
                            'fc-timegrid-axis',
                            'fc-scrollgrid-shrink',
                        ], elAttrs: {
                            'aria-hidden': true,
                        }, date: range.start, defaultFormat: DEFAULT_WEEK_NUM_FORMAT }, (InnerContent) => (preact.createElement("div", { className: [
                            'fc-timegrid-axis-frame',
                            'fc-scrollgrid-shrink-frame',
                            'fc-timegrid-axis-frame-liquid',
                        ].join(' '), style: { height: frameHeight } },
                        preact.createElement(InnerContent, { elTag: "a", elClasses: [
                                'fc-timegrid-axis-cushion',
                                'fc-scrollgrid-shrink-cushion',
                                'fc-scrollgrid-sync-inner',
                            ], elAttrs: navLinkAttrs })))));
                }
                return (preact.createElement("th", { "aria-hidden": true, className: "fc-timegrid-axis" },
                    preact.createElement("div", { className: "fc-timegrid-axis-frame", style: { height: frameHeight } })));
            };
            /* Table Component Render Methods
            ------------------------------------------------------------------------------------------------------------------*/
            // only a one-way height sync. we don't send the axis inner-content height to the DayGrid,
            // but DayGrid still needs to have classNames on inner elements in order to measure.
            this.renderTableRowAxis = (rowHeight) => {
                let { options, viewApi } = this.context;
                let renderProps = {
                    text: options.allDayText,
                    view: viewApi,
                };
                return (
                // TODO: make reusable hook. used in list view too
                preact.createElement(internal$1.ContentContainer, { elTag: "td", elClasses: [
                        'fc-timegrid-axis',
                        'fc-scrollgrid-shrink',
                    ], elAttrs: {
                        'aria-hidden': true,
                    }, renderProps: renderProps, generatorName: "allDayContent", customGenerator: options.allDayContent, defaultGenerator: renderAllDayInner, classNameGenerator: options.allDayClassNames, didMount: options.allDayDidMount, willUnmount: options.allDayWillUnmount }, (InnerContent) => (preact.createElement("div", { className: [
                        'fc-timegrid-axis-frame',
                        'fc-scrollgrid-shrink-frame',
                        rowHeight == null ? ' fc-timegrid-axis-frame-liquid' : '',
                    ].join(' '), style: { height: rowHeight } },
                    preact.createElement(InnerContent, { elTag: "span", elClasses: [
                            'fc-timegrid-axis-cushion',
                            'fc-scrollgrid-shrink-cushion',
                            'fc-scrollgrid-sync-inner',
                        ] })))));
            };
            this.handleSlatCoords = (slatCoords) => {
                this.setState({ slatCoords });
            };
        }
        // rendering
        // ----------------------------------------------------------------------------------------------------
        renderSimpleLayout(headerRowContent, allDayContent, timeContent) {
            let { context, props } = this;
            let sections = [];
            let stickyHeaderDates = internal$1.getStickyHeaderDates(context.options);
            if (headerRowContent) {
                sections.push({
                    type: 'header',
                    key: 'header',
                    isSticky: stickyHeaderDates,
                    chunk: {
                        elRef: this.headerElRef,
                        tableClassName: 'fc-col-header',
                        rowContent: headerRowContent,
                    },
                });
            }
            if (allDayContent) {
                sections.push({
                    type: 'body',
                    key: 'all-day',
                    chunk: { content: allDayContent },
                });
                sections.push({
                    type: 'body',
                    key: 'all-day-divider',
                    outerContent: ( // TODO: rename to cellContent so don't need to define <tr>?
                    preact.createElement("tr", { role: "presentation", className: "fc-scrollgrid-section" },
                        preact.createElement("td", { className: 'fc-timegrid-divider ' + context.theme.getClass('tableCellShaded') }))),
                });
            }
            sections.push({
                type: 'body',
                key: 'body',
                liquid: true,
                expandRows: Boolean(context.options.expandRows),
                chunk: {
                    scrollerElRef: this.scrollerElRef,
                    content: timeContent,
                },
            });
            return (preact.createElement(internal$1.ViewContainer, { elRef: this.rootElRef, elClasses: ['fc-timegrid'], viewSpec: context.viewSpec },
                preact.createElement(internal$1.SimpleScrollGrid, { liquid: !props.isHeightAuto && !props.forPrint, collapsibleWidth: props.forPrint, cols: [{ width: 'shrink' }], sections: sections })));
        }
        renderHScrollLayout(headerRowContent, allDayContent, timeContent, colCnt, dayMinWidth, slatMetas, slatCoords) {
            let ScrollGrid = this.context.pluginHooks.scrollGridImpl;
            if (!ScrollGrid) {
                throw new Error('No ScrollGrid implementation');
            }
            let { context, props } = this;
            let stickyHeaderDates = !props.forPrint && internal$1.getStickyHeaderDates(context.options);
            let stickyFooterScrollbar = !props.forPrint && internal$1.getStickyFooterScrollbar(context.options);
            let sections = [];
            if (headerRowContent) {
                sections.push({
                    type: 'header',
                    key: 'header',
                    isSticky: stickyHeaderDates,
                    syncRowHeights: true,
                    chunks: [
                        {
                            key: 'axis',
                            rowContent: (arg) => (preact.createElement("tr", { role: "presentation" }, this.renderHeadAxis('day', arg.rowSyncHeights[0]))),
                        },
                        {
                            key: 'cols',
                            elRef: this.headerElRef,
                            tableClassName: 'fc-col-header',
                            rowContent: headerRowContent,
                        },
                    ],
                });
            }
            if (allDayContent) {
                sections.push({
                    type: 'body',
                    key: 'all-day',
                    syncRowHeights: true,
                    chunks: [
                        {
                            key: 'axis',
                            rowContent: (contentArg) => (preact.createElement("tr", { role: "presentation" }, this.renderTableRowAxis(contentArg.rowSyncHeights[0]))),
                        },
                        {
                            key: 'cols',
                            content: allDayContent,
                        },
                    ],
                });
                sections.push({
                    key: 'all-day-divider',
                    type: 'body',
                    outerContent: ( // TODO: rename to cellContent so don't need to define <tr>?
                    preact.createElement("tr", { role: "presentation", className: "fc-scrollgrid-section" },
                        preact.createElement("td", { colSpan: 2, className: 'fc-timegrid-divider ' + context.theme.getClass('tableCellShaded') }))),
                });
            }
            let isNowIndicator = context.options.nowIndicator;
            sections.push({
                type: 'body',
                key: 'body',
                liquid: true,
                expandRows: Boolean(context.options.expandRows),
                chunks: [
                    {
                        key: 'axis',
                        content: (arg) => (
                        // TODO: make this now-indicator arrow more DRY with TimeColsContent
                        preact.createElement("div", { className: "fc-timegrid-axis-chunk" },
                            preact.createElement("table", { "aria-hidden": true, style: { height: arg.expandRows ? arg.clientHeight : '' } },
                                arg.tableColGroupNode,
                                preact.createElement("tbody", null,
                                    preact.createElement(TimeBodyAxis, { slatMetas: slatMetas }))),
                            preact.createElement("div", { className: "fc-timegrid-now-indicator-container" },
                                preact.createElement(internal$1.NowTimer, { unit: isNowIndicator ? 'minute' : 'day' /* hacky */ }, (nowDate) => {
                                    let nowIndicatorTop = isNowIndicator &&
                                        slatCoords &&
                                        slatCoords.safeComputeTop(nowDate); // might return void
                                    if (typeof nowIndicatorTop === 'number') {
                                        return (preact.createElement(internal$1.NowIndicatorContainer, { elClasses: ['fc-timegrid-now-indicator-arrow'], elStyle: { top: nowIndicatorTop }, isAxis: true, date: nowDate }));
                                    }
                                    return null;
                                })))),
                    },
                    {
                        key: 'cols',
                        scrollerElRef: this.scrollerElRef,
                        content: timeContent,
                    },
                ],
            });
            if (stickyFooterScrollbar) {
                sections.push({
                    key: 'footer',
                    type: 'footer',
                    isSticky: true,
                    chunks: [
                        {
                            key: 'axis',
                            content: internal$1.renderScrollShim,
                        },
                        {
                            key: 'cols',
                            content: internal$1.renderScrollShim,
                        },
                    ],
                });
            }
            return (preact.createElement(internal$1.ViewContainer, { elRef: this.rootElRef, elClasses: ['fc-timegrid'], viewSpec: context.viewSpec },
                preact.createElement(ScrollGrid, { liquid: !props.isHeightAuto && !props.forPrint, forPrint: props.forPrint, collapsibleWidth: false, colGroups: [
                        { width: 'shrink', cols: [{ width: 'shrink' }] },
                        { cols: [{ span: colCnt, minWidth: dayMinWidth }] },
                    ], sections: sections })));
        }
        /* Dimensions
        ------------------------------------------------------------------------------------------------------------------*/
        getAllDayMaxEventProps() {
            let { dayMaxEvents, dayMaxEventRows } = this.context.options;
            if (dayMaxEvents === true || dayMaxEventRows === true) { // is auto?
                dayMaxEvents = undefined;
                dayMaxEventRows = AUTO_ALL_DAY_MAX_EVENT_ROWS; // make sure "auto" goes to a real number
            }
            return { dayMaxEvents, dayMaxEventRows };
        }
    }
    function renderAllDayInner(renderProps) {
        return renderProps.text;
    }

    class TimeColsSlatsCoords {
        constructor(positions, dateProfile, slotDuration) {
            this.positions = positions;
            this.dateProfile = dateProfile;
            this.slotDuration = slotDuration;
        }
        safeComputeTop(date) {
            let { dateProfile } = this;
            if (internal$1.rangeContainsMarker(dateProfile.currentRange, date)) {
                let startOfDayDate = internal$1.startOfDay(date);
                let timeMs = date.valueOf() - startOfDayDate.valueOf();
                if (timeMs >= internal$1.asRoughMs(dateProfile.slotMinTime) &&
                    timeMs < internal$1.asRoughMs(dateProfile.slotMaxTime)) {
                    return this.computeTimeTop(internal$1.createDuration(timeMs));
                }
            }
            return null;
        }
        // Computes the top coordinate, relative to the bounds of the grid, of the given date.
        // A `startOfDayDate` must be given for avoiding ambiguity over how to treat midnight.
        computeDateTop(when, startOfDayDate) {
            if (!startOfDayDate) {
                startOfDayDate = internal$1.startOfDay(when);
            }
            return this.computeTimeTop(internal$1.createDuration(when.valueOf() - startOfDayDate.valueOf()));
        }
        // Computes the top coordinate, relative to the bounds of the grid, of the given time (a Duration).
        // This is a makeshify way to compute the time-top. Assumes all slatMetas dates are uniform.
        // Eventually allow computation with arbirary slat dates.
        computeTimeTop(duration) {
            let { positions, dateProfile } = this;
            let len = positions.els.length;
            // floating-point value of # of slots covered
            let slatCoverage = (duration.milliseconds - internal$1.asRoughMs(dateProfile.slotMinTime)) / internal$1.asRoughMs(this.slotDuration);
            let slatIndex;
            let slatRemainder;
            // compute a floating-point number for how many slats should be progressed through.
            // from 0 to number of slats (inclusive)
            // constrained because slotMinTime/slotMaxTime might be customized.
            slatCoverage = Math.max(0, slatCoverage);
            slatCoverage = Math.min(len, slatCoverage);
            // an integer index of the furthest whole slat
            // from 0 to number slats (*exclusive*, so len-1)
            slatIndex = Math.floor(slatCoverage);
            slatIndex = Math.min(slatIndex, len - 1);
            // how much further through the slatIndex slat (from 0.0-1.0) must be covered in addition.
            // could be 1.0 if slatCoverage is covering *all* the slots
            slatRemainder = slatCoverage - slatIndex;
            return positions.tops[slatIndex] +
                positions.getHeight(slatIndex) * slatRemainder;
        }
    }

    class TimeColsSlatsBody extends internal$1.BaseComponent {
        render() {
            let { props, context } = this;
            let { options } = context;
            let { slatElRefs } = props;
            return (preact.createElement("tbody", null, props.slatMetas.map((slatMeta, i) => {
                let renderProps = {
                    time: slatMeta.time,
                    date: context.dateEnv.toDate(slatMeta.date),
                    view: context.viewApi,
                };
                return (preact.createElement("tr", { key: slatMeta.key, ref: slatElRefs.createRef(slatMeta.key) },
                    props.axis && (preact.createElement(TimeColsAxisCell, Object.assign({}, slatMeta))),
                    preact.createElement(internal$1.ContentContainer, { elTag: "td", elClasses: [
                            'fc-timegrid-slot',
                            'fc-timegrid-slot-lane',
                            !slatMeta.isLabeled && 'fc-timegrid-slot-minor',
                        ], elAttrs: {
                            'data-time': slatMeta.isoTimeStr,
                        }, renderProps: renderProps, generatorName: "slotLaneContent", customGenerator: options.slotLaneContent, classNameGenerator: options.slotLaneClassNames, didMount: options.slotLaneDidMount, willUnmount: options.slotLaneWillUnmount })));
            })));
        }
    }

    /*
    for the horizontal "slats" that run width-wise. Has a time axis on a side. Depends on RTL.
    */
    class TimeColsSlats extends internal$1.BaseComponent {
        constructor() {
            super(...arguments);
            this.rootElRef = preact.createRef();
            this.slatElRefs = new internal$1.RefMap();
        }
        render() {
            let { props, context } = this;
            return (preact.createElement("div", { ref: this.rootElRef, className: "fc-timegrid-slots" },
                preact.createElement("table", { "aria-hidden": true, className: context.theme.getClass('table'), style: {
                        minWidth: props.tableMinWidth,
                        width: props.clientWidth,
                        height: props.minHeight,
                    } },
                    props.tableColGroupNode /* relies on there only being a single <col> for the axis */,
                    preact.createElement(TimeColsSlatsBody, { slatElRefs: this.slatElRefs, axis: props.axis, slatMetas: props.slatMetas }))));
        }
        componentDidMount() {
            this.updateSizing();
        }
        componentDidUpdate() {
            this.updateSizing();
        }
        componentWillUnmount() {
            if (this.props.onCoords) {
                this.props.onCoords(null);
            }
        }
        updateSizing() {
            let { context, props } = this;
            if (props.onCoords &&
                props.clientWidth !== null // means sizing has stabilized
            ) {
                let rootEl = this.rootElRef.current;
                if (rootEl.offsetHeight) { // not hidden by css
                    props.onCoords(new TimeColsSlatsCoords(new internal$1.PositionCache(this.rootElRef.current, collectSlatEls(this.slatElRefs.currentMap, props.slatMetas), false, true), this.props.dateProfile, context.options.slotDuration));
                }
            }
        }
    }
    function collectSlatEls(elMap, slatMetas) {
        return slatMetas.map((slatMeta) => elMap[slatMeta.key]);
    }

    function splitSegsByCol(segs, colCnt) {
        let segsByCol = [];
        let i;
        for (i = 0; i < colCnt; i += 1) {
            segsByCol.push([]);
        }
        if (segs) {
            for (i = 0; i < segs.length; i += 1) {
                segsByCol[segs[i].col].push(segs[i]);
            }
        }
        return segsByCol;
    }
    function splitInteractionByCol(ui, colCnt) {
        let byRow = [];
        if (!ui) {
            for (let i = 0; i < colCnt; i += 1) {
                byRow[i] = null;
            }
        }
        else {
            for (let i = 0; i < colCnt; i += 1) {
                byRow[i] = {
                    affectedInstances: ui.affectedInstances,
                    isEvent: ui.isEvent,
                    segs: [],
                };
            }
            for (let seg of ui.segs) {
                byRow[seg.col].segs.push(seg);
            }
        }
        return byRow;
    }

    class TimeColMoreLink extends internal$1.BaseComponent {
        render() {
            let { props } = this;
            return (preact.createElement(internal$1.MoreLinkContainer, { elClasses: ['fc-timegrid-more-link'], elStyle: {
                    top: props.top,
                    bottom: props.bottom,
                }, allDayDate: null, moreCnt: props.hiddenSegs.length, allSegs: props.hiddenSegs, hiddenSegs: props.hiddenSegs, extraDateSpan: props.extraDateSpan, dateProfile: props.dateProfile, todayRange: props.todayRange, popoverContent: () => renderPlainFgSegs(props.hiddenSegs, props), defaultGenerator: renderMoreLinkInner, forceTimed: true }, (InnerContent) => (preact.createElement(InnerContent, { elTag: "div", elClasses: ['fc-timegrid-more-link-inner', 'fc-sticky'] }))));
        }
    }
    function renderMoreLinkInner(props) {
        return props.shortText;
    }

    // segInputs assumed sorted
    function buildPositioning(segInputs, strictOrder, maxStackCnt) {
        let hierarchy = new internal$1.SegHierarchy();
        if (strictOrder != null) {
            hierarchy.strictOrder = strictOrder;
        }
        if (maxStackCnt != null) {
            hierarchy.maxStackCnt = maxStackCnt;
        }
        let hiddenEntries = hierarchy.addSegs(segInputs);
        let hiddenGroups = internal$1.groupIntersectingEntries(hiddenEntries);
        let web = buildWeb(hierarchy);
        web = stretchWeb(web, 1); // all levelCoords/thickness will have 0.0-1.0
        let segRects = webToRects(web);
        return { segRects, hiddenGroups };
    }
    function buildWeb(hierarchy) {
        const { entriesByLevel } = hierarchy;
        const buildNode = cacheable((level, lateral) => level + ':' + lateral, (level, lateral) => {
            let siblingRange = findNextLevelSegs(hierarchy, level, lateral);
            let nextLevelRes = buildNodes(siblingRange, buildNode);
            let entry = entriesByLevel[level][lateral];
            return [
                Object.assign(Object.assign({}, entry), { nextLevelNodes: nextLevelRes[0] }),
                entry.thickness + nextLevelRes[1], // the pressure builds
            ];
        });
        return buildNodes(entriesByLevel.length
            ? { level: 0, lateralStart: 0, lateralEnd: entriesByLevel[0].length }
            : null, buildNode)[0];
    }
    function buildNodes(siblingRange, buildNode) {
        if (!siblingRange) {
            return [[], 0];
        }
        let { level, lateralStart, lateralEnd } = siblingRange;
        let lateral = lateralStart;
        let pairs = [];
        while (lateral < lateralEnd) {
            pairs.push(buildNode(level, lateral));
            lateral += 1;
        }
        pairs.sort(cmpDescPressures);
        return [
            pairs.map(extractNode),
            pairs[0][1], // first item's pressure
        ];
    }
    function cmpDescPressures(a, b) {
        return b[1] - a[1];
    }
    function extractNode(a) {
        return a[0];
    }
    function findNextLevelSegs(hierarchy, subjectLevel, subjectLateral) {
        let { levelCoords, entriesByLevel } = hierarchy;
        let subjectEntry = entriesByLevel[subjectLevel][subjectLateral];
        let afterSubject = levelCoords[subjectLevel] + subjectEntry.thickness;
        let levelCnt = levelCoords.length;
        let level = subjectLevel;
        // skip past levels that are too high up
        for (; level < levelCnt && levelCoords[level] < afterSubject; level += 1)
            ; // do nothing
        for (; level < levelCnt; level += 1) {
            let entries = entriesByLevel[level];
            let entry;
            let searchIndex = internal$1.binarySearch(entries, subjectEntry.span.start, internal$1.getEntrySpanEnd);
            let lateralStart = searchIndex[0] + searchIndex[1]; // if exact match (which doesn't collide), go to next one
            let lateralEnd = lateralStart;
            while ( // loop through entries that horizontally intersect
            (entry = entries[lateralEnd]) && // but not past the whole seg list
                entry.span.start < subjectEntry.span.end) {
                lateralEnd += 1;
            }
            if (lateralStart < lateralEnd) {
                return { level, lateralStart, lateralEnd };
            }
        }
        return null;
    }
    function stretchWeb(topLevelNodes, totalThickness) {
        const stretchNode = cacheable((node, startCoord, prevThickness) => internal$1.buildEntryKey(node), (node, startCoord, prevThickness) => {
            let { nextLevelNodes, thickness } = node;
            let allThickness = thickness + prevThickness;
            let thicknessFraction = thickness / allThickness;
            let endCoord;
            let newChildren = [];
            if (!nextLevelNodes.length) {
                endCoord = totalThickness;
            }
            else {
                for (let childNode of nextLevelNodes) {
                    if (endCoord === undefined) {
                        let res = stretchNode(childNode, startCoord, allThickness);
                        endCoord = res[0];
                        newChildren.push(res[1]);
                    }
                    else {
                        let res = stretchNode(childNode, endCoord, 0);
                        newChildren.push(res[1]);
                    }
                }
            }
            let newThickness = (endCoord - startCoord) * thicknessFraction;
            return [endCoord - newThickness, Object.assign(Object.assign({}, node), { thickness: newThickness, nextLevelNodes: newChildren })];
        });
        return topLevelNodes.map((node) => stretchNode(node, 0, 0)[1]);
    }
    // not sorted in any particular order
    function webToRects(topLevelNodes) {
        let rects = [];
        const processNode = cacheable((node, levelCoord, stackDepth) => internal$1.buildEntryKey(node), (node, levelCoord, stackDepth) => {
            let rect = Object.assign(Object.assign({}, node), { levelCoord,
                stackDepth, stackForward: 0 });
            rects.push(rect);
            return (rect.stackForward = processNodes(node.nextLevelNodes, levelCoord + node.thickness, stackDepth + 1) + 1);
        });
        function processNodes(nodes, levelCoord, stackDepth) {
            let stackForward = 0;
            for (let node of nodes) {
                stackForward = Math.max(processNode(node, levelCoord, stackDepth), stackForward);
            }
            return stackForward;
        }
        processNodes(topLevelNodes, 0, 0);
        return rects; // TODO: sort rects by levelCoord to be consistent with toRects?
    }
    // TODO: move to general util
    function cacheable(keyFunc, workFunc) {
        const cache = {};
        return (...args) => {
            let key = keyFunc(...args);
            return (key in cache)
                ? cache[key]
                : (cache[key] = workFunc(...args));
        };
    }

    function computeSegVCoords(segs, colDate, slatCoords = null, eventMinHeight = 0) {
        let vcoords = [];
        if (slatCoords) {
            for (let i = 0; i < segs.length; i += 1) {
                let seg = segs[i];
                let spanStart = slatCoords.computeDateTop(seg.start, colDate);
                let spanEnd = Math.max(spanStart + (eventMinHeight || 0), // :(
                slatCoords.computeDateTop(seg.end, colDate));
                vcoords.push({
                    start: Math.round(spanStart),
                    end: Math.round(spanEnd), //
                });
            }
        }
        return vcoords;
    }
    function computeFgSegPlacements(segs, segVCoords, // might not have for every seg
    eventOrderStrict, eventMaxStack) {
        let segInputs = [];
        let dumbSegs = []; // segs without coords
        for (let i = 0; i < segs.length; i += 1) {
            let vcoords = segVCoords[i];
            if (vcoords) {
                segInputs.push({
                    index: i,
                    thickness: 1,
                    span: vcoords,
                });
            }
            else {
                dumbSegs.push(segs[i]);
            }
        }
        let { segRects, hiddenGroups } = buildPositioning(segInputs, eventOrderStrict, eventMaxStack);
        let segPlacements = [];
        for (let segRect of segRects) {
            segPlacements.push({
                seg: segs[segRect.index],
                rect: segRect,
            });
        }
        for (let dumbSeg of dumbSegs) {
            segPlacements.push({ seg: dumbSeg, rect: null });
        }
        return { segPlacements, hiddenGroups };
    }

    const DEFAULT_TIME_FORMAT = internal$1.createFormatter({
        hour: 'numeric',
        minute: '2-digit',
        meridiem: false,
    });
    class TimeColEvent extends internal$1.BaseComponent {
        render() {
            return (preact.createElement(internal$1.StandardEvent, Object.assign({}, this.props, { elClasses: [
                    'fc-timegrid-event',
                    'fc-v-event',
                    this.props.isShort && 'fc-timegrid-event-short',
                ], defaultTimeFormat: DEFAULT_TIME_FORMAT })));
        }
    }

    class TimeCol extends internal$1.BaseComponent {
        constructor() {
            super(...arguments);
            this.sortEventSegs = internal$1.memoize(internal$1.sortEventSegs);
        }
        // TODO: memoize event-placement?
        render() {
            let { props, context } = this;
            let { options } = context;
            let isSelectMirror = options.selectMirror;
            let mirrorSegs = // yuck
             (props.eventDrag && props.eventDrag.segs) ||
                (props.eventResize && props.eventResize.segs) ||
                (isSelectMirror && props.dateSelectionSegs) ||
                [];
            let interactionAffectedInstances = // TODO: messy way to compute this
             (props.eventDrag && props.eventDrag.affectedInstances) ||
                (props.eventResize && props.eventResize.affectedInstances) ||
                {};
            let sortedFgSegs = this.sortEventSegs(props.fgEventSegs, options.eventOrder);
            return (preact.createElement(internal$1.DayCellContainer, { elTag: "td", elRef: props.elRef, elClasses: [
                    'fc-timegrid-col',
                    ...(props.extraClassNames || []),
                ], elAttrs: Object.assign({ role: 'gridcell' }, props.extraDataAttrs), date: props.date, dateProfile: props.dateProfile, todayRange: props.todayRange, extraRenderProps: props.extraRenderProps }, (InnerContent) => (preact.createElement("div", { className: "fc-timegrid-col-frame" },
                preact.createElement("div", { className: "fc-timegrid-col-bg" },
                    this.renderFillSegs(props.businessHourSegs, 'non-business'),
                    this.renderFillSegs(props.bgEventSegs, 'bg-event'),
                    this.renderFillSegs(props.dateSelectionSegs, 'highlight')),
                preact.createElement("div", { className: "fc-timegrid-col-events" }, this.renderFgSegs(sortedFgSegs, interactionAffectedInstances, false, false, false)),
                preact.createElement("div", { className: "fc-timegrid-col-events" }, this.renderFgSegs(mirrorSegs, {}, Boolean(props.eventDrag), Boolean(props.eventResize), Boolean(isSelectMirror), 'mirror')),
                preact.createElement("div", { className: "fc-timegrid-now-indicator-container" }, this.renderNowIndicator(props.nowIndicatorSegs)),
                internal$1.hasCustomDayCellContent(options) && (preact.createElement(InnerContent, { elTag: "div", elClasses: ['fc-timegrid-col-misc'] }))))));
        }
        renderFgSegs(sortedFgSegs, segIsInvisible, isDragging, isResizing, isDateSelecting, forcedKey) {
            let { props } = this;
            if (props.forPrint) {
                return renderPlainFgSegs(sortedFgSegs, props);
            }
            return this.renderPositionedFgSegs(sortedFgSegs, segIsInvisible, isDragging, isResizing, isDateSelecting, forcedKey);
        }
        renderPositionedFgSegs(segs, // if not mirror, needs to be sorted
        segIsInvisible, isDragging, isResizing, isDateSelecting, forcedKey) {
            let { eventMaxStack, eventShortHeight, eventOrderStrict, eventMinHeight } = this.context.options;
            let { date, slatCoords, eventSelection, todayRange, nowDate } = this.props;
            let isMirror = isDragging || isResizing || isDateSelecting;
            let segVCoords = computeSegVCoords(segs, date, slatCoords, eventMinHeight);
            let { segPlacements, hiddenGroups } = computeFgSegPlacements(segs, segVCoords, eventOrderStrict, eventMaxStack);
            return (preact.createElement(preact.Fragment, null,
                this.renderHiddenGroups(hiddenGroups, segs),
                segPlacements.map((segPlacement) => {
                    let { seg, rect } = segPlacement;
                    let instanceId = seg.eventRange.instance.instanceId;
                    let isVisible = isMirror || Boolean(!segIsInvisible[instanceId] && rect);
                    let vStyle = computeSegVStyle(rect && rect.span);
                    let hStyle = (!isMirror && rect) ? this.computeSegHStyle(rect) : { left: 0, right: 0 };
                    let isInset = Boolean(rect) && rect.stackForward > 0;
                    let isShort = Boolean(rect) && (rect.span.end - rect.span.start) < eventShortHeight; // look at other places for this problem
                    return (preact.createElement("div", { className: 'fc-timegrid-event-harness' +
                            (isInset ? ' fc-timegrid-event-harness-inset' : ''), key: forcedKey || instanceId, style: Object.assign(Object.assign({ visibility: isVisible ? '' : 'hidden' }, vStyle), hStyle) },
                        preact.createElement(TimeColEvent, Object.assign({ seg: seg, isDragging: isDragging, isResizing: isResizing, isDateSelecting: isDateSelecting, isSelected: instanceId === eventSelection, isShort: isShort }, internal$1.getSegMeta(seg, todayRange, nowDate)))));
                })));
        }
        // will already have eventMinHeight applied because segInputs already had it
        renderHiddenGroups(hiddenGroups, segs) {
            let { extraDateSpan, dateProfile, todayRange, nowDate, eventSelection, eventDrag, eventResize } = this.props;
            return (preact.createElement(preact.Fragment, null, hiddenGroups.map((hiddenGroup) => {
                let positionCss = computeSegVStyle(hiddenGroup.span);
                let hiddenSegs = compileSegsFromEntries(hiddenGroup.entries, segs);
                return (preact.createElement(TimeColMoreLink, { key: internal$1.buildIsoString(internal$1.computeEarliestSegStart(hiddenSegs)), hiddenSegs: hiddenSegs, top: positionCss.top, bottom: positionCss.bottom, extraDateSpan: extraDateSpan, dateProfile: dateProfile, todayRange: todayRange, nowDate: nowDate, eventSelection: eventSelection, eventDrag: eventDrag, eventResize: eventResize }));
            })));
        }
        renderFillSegs(segs, fillType) {
            let { props, context } = this;
            let segVCoords = computeSegVCoords(segs, props.date, props.slatCoords, context.options.eventMinHeight); // don't assume all populated
            let children = segVCoords.map((vcoords, i) => {
                let seg = segs[i];
                return (preact.createElement("div", { key: internal$1.buildEventRangeKey(seg.eventRange), className: "fc-timegrid-bg-harness", style: computeSegVStyle(vcoords) }, fillType === 'bg-event' ?
                    preact.createElement(internal$1.BgEvent, Object.assign({ seg: seg }, internal$1.getSegMeta(seg, props.todayRange, props.nowDate))) :
                    internal$1.renderFill(fillType)));
            });
            return preact.createElement(preact.Fragment, null, children);
        }
        renderNowIndicator(segs) {
            let { slatCoords, date } = this.props;
            if (!slatCoords) {
                return null;
            }
            return segs.map((seg, i) => (preact.createElement(internal$1.NowIndicatorContainer
            // key doesn't matter. will only ever be one
            , { 
                // key doesn't matter. will only ever be one
                key: i, elClasses: ['fc-timegrid-now-indicator-line'], elStyle: {
                    top: slatCoords.computeDateTop(seg.start, date),
                }, isAxis: false, date: date })));
        }
        computeSegHStyle(segHCoords) {
            let { isRtl, options } = this.context;
            let shouldOverlap = options.slotEventOverlap;
            let nearCoord = segHCoords.levelCoord; // the left side if LTR. the right side if RTL. floating-point
            let farCoord = segHCoords.levelCoord + segHCoords.thickness; // the right side if LTR. the left side if RTL. floating-point
            let left; // amount of space from left edge, a fraction of the total width
            let right; // amount of space from right edge, a fraction of the total width
            if (shouldOverlap) {
                // double the width, but don't go beyond the maximum forward coordinate (1.0)
                farCoord = Math.min(1, nearCoord + (farCoord - nearCoord) * 2);
            }
            if (isRtl) {
                left = 1 - farCoord;
                right = nearCoord;
            }
            else {
                left = nearCoord;
                right = 1 - farCoord;
            }
            let props = {
                zIndex: segHCoords.stackDepth + 1,
                left: left * 100 + '%',
                right: right * 100 + '%',
            };
            if (shouldOverlap && !segHCoords.stackForward) {
                // add padding to the edge so that forward stacked events don't cover the resizer's icon
                props[isRtl ? 'marginLeft' : 'marginRight'] = 10 * 2; // 10 is a guesstimate of the icon's width
            }
            return props;
        }
    }
    function renderPlainFgSegs(sortedFgSegs, { todayRange, nowDate, eventSelection, eventDrag, eventResize }) {
        let hiddenInstances = (eventDrag ? eventDrag.affectedInstances : null) ||
            (eventResize ? eventResize.affectedInstances : null) ||
            {};
        return (preact.createElement(preact.Fragment, null, sortedFgSegs.map((seg) => {
            let instanceId = seg.eventRange.instance.instanceId;
            return (preact.createElement("div", { key: instanceId, style: { visibility: hiddenInstances[instanceId] ? 'hidden' : '' } },
                preact.createElement(TimeColEvent, Object.assign({ seg: seg, isDragging: false, isResizing: false, isDateSelecting: false, isSelected: instanceId === eventSelection, isShort: false }, internal$1.getSegMeta(seg, todayRange, nowDate)))));
        })));
    }
    function computeSegVStyle(segVCoords) {
        if (!segVCoords) {
            return { top: '', bottom: '' };
        }
        return {
            top: segVCoords.start,
            bottom: -segVCoords.end,
        };
    }
    function compileSegsFromEntries(segEntries, allSegs) {
        return segEntries.map((segEntry) => allSegs[segEntry.index]);
    }

    class TimeColsContent extends internal$1.BaseComponent {
        constructor() {
            super(...arguments);
            this.splitFgEventSegs = internal$1.memoize(splitSegsByCol);
            this.splitBgEventSegs = internal$1.memoize(splitSegsByCol);
            this.splitBusinessHourSegs = internal$1.memoize(splitSegsByCol);
            this.splitNowIndicatorSegs = internal$1.memoize(splitSegsByCol);
            this.splitDateSelectionSegs = internal$1.memoize(splitSegsByCol);
            this.splitEventDrag = internal$1.memoize(splitInteractionByCol);
            this.splitEventResize = internal$1.memoize(splitInteractionByCol);
            this.rootElRef = preact.createRef();
            this.cellElRefs = new internal$1.RefMap();
        }
        render() {
            let { props, context } = this;
            let nowIndicatorTop = context.options.nowIndicator &&
                props.slatCoords &&
                props.slatCoords.safeComputeTop(props.nowDate); // might return void
            let colCnt = props.cells.length;
            let fgEventSegsByRow = this.splitFgEventSegs(props.fgEventSegs, colCnt);
            let bgEventSegsByRow = this.splitBgEventSegs(props.bgEventSegs, colCnt);
            let businessHourSegsByRow = this.splitBusinessHourSegs(props.businessHourSegs, colCnt);
            let nowIndicatorSegsByRow = this.splitNowIndicatorSegs(props.nowIndicatorSegs, colCnt);
            let dateSelectionSegsByRow = this.splitDateSelectionSegs(props.dateSelectionSegs, colCnt);
            let eventDragByRow = this.splitEventDrag(props.eventDrag, colCnt);
            let eventResizeByRow = this.splitEventResize(props.eventResize, colCnt);
            return (preact.createElement("div", { className: "fc-timegrid-cols", ref: this.rootElRef },
                preact.createElement("table", { role: "presentation", style: {
                        minWidth: props.tableMinWidth,
                        width: props.clientWidth,
                    } },
                    props.tableColGroupNode,
                    preact.createElement("tbody", { role: "presentation" },
                        preact.createElement("tr", { role: "row" },
                            props.axis && (preact.createElement("td", { "aria-hidden": true, className: "fc-timegrid-col fc-timegrid-axis" },
                                preact.createElement("div", { className: "fc-timegrid-col-frame" },
                                    preact.createElement("div", { className: "fc-timegrid-now-indicator-container" }, typeof nowIndicatorTop === 'number' && (preact.createElement(internal$1.NowIndicatorContainer, { elClasses: ['fc-timegrid-now-indicator-arrow'], elStyle: { top: nowIndicatorTop }, isAxis: true, date: props.nowDate })))))),
                            props.cells.map((cell, i) => (preact.createElement(TimeCol, { key: cell.key, elRef: this.cellElRefs.createRef(cell.key), dateProfile: props.dateProfile, date: cell.date, nowDate: props.nowDate, todayRange: props.todayRange, extraRenderProps: cell.extraRenderProps, extraDataAttrs: cell.extraDataAttrs, extraClassNames: cell.extraClassNames, extraDateSpan: cell.extraDateSpan, fgEventSegs: fgEventSegsByRow[i], bgEventSegs: bgEventSegsByRow[i], businessHourSegs: businessHourSegsByRow[i], nowIndicatorSegs: nowIndicatorSegsByRow[i], dateSelectionSegs: dateSelectionSegsByRow[i], eventDrag: eventDragByRow[i], eventResize: eventResizeByRow[i], slatCoords: props.slatCoords, eventSelection: props.eventSelection, forPrint: props.forPrint }))))))));
        }
        componentDidMount() {
            this.updateCoords();
        }
        componentDidUpdate() {
            this.updateCoords();
        }
        updateCoords() {
            let { props } = this;
            if (props.onColCoords &&
                props.clientWidth !== null // means sizing has stabilized
            ) {
                props.onColCoords(new internal$1.PositionCache(this.rootElRef.current, collectCellEls(this.cellElRefs.currentMap, props.cells), true, // horizontal
                false));
            }
        }
    }
    function collectCellEls(elMap, cells) {
        return cells.map((cell) => elMap[cell.key]);
    }

    /* A component that renders one or more columns of vertical time slots
    ----------------------------------------------------------------------------------------------------------------------*/
    class TimeCols extends internal$1.DateComponent {
        constructor() {
            super(...arguments);
            this.processSlotOptions = internal$1.memoize(processSlotOptions);
            this.state = {
                slatCoords: null,
            };
            this.handleRootEl = (el) => {
                if (el) {
                    this.context.registerInteractiveComponent(this, {
                        el,
                        isHitComboAllowed: this.props.isHitComboAllowed,
                    });
                }
                else {
                    this.context.unregisterInteractiveComponent(this);
                }
            };
            this.handleScrollRequest = (request) => {
                let { onScrollTopRequest } = this.props;
                let { slatCoords } = this.state;
                if (onScrollTopRequest && slatCoords) {
                    if (request.time) {
                        let top = slatCoords.computeTimeTop(request.time);
                        top = Math.ceil(top); // zoom can give weird floating-point values. rather scroll a little bit further
                        if (top) {
                            top += 1; // to overcome top border that slots beyond the first have. looks better
                        }
                        onScrollTopRequest(top);
                    }
                    return true;
                }
                return false;
            };
            this.handleColCoords = (colCoords) => {
                this.colCoords = colCoords;
            };
            this.handleSlatCoords = (slatCoords) => {
                this.setState({ slatCoords });
                if (this.props.onSlatCoords) {
                    this.props.onSlatCoords(slatCoords);
                }
            };
        }
        render() {
            let { props, state } = this;
            return (preact.createElement("div", { className: "fc-timegrid-body", ref: this.handleRootEl, style: {
                    // these props are important to give this wrapper correct dimensions for interactions
                    // TODO: if we set it here, can we avoid giving to inner tables?
                    width: props.clientWidth,
                    minWidth: props.tableMinWidth,
                } },
                preact.createElement(TimeColsSlats, { axis: props.axis, dateProfile: props.dateProfile, slatMetas: props.slatMetas, clientWidth: props.clientWidth, minHeight: props.expandRows ? props.clientHeight : '', tableMinWidth: props.tableMinWidth, tableColGroupNode: props.axis ? props.tableColGroupNode : null /* axis depends on the colgroup's shrinking */, onCoords: this.handleSlatCoords }),
                preact.createElement(TimeColsContent, { cells: props.cells, axis: props.axis, dateProfile: props.dateProfile, businessHourSegs: props.businessHourSegs, bgEventSegs: props.bgEventSegs, fgEventSegs: props.fgEventSegs, dateSelectionSegs: props.dateSelectionSegs, eventSelection: props.eventSelection, eventDrag: props.eventDrag, eventResize: props.eventResize, todayRange: props.todayRange, nowDate: props.nowDate, nowIndicatorSegs: props.nowIndicatorSegs, clientWidth: props.clientWidth, tableMinWidth: props.tableMinWidth, tableColGroupNode: props.tableColGroupNode, slatCoords: state.slatCoords, onColCoords: this.handleColCoords, forPrint: props.forPrint })));
        }
        componentDidMount() {
            this.scrollResponder = this.context.createScrollResponder(this.handleScrollRequest);
        }
        componentDidUpdate(prevProps) {
            this.scrollResponder.update(prevProps.dateProfile !== this.props.dateProfile);
        }
        componentWillUnmount() {
            this.scrollResponder.detach();
        }
        queryHit(positionLeft, positionTop) {
            let { dateEnv, options } = this.context;
            let { colCoords } = this;
            let { dateProfile } = this.props;
            let { slatCoords } = this.state;
            let { snapDuration, snapsPerSlot } = this.processSlotOptions(this.props.slotDuration, options.snapDuration);
            let colIndex = colCoords.leftToIndex(positionLeft);
            let slatIndex = slatCoords.positions.topToIndex(positionTop);
            if (colIndex != null && slatIndex != null) {
                let cell = this.props.cells[colIndex];
                let slatTop = slatCoords.positions.tops[slatIndex];
                let slatHeight = slatCoords.positions.getHeight(slatIndex);
                let partial = (positionTop - slatTop) / slatHeight; // floating point number between 0 and 1
                let localSnapIndex = Math.floor(partial * snapsPerSlot); // the snap # relative to start of slat
                let snapIndex = slatIndex * snapsPerSlot + localSnapIndex;
                let dayDate = this.props.cells[colIndex].date;
                let time = internal$1.addDurations(dateProfile.slotMinTime, internal$1.multiplyDuration(snapDuration, snapIndex));
                let start = dateEnv.add(dayDate, time);
                let end = dateEnv.add(start, snapDuration);
                return {
                    dateProfile,
                    dateSpan: Object.assign({ range: { start, end }, allDay: false }, cell.extraDateSpan),
                    dayEl: colCoords.els[colIndex],
                    rect: {
                        left: colCoords.lefts[colIndex],
                        right: colCoords.rights[colIndex],
                        top: slatTop,
                        bottom: slatTop + slatHeight,
                    },
                    layer: 0,
                };
            }
            return null;
        }
    }
    function processSlotOptions(slotDuration, snapDurationOverride) {
        let snapDuration = snapDurationOverride || slotDuration;
        let snapsPerSlot = internal$1.wholeDivideDurations(slotDuration, snapDuration);
        if (snapsPerSlot === null) {
            snapDuration = slotDuration;
            snapsPerSlot = 1;
            // TODO: say warning?
        }
        return { snapDuration, snapsPerSlot };
    }

    class DayTimeColsSlicer extends internal$1.Slicer {
        sliceRange(range, dayRanges) {
            let segs = [];
            for (let col = 0; col < dayRanges.length; col += 1) {
                let segRange = internal$1.intersectRanges(range, dayRanges[col]);
                if (segRange) {
                    segs.push({
                        start: segRange.start,
                        end: segRange.end,
                        isStart: segRange.start.valueOf() === range.start.valueOf(),
                        isEnd: segRange.end.valueOf() === range.end.valueOf(),
                        col,
                    });
                }
            }
            return segs;
        }
    }

    class DayTimeCols extends internal$1.DateComponent {
        constructor() {
            super(...arguments);
            this.buildDayRanges = internal$1.memoize(buildDayRanges);
            this.slicer = new DayTimeColsSlicer();
            this.timeColsRef = preact.createRef();
        }
        render() {
            let { props, context } = this;
            let { dateProfile, dayTableModel } = props;
            let { nowIndicator, nextDayThreshold } = context.options;
            let dayRanges = this.buildDayRanges(dayTableModel, dateProfile, context.dateEnv);
            // give it the first row of cells
            // TODO: would move this further down hierarchy, but sliceNowDate needs it
            return (preact.createElement(internal$1.NowTimer, { unit: nowIndicator ? 'minute' : 'day' }, (nowDate, todayRange) => (preact.createElement(TimeCols, Object.assign({ ref: this.timeColsRef }, this.slicer.sliceProps(props, dateProfile, null, context, dayRanges), { forPrint: props.forPrint, axis: props.axis, dateProfile: dateProfile, slatMetas: props.slatMetas, slotDuration: props.slotDuration, cells: dayTableModel.cells[0], tableColGroupNode: props.tableColGroupNode, tableMinWidth: props.tableMinWidth, clientWidth: props.clientWidth, clientHeight: props.clientHeight, expandRows: props.expandRows, nowDate: nowDate, nowIndicatorSegs: nowIndicator && this.slicer.sliceNowDate(nowDate, dateProfile, nextDayThreshold, context, dayRanges), todayRange: todayRange, onScrollTopRequest: props.onScrollTopRequest, onSlatCoords: props.onSlatCoords })))));
        }
    }
    function buildDayRanges(dayTableModel, dateProfile, dateEnv) {
        let ranges = [];
        for (let date of dayTableModel.headerDates) {
            ranges.push({
                start: dateEnv.add(date, dateProfile.slotMinTime),
                end: dateEnv.add(date, dateProfile.slotMaxTime),
            });
        }
        return ranges;
    }

    // potential nice values for the slot-duration and interval-duration
    // from largest to smallest
    const STOCK_SUB_DURATIONS = [
        { hours: 1 },
        { minutes: 30 },
        { minutes: 15 },
        { seconds: 30 },
        { seconds: 15 },
    ];
    function buildSlatMetas(slotMinTime, slotMaxTime, explicitLabelInterval, slotDuration, dateEnv) {
        let dayStart = new Date(0);
        let slatTime = slotMinTime;
        let slatIterator = internal$1.createDuration(0);
        let labelInterval = explicitLabelInterval || computeLabelInterval(slotDuration);
        let metas = [];
        while (internal$1.asRoughMs(slatTime) < internal$1.asRoughMs(slotMaxTime)) {
            let date = dateEnv.add(dayStart, slatTime);
            let isLabeled = internal$1.wholeDivideDurations(slatIterator, labelInterval) !== null;
            metas.push({
                date,
                time: slatTime,
                key: date.toISOString(),
                isoTimeStr: internal$1.formatIsoTimeString(date),
                isLabeled,
            });
            slatTime = internal$1.addDurations(slatTime, slotDuration);
            slatIterator = internal$1.addDurations(slatIterator, slotDuration);
        }
        return metas;
    }
    // Computes an automatic value for slotLabelInterval
    function computeLabelInterval(slotDuration) {
        let i;
        let labelInterval;
        let slotsPerLabel;
        // find the smallest stock label interval that results in more than one slots-per-label
        for (i = STOCK_SUB_DURATIONS.length - 1; i >= 0; i -= 1) {
            labelInterval = internal$1.createDuration(STOCK_SUB_DURATIONS[i]);
            slotsPerLabel = internal$1.wholeDivideDurations(labelInterval, slotDuration);
            if (slotsPerLabel !== null && slotsPerLabel > 1) {
                return labelInterval;
            }
        }
        return slotDuration; // fall back
    }

    class DayTimeColsView extends TimeColsView {
        constructor() {
            super(...arguments);
            this.buildTimeColsModel = internal$1.memoize(buildTimeColsModel);
            this.buildSlatMetas = internal$1.memoize(buildSlatMetas);
        }
        render() {
            let { options, dateEnv, dateProfileGenerator } = this.context;
            let { props } = this;
            let { dateProfile } = props;
            let dayTableModel = this.buildTimeColsModel(dateProfile, dateProfileGenerator);
            let splitProps = this.allDaySplitter.splitProps(props);
            let slatMetas = this.buildSlatMetas(dateProfile.slotMinTime, dateProfile.slotMaxTime, options.slotLabelInterval, options.slotDuration, dateEnv);
            let { dayMinWidth } = options;
            let hasAttachedAxis = !dayMinWidth;
            let hasDetachedAxis = dayMinWidth;
            let headerContent = options.dayHeaders && (preact.createElement(internal$1.DayHeader, { dates: dayTableModel.headerDates, dateProfile: dateProfile, datesRepDistinctDays: true, renderIntro: hasAttachedAxis ? this.renderHeadAxis : null }));
            let allDayContent = (options.allDaySlot !== false) && ((contentArg) => (preact.createElement(internal$2.DayTable, Object.assign({}, splitProps.allDay, { dateProfile: dateProfile, dayTableModel: dayTableModel, nextDayThreshold: options.nextDayThreshold, tableMinWidth: contentArg.tableMinWidth, colGroupNode: contentArg.tableColGroupNode, renderRowIntro: hasAttachedAxis ? this.renderTableRowAxis : null, showWeekNumbers: false, expandRows: false, headerAlignElRef: this.headerElRef, clientWidth: contentArg.clientWidth, clientHeight: contentArg.clientHeight, forPrint: props.forPrint }, this.getAllDayMaxEventProps()))));
            let timeGridContent = (contentArg) => (preact.createElement(DayTimeCols, Object.assign({}, splitProps.timed, { dayTableModel: dayTableModel, dateProfile: dateProfile, axis: hasAttachedAxis, slotDuration: options.slotDuration, slatMetas: slatMetas, forPrint: props.forPrint, tableColGroupNode: contentArg.tableColGroupNode, tableMinWidth: contentArg.tableMinWidth, clientWidth: contentArg.clientWidth, clientHeight: contentArg.clientHeight, onSlatCoords: this.handleSlatCoords, expandRows: contentArg.expandRows, onScrollTopRequest: this.handleScrollTopRequest })));
            return hasDetachedAxis
                ? this.renderHScrollLayout(headerContent, allDayContent, timeGridContent, dayTableModel.colCnt, dayMinWidth, slatMetas, this.state.slatCoords)
                : this.renderSimpleLayout(headerContent, allDayContent, timeGridContent);
        }
    }
    function buildTimeColsModel(dateProfile, dateProfileGenerator) {
        let daySeries = new internal$1.DaySeriesModel(dateProfile.renderRange, dateProfileGenerator);
        return new internal$1.DayTableModel(daySeries, false);
    }

    const OPTION_REFINERS = {
        allDaySlot: Boolean,
    };

    var css_248z = ".fc-v-event{background-color:var(--fc-event-bg-color);border:1px solid var(--fc-event-border-color);display:block}.fc-v-event .fc-event-main{color:var(--fc-event-text-color);height:100%}.fc-v-event .fc-event-main-frame{display:flex;flex-direction:column;height:100%}.fc-v-event .fc-event-time{flex-grow:0;flex-shrink:0;max-height:100%;overflow:hidden}.fc-v-event .fc-event-title-container{flex-grow:1;flex-shrink:1;min-height:0}.fc-v-event .fc-event-title{bottom:0;max-height:100%;overflow:hidden;top:0}.fc-v-event:not(.fc-event-start){border-top-left-radius:0;border-top-right-radius:0;border-top-width:0}.fc-v-event:not(.fc-event-end){border-bottom-left-radius:0;border-bottom-right-radius:0;border-bottom-width:0}.fc-v-event.fc-event-selected:before{left:-10px;right:-10px}.fc-v-event .fc-event-resizer-start{cursor:n-resize}.fc-v-event .fc-event-resizer-end{cursor:s-resize}.fc-v-event:not(.fc-event-selected) .fc-event-resizer{height:var(--fc-event-resizer-thickness);left:0;right:0}.fc-v-event:not(.fc-event-selected) .fc-event-resizer-start{top:calc(var(--fc-event-resizer-thickness)/-2)}.fc-v-event:not(.fc-event-selected) .fc-event-resizer-end{bottom:calc(var(--fc-event-resizer-thickness)/-2)}.fc-v-event.fc-event-selected .fc-event-resizer{left:50%;margin-left:calc(var(--fc-event-resizer-dot-total-width)/-2)}.fc-v-event.fc-event-selected .fc-event-resizer-start{top:calc(var(--fc-event-resizer-dot-total-width)/-2)}.fc-v-event.fc-event-selected .fc-event-resizer-end{bottom:calc(var(--fc-event-resizer-dot-total-width)/-2)}.fc .fc-timegrid .fc-daygrid-body{z-index:2}.fc .fc-timegrid-divider{padding:0 0 2px}.fc .fc-timegrid-body{min-height:100%;position:relative;z-index:1}.fc .fc-timegrid-axis-chunk{position:relative}.fc .fc-timegrid-axis-chunk>table,.fc .fc-timegrid-slots{position:relative;z-index:1}.fc .fc-timegrid-slot{border-bottom:0;height:1.5em}.fc .fc-timegrid-slot:empty:before{content:\"\\00a0\"}.fc .fc-timegrid-slot-minor{border-top-style:dotted}.fc .fc-timegrid-slot-label-cushion{display:inline-block;white-space:nowrap}.fc .fc-timegrid-slot-label{vertical-align:middle}.fc .fc-timegrid-axis-cushion,.fc .fc-timegrid-slot-label-cushion{padding:0 4px}.fc .fc-timegrid-axis-frame-liquid{height:100%}.fc .fc-timegrid-axis-frame{align-items:center;display:flex;justify-content:flex-end;overflow:hidden}.fc .fc-timegrid-axis-cushion{flex-shrink:0;max-width:60px}.fc-direction-ltr .fc-timegrid-slot-label-frame{text-align:right}.fc-direction-rtl .fc-timegrid-slot-label-frame{text-align:left}.fc-liquid-hack .fc-timegrid-axis-frame-liquid{bottom:0;height:auto;left:0;position:absolute;right:0;top:0}.fc .fc-timegrid-col.fc-day-today{background-color:var(--fc-today-bg-color)}.fc .fc-timegrid-col-frame{min-height:100%;position:relative}.fc-media-screen.fc-liquid-hack .fc-timegrid-col-frame{bottom:0;height:auto;left:0;position:absolute;right:0;top:0}.fc-media-screen .fc-timegrid-cols{bottom:0;left:0;position:absolute;right:0;top:0}.fc-media-screen .fc-timegrid-cols>table{height:100%}.fc-media-screen .fc-timegrid-col-bg,.fc-media-screen .fc-timegrid-col-events,.fc-media-screen .fc-timegrid-now-indicator-container{left:0;position:absolute;right:0;top:0}.fc .fc-timegrid-col-bg{z-index:2}.fc .fc-timegrid-col-bg .fc-non-business{z-index:1}.fc .fc-timegrid-col-bg .fc-bg-event{z-index:2}.fc .fc-timegrid-col-bg .fc-highlight{z-index:3}.fc .fc-timegrid-bg-harness{left:0;position:absolute;right:0}.fc .fc-timegrid-col-events{z-index:3}.fc .fc-timegrid-now-indicator-container{bottom:0;overflow:hidden}.fc-direction-ltr .fc-timegrid-col-events{margin:0 2.5% 0 2px}.fc-direction-rtl .fc-timegrid-col-events{margin:0 2px 0 2.5%}.fc-timegrid-event-harness{position:absolute}.fc-timegrid-event-harness>.fc-timegrid-event{bottom:0;left:0;position:absolute;right:0;top:0}.fc-timegrid-event-harness-inset .fc-timegrid-event,.fc-timegrid-event.fc-event-mirror,.fc-timegrid-more-link{box-shadow:0 0 0 1px var(--fc-page-bg-color)}.fc-timegrid-event,.fc-timegrid-more-link{border-radius:3px;font-size:var(--fc-small-font-size)}.fc-timegrid-event{margin-bottom:1px}.fc-timegrid-event .fc-event-main{padding:1px 1px 0}.fc-timegrid-event .fc-event-time{font-size:var(--fc-small-font-size);margin-bottom:1px;white-space:nowrap}.fc-timegrid-event-short .fc-event-main-frame{flex-direction:row;overflow:hidden}.fc-timegrid-event-short .fc-event-time:after{content:\"\\00a0-\\00a0\"}.fc-timegrid-event-short .fc-event-title{font-size:var(--fc-small-font-size)}.fc-timegrid-more-link{background:var(--fc-more-link-bg-color);color:var(--fc-more-link-text-color);cursor:pointer;margin-bottom:1px;position:absolute;z-index:9999}.fc-timegrid-more-link-inner{padding:3px 2px;top:0}.fc-direction-ltr .fc-timegrid-more-link{right:0}.fc-direction-rtl .fc-timegrid-more-link{left:0}.fc .fc-timegrid-now-indicator-arrow,.fc .fc-timegrid-now-indicator-line{pointer-events:none}.fc .fc-timegrid-now-indicator-line{border-color:var(--fc-now-indicator-color);border-style:solid;border-width:1px 0 0;left:0;position:absolute;right:0;z-index:4}.fc .fc-timegrid-now-indicator-arrow{border-color:var(--fc-now-indicator-color);border-style:solid;margin-top:-5px;position:absolute;z-index:4}.fc-direction-ltr .fc-timegrid-now-indicator-arrow{border-bottom-color:transparent;border-top-color:transparent;border-width:5px 0 5px 6px;left:0}.fc-direction-rtl .fc-timegrid-now-indicator-arrow{border-bottom-color:transparent;border-top-color:transparent;border-width:5px 6px 5px 0;right:0}";
    internal$1.injectStyles(css_248z);

    var plugin = core.createPlugin({
        name: '@fullcalendar/timegrid',
        initialView: 'timeGridWeek',
        optionRefiners: OPTION_REFINERS,
        views: {
            timeGrid: {
                component: DayTimeColsView,
                usesMinMaxTime: true,
                allDaySlot: true,
                slotDuration: '00:30:00',
                slotEventOverlap: true, // a bad name. confused with overlap/constraint system
            },
            timeGridDay: {
                type: 'timeGrid',
                duration: { days: 1 },
            },
            timeGridWeek: {
                type: 'timeGrid',
                duration: { weeks: 1 },
            },
        },
    });

    var internal = {
        __proto__: null,
        TimeColsView: TimeColsView,
        DayTimeColsView: DayTimeColsView,
        buildTimeColsModel: buildTimeColsModel,
        DayTimeCols: DayTimeCols,
        buildDayRanges: buildDayRanges,
        DayTimeColsSlicer: DayTimeColsSlicer,
        TimeCols: TimeCols,
        buildSlatMetas: buildSlatMetas,
        TimeColsSlatsCoords: TimeColsSlatsCoords
    };

    core.globalPlugins.push(plugin);

    exports.Internal = internal;
    exports["default"] = plugin;

    Object.defineProperty(exports, '__esModule', { value: true });

    return exports;

})({}, FullCalendar, FullCalendar.Internal, FullCalendar.Preact, FullCalendar.DayGrid.Internal);
