/*!
FullCalendar Day Grid Plugin v6.1.20
Docs & License: https://fullcalendar.io/docs/month-view
(c) 2024 Adam Shaw
*/
FullCalendar.DayGrid = (function (exports, core, internal$1, preact) {
    'use strict';

    /* An abstract class for the daygrid views, as well as month view. Renders one or more rows of day cells.
    ----------------------------------------------------------------------------------------------------------------------*/
    // It is a manager for a Table subcomponent, which does most of the heavy lifting.
    // It is responsible for managing width/height.
    class TableView extends internal$1.DateComponent {
        constructor() {
            super(...arguments);
            this.headerElRef = preact.createRef();
        }
        renderSimpleLayout(headerRowContent, bodyContent) {
            let { props, context } = this;
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
            sections.push({
                type: 'body',
                key: 'body',
                liquid: true,
                chunk: { content: bodyContent },
            });
            return (preact.createElement(internal$1.ViewContainer, { elClasses: ['fc-daygrid'], viewSpec: context.viewSpec },
                preact.createElement(internal$1.SimpleScrollGrid, { liquid: !props.isHeightAuto && !props.forPrint, collapsibleWidth: props.forPrint, cols: [] /* TODO: make optional? */, sections: sections })));
        }
        renderHScrollLayout(headerRowContent, bodyContent, colCnt, dayMinWidth) {
            let ScrollGrid = this.context.pluginHooks.scrollGridImpl;
            if (!ScrollGrid) {
                throw new Error('No ScrollGrid implementation');
            }
            let { props, context } = this;
            let stickyHeaderDates = !props.forPrint && internal$1.getStickyHeaderDates(context.options);
            let stickyFooterScrollbar = !props.forPrint && internal$1.getStickyFooterScrollbar(context.options);
            let sections = [];
            if (headerRowContent) {
                sections.push({
                    type: 'header',
                    key: 'header',
                    isSticky: stickyHeaderDates,
                    chunks: [{
                            key: 'main',
                            elRef: this.headerElRef,
                            tableClassName: 'fc-col-header',
                            rowContent: headerRowContent,
                        }],
                });
            }
            sections.push({
                type: 'body',
                key: 'body',
                liquid: true,
                chunks: [{
                        key: 'main',
                        content: bodyContent,
                    }],
            });
            if (stickyFooterScrollbar) {
                sections.push({
                    type: 'footer',
                    key: 'footer',
                    isSticky: true,
                    chunks: [{
                            key: 'main',
                            content: internal$1.renderScrollShim,
                        }],
                });
            }
            return (preact.createElement(internal$1.ViewContainer, { elClasses: ['fc-daygrid'], viewSpec: context.viewSpec },
                preact.createElement(ScrollGrid, { liquid: !props.isHeightAuto && !props.forPrint, forPrint: props.forPrint, collapsibleWidth: props.forPrint, colGroups: [{ cols: [{ span: colCnt, minWidth: dayMinWidth }] }], sections: sections })));
        }
    }

    function splitSegsByRow(segs, rowCnt) {
        let byRow = [];
        for (let i = 0; i < rowCnt; i += 1) {
            byRow[i] = [];
        }
        for (let seg of segs) {
            byRow[seg.row].push(seg);
        }
        return byRow;
    }
    function splitSegsByFirstCol(segs, colCnt) {
        let byCol = [];
        for (let i = 0; i < colCnt; i += 1) {
            byCol[i] = [];
        }
        for (let seg of segs) {
            byCol[seg.firstCol].push(seg);
        }
        return byCol;
    }
    function splitInteractionByRow(ui, rowCnt) {
        let byRow = [];
        if (!ui) {
            for (let i = 0; i < rowCnt; i += 1) {
                byRow[i] = null;
            }
        }
        else {
            for (let i = 0; i < rowCnt; i += 1) {
                byRow[i] = {
                    affectedInstances: ui.affectedInstances,
                    isEvent: ui.isEvent,
                    segs: [],
                };
            }
            for (let seg of ui.segs) {
                byRow[seg.row].segs.push(seg);
            }
        }
        return byRow;
    }

    const DEFAULT_TABLE_EVENT_TIME_FORMAT = internal$1.createFormatter({
        hour: 'numeric',
        minute: '2-digit',
        omitZeroMinute: true,
        meridiem: 'narrow',
    });
    function hasListItemDisplay(seg) {
        let { display } = seg.eventRange.ui;
        return display === 'list-item' || (display === 'auto' &&
            !seg.eventRange.def.allDay &&
            seg.firstCol === seg.lastCol && // can't be multi-day
            seg.isStart && // "
            seg.isEnd // "
        );
    }

    class TableBlockEvent extends internal$1.BaseComponent {
        render() {
            let { props } = this;
            return (preact.createElement(internal$1.StandardEvent, Object.assign({}, props, { elClasses: ['fc-daygrid-event', 'fc-daygrid-block-event', 'fc-h-event'], defaultTimeFormat: DEFAULT_TABLE_EVENT_TIME_FORMAT, defaultDisplayEventEnd: props.defaultDisplayEventEnd, disableResizing: !props.seg.eventRange.def.allDay })));
        }
    }

    class TableListItemEvent extends internal$1.BaseComponent {
        render() {
            let { props, context } = this;
            let { options } = context;
            let { seg } = props;
            let timeFormat = options.eventTimeFormat || DEFAULT_TABLE_EVENT_TIME_FORMAT;
            let timeText = internal$1.buildSegTimeText(seg, timeFormat, context, true, props.defaultDisplayEventEnd);
            return (preact.createElement(internal$1.EventContainer, Object.assign({}, props, { elTag: "a", elClasses: ['fc-daygrid-event', 'fc-daygrid-dot-event'], elAttrs: internal$1.getSegAnchorAttrs(props.seg, context), defaultGenerator: renderInnerContent, timeText: timeText, isResizing: false, isDateSelecting: false })));
        }
    }
    function renderInnerContent(renderProps) {
        return (preact.createElement(preact.Fragment, null,
            preact.createElement("div", { className: "fc-daygrid-event-dot", style: { borderColor: renderProps.borderColor || renderProps.backgroundColor } }),
            renderProps.timeText && (preact.createElement("div", { className: "fc-event-time" }, renderProps.timeText)),
            preact.createElement("div", { className: "fc-event-title" }, renderProps.event.title || preact.createElement(preact.Fragment, null, "\u00A0"))));
    }

    class TableCellMoreLink extends internal$1.BaseComponent {
        constructor() {
            super(...arguments);
            this.compileSegs = internal$1.memoize(compileSegs);
        }
        render() {
            let { props } = this;
            let { allSegs, invisibleSegs } = this.compileSegs(props.singlePlacements);
            return (preact.createElement(internal$1.MoreLinkContainer, { elClasses: ['fc-daygrid-more-link'], dateProfile: props.dateProfile, todayRange: props.todayRange, allDayDate: props.allDayDate, moreCnt: props.moreCnt, allSegs: allSegs, hiddenSegs: invisibleSegs, alignmentElRef: props.alignmentElRef, alignGridTop: props.alignGridTop, extraDateSpan: props.extraDateSpan, popoverContent: () => {
                    let isForcedInvisible = (props.eventDrag ? props.eventDrag.affectedInstances : null) ||
                        (props.eventResize ? props.eventResize.affectedInstances : null) ||
                        {};
                    return (preact.createElement(preact.Fragment, null, allSegs.map((seg) => {
                        let instanceId = seg.eventRange.instance.instanceId;
                        return (preact.createElement("div", { className: "fc-daygrid-event-harness", key: instanceId, style: {
                                visibility: isForcedInvisible[instanceId] ? 'hidden' : '',
                            } }, hasListItemDisplay(seg) ? (preact.createElement(TableListItemEvent, Object.assign({ seg: seg, isDragging: false, isSelected: instanceId === props.eventSelection, defaultDisplayEventEnd: false }, internal$1.getSegMeta(seg, props.todayRange)))) : (preact.createElement(TableBlockEvent, Object.assign({ seg: seg, isDragging: false, isResizing: false, isDateSelecting: false, isSelected: instanceId === props.eventSelection, defaultDisplayEventEnd: false }, internal$1.getSegMeta(seg, props.todayRange))))));
                    })));
                } }));
        }
    }
    function compileSegs(singlePlacements) {
        let allSegs = [];
        let invisibleSegs = [];
        for (let placement of singlePlacements) {
            allSegs.push(placement.seg);
            if (!placement.isVisible) {
                invisibleSegs.push(placement.seg);
            }
        }
        return { allSegs, invisibleSegs };
    }

    const DEFAULT_WEEK_NUM_FORMAT = internal$1.createFormatter({ week: 'narrow' });
    class TableCell extends internal$1.DateComponent {
        constructor() {
            super(...arguments);
            this.rootElRef = preact.createRef();
            this.state = {
                dayNumberId: internal$1.getUniqueDomId(),
            };
            this.handleRootEl = (el) => {
                internal$1.setRef(this.rootElRef, el);
                internal$1.setRef(this.props.elRef, el);
            };
        }
        render() {
            let { context, props, state, rootElRef } = this;
            let { options, dateEnv } = context;
            let { date, dateProfile } = props;
            // TODO: memoize this?
            const isMonthStart = props.showDayNumber &&
                shouldDisplayMonthStart(date, dateProfile.currentRange, dateEnv);
            return (preact.createElement(internal$1.DayCellContainer, { elTag: "td", elRef: this.handleRootEl, elClasses: [
                    'fc-daygrid-day',
                    ...(props.extraClassNames || []),
                ], elAttrs: Object.assign(Object.assign(Object.assign({}, props.extraDataAttrs), (props.showDayNumber ? { 'aria-labelledby': state.dayNumberId } : {})), { role: 'gridcell' }), defaultGenerator: renderTopInner, date: date, dateProfile: dateProfile, todayRange: props.todayRange, showDayNumber: props.showDayNumber, isMonthStart: isMonthStart, extraRenderProps: props.extraRenderProps }, (InnerContent, renderProps) => (preact.createElement("div", { ref: props.innerElRef, className: "fc-daygrid-day-frame fc-scrollgrid-sync-inner", style: { minHeight: props.minHeight } },
                props.showWeekNumber && (preact.createElement(internal$1.WeekNumberContainer, { elTag: "a", elClasses: ['fc-daygrid-week-number'], elAttrs: internal$1.buildNavLinkAttrs(context, date, 'week'), date: date, defaultFormat: DEFAULT_WEEK_NUM_FORMAT })),
                !renderProps.isDisabled &&
                    (props.showDayNumber || internal$1.hasCustomDayCellContent(options) || props.forceDayTop) ? (preact.createElement("div", { className: "fc-daygrid-day-top" },
                    preact.createElement(InnerContent, { elTag: "a", elClasses: [
                            'fc-daygrid-day-number',
                            isMonthStart && 'fc-daygrid-month-start',
                        ], elAttrs: Object.assign(Object.assign({}, internal$1.buildNavLinkAttrs(context, date)), { id: state.dayNumberId }) }))) : props.showDayNumber ? (
                // for creating correct amount of space (see issue #7162)
                preact.createElement("div", { className: "fc-daygrid-day-top", style: { visibility: 'hidden' } },
                    preact.createElement("a", { className: "fc-daygrid-day-number" }, "\u00A0"))) : undefined,
                preact.createElement("div", { className: "fc-daygrid-day-events", ref: props.fgContentElRef },
                    props.fgContent,
                    preact.createElement("div", { className: "fc-daygrid-day-bottom", style: { marginTop: props.moreMarginTop } },
                        preact.createElement(TableCellMoreLink, { allDayDate: date, singlePlacements: props.singlePlacements, moreCnt: props.moreCnt, alignmentElRef: rootElRef, alignGridTop: !props.showDayNumber, extraDateSpan: props.extraDateSpan, dateProfile: props.dateProfile, eventSelection: props.eventSelection, eventDrag: props.eventDrag, eventResize: props.eventResize, todayRange: props.todayRange }))),
                preact.createElement("div", { className: "fc-daygrid-day-bg" }, props.bgContent)))));
        }
    }
    function renderTopInner(props) {
        return props.dayNumberText || preact.createElement(preact.Fragment, null, "\u00A0");
    }
    function shouldDisplayMonthStart(date, currentRange, dateEnv) {
        const { start: currentStart, end: currentEnd } = currentRange;
        const currentEndIncl = internal$1.addMs(currentEnd, -1);
        const currentFirstYear = dateEnv.getYear(currentStart);
        const currentFirstMonth = dateEnv.getMonth(currentStart);
        const currentLastYear = dateEnv.getYear(currentEndIncl);
        const currentLastMonth = dateEnv.getMonth(currentEndIncl);
        // spans more than one month?
        return !(currentFirstYear === currentLastYear && currentFirstMonth === currentLastMonth) &&
            Boolean(
            // first date in current view?
            date.valueOf() === currentStart.valueOf() ||
                // a month-start that's within the current range?
                (dateEnv.getDay(date) === 1 && date.valueOf() < currentEnd.valueOf()));
    }

    function generateSegKey(seg) {
        return seg.eventRange.instance.instanceId + ':' + seg.firstCol;
    }
    function generateSegUid(seg) {
        return generateSegKey(seg) + ':' + seg.lastCol;
    }
    function computeFgSegPlacement(segs, // assumed already sorted
    dayMaxEvents, dayMaxEventRows, strictOrder, segHeights, maxContentHeight, cells) {
        let hierarchy = new DayGridSegHierarchy((segEntry) => {
            // TODO: more DRY with generateSegUid
            let segUid = segs[segEntry.index].eventRange.instance.instanceId +
                ':' + segEntry.span.start +
                ':' + (segEntry.span.end - 1);
            // if no thickness known, assume 1 (if 0, so small it always fits)
            return segHeights[segUid] || 1;
        });
        hierarchy.allowReslicing = true;
        hierarchy.strictOrder = strictOrder;
        if (dayMaxEvents === true || dayMaxEventRows === true) {
            hierarchy.maxCoord = maxContentHeight;
            hierarchy.hiddenConsumes = true;
        }
        else if (typeof dayMaxEvents === 'number') {
            hierarchy.maxStackCnt = dayMaxEvents;
        }
        else if (typeof dayMaxEventRows === 'number') {
            hierarchy.maxStackCnt = dayMaxEventRows;
            hierarchy.hiddenConsumes = true;
        }
        // create segInputs only for segs with known heights
        let segInputs = [];
        let unknownHeightSegs = [];
        for (let i = 0; i < segs.length; i += 1) {
            let seg = segs[i];
            let segUid = generateSegUid(seg);
            let eventHeight = segHeights[segUid];
            if (eventHeight != null) {
                segInputs.push({
                    index: i,
                    span: {
                        start: seg.firstCol,
                        end: seg.lastCol + 1,
                    },
                });
            }
            else {
                unknownHeightSegs.push(seg);
            }
        }
        let hiddenEntries = hierarchy.addSegs(segInputs);
        let segRects = hierarchy.toRects();
        let { singleColPlacements, multiColPlacements, leftoverMargins } = placeRects(segRects, segs, cells);
        let moreCnts = [];
        let moreMarginTops = [];
        // add segs with unknown heights
        for (let seg of unknownHeightSegs) {
            multiColPlacements[seg.firstCol].push({
                seg,
                isVisible: false,
                isAbsolute: true,
                absoluteTop: 0,
                marginTop: 0,
            });
            for (let col = seg.firstCol; col <= seg.lastCol; col += 1) {
                singleColPlacements[col].push({
                    seg: resliceSeg(seg, col, col + 1, cells),
                    isVisible: false,
                    isAbsolute: false,
                    absoluteTop: 0,
                    marginTop: 0,
                });
            }
        }
        // add the hidden entries
        for (let col = 0; col < cells.length; col += 1) {
            moreCnts.push(0);
        }
        for (let hiddenEntry of hiddenEntries) {
            let seg = segs[hiddenEntry.index];
            let hiddenSpan = hiddenEntry.span;
            multiColPlacements[hiddenSpan.start].push({
                seg: resliceSeg(seg, hiddenSpan.start, hiddenSpan.end, cells),
                isVisible: false,
                isAbsolute: true,
                absoluteTop: 0,
                marginTop: 0,
            });
            for (let col = hiddenSpan.start; col < hiddenSpan.end; col += 1) {
                moreCnts[col] += 1;
                singleColPlacements[col].push({
                    seg: resliceSeg(seg, col, col + 1, cells),
                    isVisible: false,
                    isAbsolute: false,
                    absoluteTop: 0,
                    marginTop: 0,
                });
            }
        }
        // deal with leftover margins
        for (let col = 0; col < cells.length; col += 1) {
            moreMarginTops.push(leftoverMargins[col]);
        }
        return { singleColPlacements, multiColPlacements, moreCnts, moreMarginTops };
    }
    // rects ordered by top coord, then left
    function placeRects(allRects, segs, cells) {
        let rectsByEachCol = groupRectsByEachCol(allRects, cells.length);
        let singleColPlacements = [];
        let multiColPlacements = [];
        let leftoverMargins = [];
        for (let col = 0; col < cells.length; col += 1) {
            let rects = rectsByEachCol[col];
            // compute all static segs in singlePlacements
            let singlePlacements = [];
            let currentHeight = 0;
            let currentMarginTop = 0;
            for (let rect of rects) {
                let seg = segs[rect.index];
                singlePlacements.push({
                    seg: resliceSeg(seg, col, col + 1, cells),
                    isVisible: true,
                    isAbsolute: false,
                    absoluteTop: rect.levelCoord,
                    marginTop: rect.levelCoord - currentHeight,
                });
                currentHeight = rect.levelCoord + rect.thickness;
            }
            // compute mixed static/absolute segs in multiPlacements
            let multiPlacements = [];
            currentHeight = 0;
            currentMarginTop = 0;
            for (let rect of rects) {
                let seg = segs[rect.index];
                let isAbsolute = rect.span.end - rect.span.start > 1; // multi-column?
                let isFirstCol = rect.span.start === col;
                currentMarginTop += rect.levelCoord - currentHeight; // amount of space since bottom of previous seg
                currentHeight = rect.levelCoord + rect.thickness; // height will now be bottom of current seg
                if (isAbsolute) {
                    currentMarginTop += rect.thickness;
                    if (isFirstCol) {
                        multiPlacements.push({
                            seg: resliceSeg(seg, rect.span.start, rect.span.end, cells),
                            isVisible: true,
                            isAbsolute: true,
                            absoluteTop: rect.levelCoord,
                            marginTop: 0,
                        });
                    }
                }
                else if (isFirstCol) {
                    multiPlacements.push({
                        seg: resliceSeg(seg, rect.span.start, rect.span.end, cells),
                        isVisible: true,
                        isAbsolute: false,
                        absoluteTop: rect.levelCoord,
                        marginTop: currentMarginTop, // claim the margin
                    });
                    currentMarginTop = 0;
                }
            }
            singleColPlacements.push(singlePlacements);
            multiColPlacements.push(multiPlacements);
            leftoverMargins.push(currentMarginTop);
        }
        return { singleColPlacements, multiColPlacements, leftoverMargins };
    }
    function groupRectsByEachCol(rects, colCnt) {
        let rectsByEachCol = [];
        for (let col = 0; col < colCnt; col += 1) {
            rectsByEachCol.push([]);
        }
        for (let rect of rects) {
            for (let col = rect.span.start; col < rect.span.end; col += 1) {
                rectsByEachCol[col].push(rect);
            }
        }
        return rectsByEachCol;
    }
    function resliceSeg(seg, spanStart, spanEnd, cells) {
        if (seg.firstCol === spanStart && seg.lastCol === spanEnd - 1) {
            return seg;
        }
        let eventRange = seg.eventRange;
        let origRange = eventRange.range;
        let slicedRange = internal$1.intersectRanges(origRange, {
            start: cells[spanStart].date,
            end: internal$1.addDays(cells[spanEnd - 1].date, 1),
        });
        return Object.assign(Object.assign({}, seg), { firstCol: spanStart, lastCol: spanEnd - 1, eventRange: {
                def: eventRange.def,
                ui: Object.assign(Object.assign({}, eventRange.ui), { durationEditable: false }),
                instance: eventRange.instance,
                range: slicedRange,
            }, isStart: seg.isStart && slicedRange.start.valueOf() === origRange.start.valueOf(), isEnd: seg.isEnd && slicedRange.end.valueOf() === origRange.end.valueOf() });
    }
    class DayGridSegHierarchy extends internal$1.SegHierarchy {
        constructor() {
            super(...arguments);
            // config
            this.hiddenConsumes = false;
            // allows us to keep hidden entries in the hierarchy so they take up space
            this.forceHidden = {};
        }
        addSegs(segInputs) {
            const hiddenSegs = super.addSegs(segInputs);
            const { entriesByLevel } = this;
            const excludeHidden = (entry) => !this.forceHidden[internal$1.buildEntryKey(entry)];
            // remove the forced-hidden segs
            for (let level = 0; level < entriesByLevel.length; level += 1) {
                entriesByLevel[level] = entriesByLevel[level].filter(excludeHidden);
            }
            return hiddenSegs;
        }
        handleInvalidInsertion(insertion, entry, hiddenEntries) {
            const { entriesByLevel, forceHidden } = this;
            const { touchingEntry, touchingLevel, touchingLateral } = insertion;
            // the entry that the new insertion is touching must be hidden
            if (this.hiddenConsumes && touchingEntry) {
                const touchingEntryId = internal$1.buildEntryKey(touchingEntry);
                if (!forceHidden[touchingEntryId]) {
                    if (this.allowReslicing) {
                        // split up the touchingEntry, reinsert it
                        const hiddenEntry = Object.assign(Object.assign({}, touchingEntry), { span: internal$1.intersectSpans(touchingEntry.span, entry.span) });
                        // reinsert the area that turned into a "more" link (so no other entries try to
                        // occupy the space) but mark it forced-hidden
                        const hiddenEntryId = internal$1.buildEntryKey(hiddenEntry);
                        forceHidden[hiddenEntryId] = true;
                        entriesByLevel[touchingLevel][touchingLateral] = hiddenEntry;
                        hiddenEntries.push(hiddenEntry);
                        this.splitEntry(touchingEntry, entry, hiddenEntries);
                    }
                    else {
                        forceHidden[touchingEntryId] = true;
                        hiddenEntries.push(touchingEntry);
                    }
                }
            }
            // will try to reslice...
            super.handleInvalidInsertion(insertion, entry, hiddenEntries);
        }
    }

    class TableRow extends internal$1.DateComponent {
        constructor() {
            super(...arguments);
            this.cellElRefs = new internal$1.RefMap(); // the <td>
            this.frameElRefs = new internal$1.RefMap(); // the fc-daygrid-day-frame
            this.fgElRefs = new internal$1.RefMap(); // the fc-daygrid-day-events
            this.segHarnessRefs = new internal$1.RefMap(); // indexed by "instanceId:firstCol"
            this.rootElRef = preact.createRef();
            this.state = {
                framePositions: null,
                maxContentHeight: null,
                segHeights: {},
            };
            this.handleResize = (isForced) => {
                if (isForced) {
                    this.updateSizing(true); // isExternal=true
                }
            };
        }
        render() {
            let { props, state, context } = this;
            let { options } = context;
            let colCnt = props.cells.length;
            let businessHoursByCol = splitSegsByFirstCol(props.businessHourSegs, colCnt);
            let bgEventSegsByCol = splitSegsByFirstCol(props.bgEventSegs, colCnt);
            let highlightSegsByCol = splitSegsByFirstCol(this.getHighlightSegs(), colCnt);
            let mirrorSegsByCol = splitSegsByFirstCol(this.getMirrorSegs(), colCnt);
            let { singleColPlacements, multiColPlacements, moreCnts, moreMarginTops } = computeFgSegPlacement(internal$1.sortEventSegs(props.fgEventSegs, options.eventOrder), props.dayMaxEvents, props.dayMaxEventRows, options.eventOrderStrict, state.segHeights, state.maxContentHeight, props.cells);
            let isForcedInvisible = // TODO: messy way to compute this
             (props.eventDrag && props.eventDrag.affectedInstances) ||
                (props.eventResize && props.eventResize.affectedInstances) ||
                {};
            return (preact.createElement("tr", { ref: this.rootElRef, role: "row" },
                props.renderIntro && props.renderIntro(),
                props.cells.map((cell, col) => {
                    let normalFgNodes = this.renderFgSegs(col, props.forPrint ? singleColPlacements[col] : multiColPlacements[col], props.todayRange, isForcedInvisible);
                    let mirrorFgNodes = this.renderFgSegs(col, buildMirrorPlacements(mirrorSegsByCol[col], multiColPlacements), props.todayRange, {}, Boolean(props.eventDrag), Boolean(props.eventResize), false);
                    return (preact.createElement(TableCell, { key: cell.key, elRef: this.cellElRefs.createRef(cell.key), innerElRef: this.frameElRefs.createRef(cell.key) /* FF <td> problem, but okay to use for left/right. TODO: rename prop */, dateProfile: props.dateProfile, date: cell.date, showDayNumber: props.showDayNumbers, showWeekNumber: props.showWeekNumbers && col === 0, forceDayTop: props.showWeekNumbers /* even displaying weeknum for row, not necessarily day */, todayRange: props.todayRange, eventSelection: props.eventSelection, eventDrag: props.eventDrag, eventResize: props.eventResize, extraRenderProps: cell.extraRenderProps, extraDataAttrs: cell.extraDataAttrs, extraClassNames: cell.extraClassNames, extraDateSpan: cell.extraDateSpan, moreCnt: moreCnts[col], moreMarginTop: moreMarginTops[col], singlePlacements: singleColPlacements[col], fgContentElRef: this.fgElRefs.createRef(cell.key), fgContent: ( // Fragment scopes the keys
                        preact.createElement(preact.Fragment, null,
                            preact.createElement(preact.Fragment, null, normalFgNodes),
                            preact.createElement(preact.Fragment, null, mirrorFgNodes))), bgContent: ( // Fragment scopes the keys
                        preact.createElement(preact.Fragment, null,
                            this.renderFillSegs(highlightSegsByCol[col], 'highlight'),
                            this.renderFillSegs(businessHoursByCol[col], 'non-business'),
                            this.renderFillSegs(bgEventSegsByCol[col], 'bg-event'))), minHeight: props.cellMinHeight }));
                })));
        }
        componentDidMount() {
            this.updateSizing(true);
            this.context.addResizeHandler(this.handleResize);
        }
        componentDidUpdate(prevProps, prevState) {
            let currentProps = this.props;
            this.updateSizing(!internal$1.isPropsEqual(prevProps, currentProps));
        }
        componentWillUnmount() {
            this.context.removeResizeHandler(this.handleResize);
        }
        getHighlightSegs() {
            let { props } = this;
            if (props.eventDrag && props.eventDrag.segs.length) { // messy check
                return props.eventDrag.segs;
            }
            if (props.eventResize && props.eventResize.segs.length) { // messy check
                return props.eventResize.segs;
            }
            return props.dateSelectionSegs;
        }
        getMirrorSegs() {
            let { props } = this;
            if (props.eventResize && props.eventResize.segs.length) { // messy check
                return props.eventResize.segs;
            }
            return [];
        }
        renderFgSegs(col, segPlacements, todayRange, isForcedInvisible, isDragging, isResizing, isDateSelecting) {
            let { context } = this;
            let { eventSelection } = this.props;
            let { framePositions } = this.state;
            let defaultDisplayEventEnd = this.props.cells.length === 1; // colCnt === 1
            let isMirror = isDragging || isResizing || isDateSelecting;
            let nodes = [];
            if (framePositions) {
                for (let placement of segPlacements) {
                    let { seg } = placement;
                    let { instanceId } = seg.eventRange.instance;
                    let isVisible = placement.isVisible && !isForcedInvisible[instanceId];
                    let isAbsolute = placement.isAbsolute;
                    let left = '';
                    let right = '';
                    if (isAbsolute) {
                        if (context.isRtl) {
                            right = 0;
                            left = framePositions.lefts[seg.lastCol] - framePositions.lefts[seg.firstCol];
                        }
                        else {
                            left = 0;
                            right = framePositions.rights[seg.firstCol] - framePositions.rights[seg.lastCol];
                        }
                    }
                    /*
                    known bug: events that are force to be list-item but span multiple days still take up space in later columns
                    todo: in print view, for multi-day events, don't display title within non-start/end segs
                    */
                    nodes.push(preact.createElement("div", { className: 'fc-daygrid-event-harness' + (isAbsolute ? ' fc-daygrid-event-harness-abs' : ''), key: generateSegKey(seg), ref: isMirror ? null : this.segHarnessRefs.createRef(generateSegUid(seg)), style: {
                            visibility: isVisible ? '' : 'hidden',
                            marginTop: isAbsolute ? '' : placement.marginTop,
                            top: isAbsolute ? placement.absoluteTop : '',
                            left,
                            right,
                        } }, hasListItemDisplay(seg) ? (preact.createElement(TableListItemEvent, Object.assign({ seg: seg, isDragging: isDragging, isSelected: instanceId === eventSelection, defaultDisplayEventEnd: defaultDisplayEventEnd }, internal$1.getSegMeta(seg, todayRange)))) : (preact.createElement(TableBlockEvent, Object.assign({ seg: seg, isDragging: isDragging, isResizing: isResizing, isDateSelecting: isDateSelecting, isSelected: instanceId === eventSelection, defaultDisplayEventEnd: defaultDisplayEventEnd }, internal$1.getSegMeta(seg, todayRange))))));
                }
            }
            return nodes;
        }
        renderFillSegs(segs, fillType) {
            let { isRtl } = this.context;
            let { todayRange } = this.props;
            let { framePositions } = this.state;
            let nodes = [];
            if (framePositions) {
                for (let seg of segs) {
                    let leftRightCss = isRtl ? {
                        right: 0,
                        left: framePositions.lefts[seg.lastCol] - framePositions.lefts[seg.firstCol],
                    } : {
                        left: 0,
                        right: framePositions.rights[seg.firstCol] - framePositions.rights[seg.lastCol],
                    };
                    nodes.push(preact.createElement("div", { key: internal$1.buildEventRangeKey(seg.eventRange), className: "fc-daygrid-bg-harness", style: leftRightCss }, fillType === 'bg-event' ?
                        preact.createElement(internal$1.BgEvent, Object.assign({ seg: seg }, internal$1.getSegMeta(seg, todayRange))) :
                        internal$1.renderFill(fillType)));
                }
            }
            return preact.createElement(preact.Fragment, {}, ...nodes);
        }
        updateSizing(isExternalSizingChange) {
            let { props, state, frameElRefs } = this;
            if (!props.forPrint &&
                props.clientWidth !== null // positioning ready?
            ) {
                if (isExternalSizingChange) {
                    let frameEls = props.cells.map((cell) => frameElRefs.currentMap[cell.key]);
                    if (frameEls.length) {
                        let originEl = this.rootElRef.current;
                        let newPositionCache = new internal$1.PositionCache(originEl, frameEls, true, // isHorizontal
                        false);
                        if (!state.framePositions || !state.framePositions.similarTo(newPositionCache)) {
                            this.setState({
                                framePositions: new internal$1.PositionCache(originEl, frameEls, true, // isHorizontal
                                false),
                            });
                        }
                    }
                }
                const oldSegHeights = this.state.segHeights;
                const newSegHeights = this.querySegHeights();
                const limitByContentHeight = props.dayMaxEvents === true || props.dayMaxEventRows === true;
                this.safeSetState({
                    // HACK to prevent oscillations of events being shown/hidden from max-event-rows
                    // Essentially, once you compute an element's height, never null-out.
                    // TODO: always display all events, as visibility:hidden?
                    segHeights: Object.assign(Object.assign({}, oldSegHeights), newSegHeights),
                    maxContentHeight: limitByContentHeight ? this.computeMaxContentHeight() : null,
                });
            }
        }
        querySegHeights() {
            let segElMap = this.segHarnessRefs.currentMap;
            let segHeights = {};
            // get the max height amongst instance segs
            for (let segUid in segElMap) {
                let height = Math.round(segElMap[segUid].getBoundingClientRect().height);
                segHeights[segUid] = Math.max(segHeights[segUid] || 0, height);
            }
            return segHeights;
        }
        computeMaxContentHeight() {
            let firstKey = this.props.cells[0].key;
            let cellEl = this.cellElRefs.currentMap[firstKey];
            let fcContainerEl = this.fgElRefs.currentMap[firstKey];
            return cellEl.getBoundingClientRect().bottom - fcContainerEl.getBoundingClientRect().top;
        }
        getCellEls() {
            let elMap = this.cellElRefs.currentMap;
            return this.props.cells.map((cell) => elMap[cell.key]);
        }
    }
    TableRow.addStateEquality({
        segHeights: internal$1.isPropsEqual,
    });
    function buildMirrorPlacements(mirrorSegs, colPlacements) {
        if (!mirrorSegs.length) {
            return [];
        }
        let topsByInstanceId = buildAbsoluteTopHash(colPlacements); // TODO: cache this at first render?
        return mirrorSegs.map((seg) => ({
            seg,
            isVisible: true,
            isAbsolute: true,
            absoluteTop: topsByInstanceId[seg.eventRange.instance.instanceId],
            marginTop: 0,
        }));
    }
    function buildAbsoluteTopHash(colPlacements) {
        let topsByInstanceId = {};
        for (let placements of colPlacements) {
            for (let placement of placements) {
                topsByInstanceId[placement.seg.eventRange.instance.instanceId] = placement.absoluteTop;
            }
        }
        return topsByInstanceId;
    }

    class TableRows extends internal$1.DateComponent {
        constructor() {
            super(...arguments);
            this.splitBusinessHourSegs = internal$1.memoize(splitSegsByRow);
            this.splitBgEventSegs = internal$1.memoize(splitAllDaySegsByRow);
            this.splitFgEventSegs = internal$1.memoize(splitSegsByRow);
            this.splitDateSelectionSegs = internal$1.memoize(splitSegsByRow);
            this.splitEventDrag = internal$1.memoize(splitInteractionByRow);
            this.splitEventResize = internal$1.memoize(splitInteractionByRow);
            this.rowRefs = new internal$1.RefMap();
        }
        render() {
            let { props, context } = this;
            let rowCnt = props.cells.length;
            let businessHourSegsByRow = this.splitBusinessHourSegs(props.businessHourSegs, rowCnt);
            let bgEventSegsByRow = this.splitBgEventSegs(props.bgEventSegs, rowCnt);
            let fgEventSegsByRow = this.splitFgEventSegs(props.fgEventSegs, rowCnt);
            let dateSelectionSegsByRow = this.splitDateSelectionSegs(props.dateSelectionSegs, rowCnt);
            let eventDragByRow = this.splitEventDrag(props.eventDrag, rowCnt);
            let eventResizeByRow = this.splitEventResize(props.eventResize, rowCnt);
            // for DayGrid view with many rows, force a min-height on cells so doesn't appear squished
            // choose 7 because a month view will have max 6 rows
            let cellMinHeight = (rowCnt >= 7 && props.clientWidth) ?
                props.clientWidth / context.options.aspectRatio / 6 :
                null;
            return (preact.createElement(internal$1.NowTimer, { unit: "day" }, (nowDate, todayRange) => (preact.createElement(preact.Fragment, null, props.cells.map((cells, row) => (preact.createElement(TableRow, { ref: this.rowRefs.createRef(row), key: cells.length
                    ? cells[0].date.toISOString() /* best? or put key on cell? or use diff formatter? */
                    : row // in case there are no cells (like when resource view is loading)
                , showDayNumbers: rowCnt > 1, showWeekNumbers: props.showWeekNumbers, todayRange: todayRange, dateProfile: props.dateProfile, cells: cells, renderIntro: props.renderRowIntro, businessHourSegs: businessHourSegsByRow[row], eventSelection: props.eventSelection, bgEventSegs: bgEventSegsByRow[row], fgEventSegs: fgEventSegsByRow[row], dateSelectionSegs: dateSelectionSegsByRow[row], eventDrag: eventDragByRow[row], eventResize: eventResizeByRow[row], dayMaxEvents: props.dayMaxEvents, dayMaxEventRows: props.dayMaxEventRows, clientWidth: props.clientWidth, clientHeight: props.clientHeight, cellMinHeight: cellMinHeight, forPrint: props.forPrint })))))));
        }
        componentDidMount() {
            this.registerInteractiveComponent();
        }
        componentDidUpdate() {
            // for if started with zero cells
            this.registerInteractiveComponent();
        }
        registerInteractiveComponent() {
            if (!this.rootEl) {
                // HACK: need a daygrid wrapper parent to do positioning
                // NOTE: a daygrid resource view w/o resources can have zero cells
                const firstCellEl = this.rowRefs.currentMap[0].getCellEls()[0];
                const rootEl = firstCellEl ? firstCellEl.closest('.fc-daygrid-body') : null;
                if (rootEl) {
                    this.rootEl = rootEl;
                    this.context.registerInteractiveComponent(this, {
                        el: rootEl,
                        isHitComboAllowed: this.props.isHitComboAllowed,
                    });
                }
            }
        }
        componentWillUnmount() {
            if (this.rootEl) {
                this.context.unregisterInteractiveComponent(this);
                this.rootEl = null;
            }
        }
        // Hit System
        // ----------------------------------------------------------------------------------------------------
        prepareHits() {
            this.rowPositions = new internal$1.PositionCache(this.rootEl, this.rowRefs.collect().map((rowObj) => rowObj.getCellEls()[0]), // first cell el in each row. TODO: not optimal
            false, true);
            this.colPositions = new internal$1.PositionCache(this.rootEl, this.rowRefs.currentMap[0].getCellEls(), // cell els in first row
            true, // horizontal
            false);
        }
        queryHit(positionLeft, positionTop) {
            let { colPositions, rowPositions } = this;
            let col = colPositions.leftToIndex(positionLeft);
            let row = rowPositions.topToIndex(positionTop);
            if (row != null && col != null) {
                let cell = this.props.cells[row][col];
                return {
                    dateProfile: this.props.dateProfile,
                    dateSpan: Object.assign({ range: this.getCellRange(row, col), allDay: true }, cell.extraDateSpan),
                    dayEl: this.getCellEl(row, col),
                    rect: {
                        left: colPositions.lefts[col],
                        right: colPositions.rights[col],
                        top: rowPositions.tops[row],
                        bottom: rowPositions.bottoms[row],
                    },
                    layer: 0,
                };
            }
            return null;
        }
        getCellEl(row, col) {
            return this.rowRefs.currentMap[row].getCellEls()[col]; // TODO: not optimal
        }
        getCellRange(row, col) {
            let start = this.props.cells[row][col].date;
            let end = internal$1.addDays(start, 1);
            return { start, end };
        }
    }
    function splitAllDaySegsByRow(segs, rowCnt) {
        return splitSegsByRow(segs.filter(isSegAllDay), rowCnt);
    }
    function isSegAllDay(seg) {
        return seg.eventRange.def.allDay;
    }

    class Table extends internal$1.DateComponent {
        constructor() {
            super(...arguments);
            this.elRef = preact.createRef();
            this.needsScrollReset = false;
        }
        render() {
            let { props } = this;
            let { dayMaxEventRows, dayMaxEvents, expandRows } = props;
            let limitViaBalanced = dayMaxEvents === true || dayMaxEventRows === true;
            // if rows can't expand to fill fixed height, can't do balanced-height event limit
            // TODO: best place to normalize these options?
            if (limitViaBalanced && !expandRows) {
                limitViaBalanced = false;
                dayMaxEventRows = null;
                dayMaxEvents = null;
            }
            let classNames = [
                'fc-daygrid-body',
                limitViaBalanced ? 'fc-daygrid-body-balanced' : 'fc-daygrid-body-unbalanced',
                expandRows ? '' : 'fc-daygrid-body-natural', // will height of one row depend on the others?
            ];
            return (preact.createElement("div", { ref: this.elRef, className: classNames.join(' '), style: {
                    // these props are important to give this wrapper correct dimensions for interactions
                    // TODO: if we set it here, can we avoid giving to inner tables?
                    width: props.clientWidth,
                    minWidth: props.tableMinWidth,
                } },
                preact.createElement("table", { role: "presentation", className: "fc-scrollgrid-sync-table", style: {
                        width: props.clientWidth,
                        minWidth: props.tableMinWidth,
                        height: expandRows ? props.clientHeight : '',
                    } },
                    props.colGroupNode,
                    preact.createElement("tbody", { role: "presentation" },
                        preact.createElement(TableRows, { dateProfile: props.dateProfile, cells: props.cells, renderRowIntro: props.renderRowIntro, showWeekNumbers: props.showWeekNumbers, clientWidth: props.clientWidth, clientHeight: props.clientHeight, businessHourSegs: props.businessHourSegs, bgEventSegs: props.bgEventSegs, fgEventSegs: props.fgEventSegs, dateSelectionSegs: props.dateSelectionSegs, eventSelection: props.eventSelection, eventDrag: props.eventDrag, eventResize: props.eventResize, dayMaxEvents: dayMaxEvents, dayMaxEventRows: dayMaxEventRows, forPrint: props.forPrint, isHitComboAllowed: props.isHitComboAllowed })))));
        }
        componentDidMount() {
            this.requestScrollReset();
        }
        componentDidUpdate(prevProps) {
            if (prevProps.dateProfile !== this.props.dateProfile) {
                this.requestScrollReset();
            }
            else {
                this.flushScrollReset();
            }
        }
        requestScrollReset() {
            this.needsScrollReset = true;
            this.flushScrollReset();
        }
        flushScrollReset() {
            if (this.needsScrollReset &&
                this.props.clientWidth // sizes computed?
            ) {
                const subjectEl = getScrollSubjectEl(this.elRef.current, this.props.dateProfile);
                if (subjectEl) {
                    const originEl = subjectEl.closest('.fc-daygrid-body');
                    const scrollEl = originEl.closest('.fc-scroller');
                    const scrollTop = subjectEl.getBoundingClientRect().top -
                        originEl.getBoundingClientRect().top;
                    scrollEl.scrollTop = scrollTop ? (scrollTop + 1) : 0; // overcome border
                }
                this.needsScrollReset = false;
            }
        }
    }
    function getScrollSubjectEl(containerEl, dateProfile) {
        let el;
        if (dateProfile.currentRangeUnit.match(/year|month/)) {
            el = containerEl.querySelector(`[data-date="${internal$1.formatIsoMonthStr(dateProfile.currentDate)}-01"]`);
            // even if view is month-based, first-of-month might be hidden...
        }
        if (!el) {
            el = containerEl.querySelector(`[data-date="${internal$1.formatDayString(dateProfile.currentDate)}"]`);
            // could still be hidden if an interior-view hidden day
        }
        return el;
    }

    class DayTableSlicer extends internal$1.Slicer {
        constructor() {
            super(...arguments);
            this.forceDayIfListItem = true;
        }
        sliceRange(dateRange, dayTableModel) {
            return dayTableModel.sliceRange(dateRange);
        }
    }

    class DayTable extends internal$1.DateComponent {
        constructor() {
            super(...arguments);
            this.slicer = new DayTableSlicer();
            this.tableRef = preact.createRef();
        }
        render() {
            let { props, context } = this;
            return (preact.createElement(Table, Object.assign({ ref: this.tableRef }, this.slicer.sliceProps(props, props.dateProfile, props.nextDayThreshold, context, props.dayTableModel), { dateProfile: props.dateProfile, cells: props.dayTableModel.cells, colGroupNode: props.colGroupNode, tableMinWidth: props.tableMinWidth, renderRowIntro: props.renderRowIntro, dayMaxEvents: props.dayMaxEvents, dayMaxEventRows: props.dayMaxEventRows, showWeekNumbers: props.showWeekNumbers, expandRows: props.expandRows, headerAlignElRef: props.headerAlignElRef, clientWidth: props.clientWidth, clientHeight: props.clientHeight, forPrint: props.forPrint })));
        }
    }

    class DayTableView extends TableView {
        constructor() {
            super(...arguments);
            this.buildDayTableModel = internal$1.memoize(buildDayTableModel);
            this.headerRef = preact.createRef();
            this.tableRef = preact.createRef();
            // can't override any lifecycle methods from parent
        }
        render() {
            let { options, dateProfileGenerator } = this.context;
            let { props } = this;
            let dayTableModel = this.buildDayTableModel(props.dateProfile, dateProfileGenerator);
            let headerContent = options.dayHeaders && (preact.createElement(internal$1.DayHeader, { ref: this.headerRef, dateProfile: props.dateProfile, dates: dayTableModel.headerDates, datesRepDistinctDays: dayTableModel.rowCnt === 1 }));
            let bodyContent = (contentArg) => (preact.createElement(DayTable, { ref: this.tableRef, dateProfile: props.dateProfile, dayTableModel: dayTableModel, businessHours: props.businessHours, dateSelection: props.dateSelection, eventStore: props.eventStore, eventUiBases: props.eventUiBases, eventSelection: props.eventSelection, eventDrag: props.eventDrag, eventResize: props.eventResize, nextDayThreshold: options.nextDayThreshold, colGroupNode: contentArg.tableColGroupNode, tableMinWidth: contentArg.tableMinWidth, dayMaxEvents: options.dayMaxEvents, dayMaxEventRows: options.dayMaxEventRows, showWeekNumbers: options.weekNumbers, expandRows: !props.isHeightAuto, headerAlignElRef: this.headerElRef, clientWidth: contentArg.clientWidth, clientHeight: contentArg.clientHeight, forPrint: props.forPrint }));
            return options.dayMinWidth
                ? this.renderHScrollLayout(headerContent, bodyContent, dayTableModel.colCnt, options.dayMinWidth)
                : this.renderSimpleLayout(headerContent, bodyContent);
        }
    }
    function buildDayTableModel(dateProfile, dateProfileGenerator) {
        let daySeries = new internal$1.DaySeriesModel(dateProfile.renderRange, dateProfileGenerator);
        return new internal$1.DayTableModel(daySeries, /year|month|week/.test(dateProfile.currentRangeUnit));
    }

    class TableDateProfileGenerator extends internal$1.DateProfileGenerator {
        // Computes the date range that will be rendered
        buildRenderRange(currentRange, currentRangeUnit, isRangeAllDay) {
            let renderRange = super.buildRenderRange(currentRange, currentRangeUnit, isRangeAllDay);
            let { props } = this;
            return buildDayTableRenderRange({
                currentRange: renderRange,
                snapToWeek: /^(year|month)$/.test(currentRangeUnit),
                fixedWeekCount: props.fixedWeekCount,
                dateEnv: props.dateEnv,
            });
        }
    }
    function buildDayTableRenderRange(props) {
        let { dateEnv, currentRange } = props;
        let { start, end } = currentRange;
        let endOfWeek;
        // year and month views should be aligned with weeks. this is already done for week
        if (props.snapToWeek) {
            start = dateEnv.startOfWeek(start);
            // make end-of-week if not already
            endOfWeek = dateEnv.startOfWeek(end);
            if (endOfWeek.valueOf() !== end.valueOf()) {
                end = internal$1.addWeeks(endOfWeek, 1);
            }
        }
        // ensure 6 weeks
        if (props.fixedWeekCount) {
            // TODO: instead of these date-math gymnastics (for multimonth view),
            // compute dateprofiles of all months, then use start of first and end of last.
            let lastMonthRenderStart = dateEnv.startOfWeek(dateEnv.startOfMonth(internal$1.addDays(currentRange.end, -1)));
            let rowCnt = Math.ceil(// could be partial weeks due to hiddenDays
            internal$1.diffWeeks(lastMonthRenderStart, end));
            end = internal$1.addWeeks(end, 6 - rowCnt);
        }
        return { start, end };
    }

    var css_248z = ":root{--fc-daygrid-event-dot-width:8px}.fc-daygrid-day-events:after,.fc-daygrid-day-events:before,.fc-daygrid-day-frame:after,.fc-daygrid-day-frame:before,.fc-daygrid-event-harness:after,.fc-daygrid-event-harness:before{clear:both;content:\"\";display:table}.fc .fc-daygrid-body{position:relative;z-index:1}.fc .fc-daygrid-day.fc-day-today{background-color:var(--fc-today-bg-color)}.fc .fc-daygrid-day-frame{min-height:100%;position:relative}.fc .fc-daygrid-day-top{display:flex;flex-direction:row-reverse}.fc .fc-day-other .fc-daygrid-day-top{opacity:.3}.fc .fc-daygrid-day-number{padding:4px;position:relative;z-index:4}.fc .fc-daygrid-month-start{font-size:1.1em;font-weight:700}.fc .fc-daygrid-day-events{margin-top:1px}.fc .fc-daygrid-body-balanced .fc-daygrid-day-events{left:0;position:absolute;right:0}.fc .fc-daygrid-body-unbalanced .fc-daygrid-day-events{min-height:2em;position:relative}.fc .fc-daygrid-body-natural .fc-daygrid-day-events{margin-bottom:1em}.fc .fc-daygrid-event-harness{position:relative}.fc .fc-daygrid-event-harness-abs{left:0;position:absolute;right:0;top:0}.fc .fc-daygrid-bg-harness{bottom:0;position:absolute;top:0}.fc .fc-daygrid-day-bg .fc-non-business{z-index:1}.fc .fc-daygrid-day-bg .fc-bg-event{z-index:2}.fc .fc-daygrid-day-bg .fc-highlight{z-index:3}.fc .fc-daygrid-event{margin-top:1px;z-index:6}.fc .fc-daygrid-event.fc-event-mirror{z-index:7}.fc .fc-daygrid-day-bottom{font-size:.85em;margin:0 2px}.fc .fc-daygrid-day-bottom:after,.fc .fc-daygrid-day-bottom:before{clear:both;content:\"\";display:table}.fc .fc-daygrid-more-link{border-radius:3px;cursor:pointer;line-height:1;margin-top:1px;max-width:100%;overflow:hidden;padding:2px;position:relative;white-space:nowrap;z-index:4}.fc .fc-daygrid-more-link:hover{background-color:rgba(0,0,0,.1)}.fc .fc-daygrid-week-number{background-color:var(--fc-neutral-bg-color);color:var(--fc-neutral-text-color);min-width:1.5em;padding:2px;position:absolute;text-align:center;top:0;z-index:5}.fc .fc-more-popover .fc-popover-body{min-width:220px;padding:10px}.fc-direction-ltr .fc-daygrid-event.fc-event-start,.fc-direction-rtl .fc-daygrid-event.fc-event-end{margin-left:2px}.fc-direction-ltr .fc-daygrid-event.fc-event-end,.fc-direction-rtl .fc-daygrid-event.fc-event-start{margin-right:2px}.fc-direction-ltr .fc-daygrid-more-link{float:left}.fc-direction-ltr .fc-daygrid-week-number{border-radius:0 0 3px 0;left:0}.fc-direction-rtl .fc-daygrid-more-link{float:right}.fc-direction-rtl .fc-daygrid-week-number{border-radius:0 0 0 3px;right:0}.fc-liquid-hack .fc-daygrid-day-frame{position:static}.fc-daygrid-event{border-radius:3px;font-size:var(--fc-small-font-size);position:relative;white-space:nowrap}.fc-daygrid-block-event .fc-event-time{font-weight:700}.fc-daygrid-block-event .fc-event-time,.fc-daygrid-block-event .fc-event-title{padding:1px}.fc-daygrid-dot-event{align-items:center;display:flex;padding:2px 0}.fc-daygrid-dot-event .fc-event-title{flex-grow:1;flex-shrink:1;font-weight:700;min-width:0;overflow:hidden}.fc-daygrid-dot-event.fc-event-mirror,.fc-daygrid-dot-event:hover{background:rgba(0,0,0,.1)}.fc-daygrid-dot-event.fc-event-selected:before{bottom:-10px;top:-10px}.fc-daygrid-event-dot{border:calc(var(--fc-daygrid-event-dot-width)/2) solid var(--fc-event-border-color);border-radius:calc(var(--fc-daygrid-event-dot-width)/2);box-sizing:content-box;height:0;margin:0 4px;width:0}.fc-direction-ltr .fc-daygrid-event .fc-event-time{margin-right:3px}.fc-direction-rtl .fc-daygrid-event .fc-event-time{margin-left:3px}";
    internal$1.injectStyles(css_248z);

    var plugin = core.createPlugin({
        name: '@fullcalendar/daygrid',
        initialView: 'dayGridMonth',
        views: {
            dayGrid: {
                component: DayTableView,
                dateProfileGeneratorClass: TableDateProfileGenerator,
            },
            dayGridDay: {
                type: 'dayGrid',
                duration: { days: 1 },
            },
            dayGridWeek: {
                type: 'dayGrid',
                duration: { weeks: 1 },
            },
            dayGridMonth: {
                type: 'dayGrid',
                duration: { months: 1 },
                fixedWeekCount: true,
            },
            dayGridYear: {
                type: 'dayGrid',
                duration: { years: 1 },
            },
        },
    });

    var internal = {
        __proto__: null,
        DayTable: DayTable,
        DayTableSlicer: DayTableSlicer,
        TableDateProfileGenerator: TableDateProfileGenerator,
        buildDayTableRenderRange: buildDayTableRenderRange,
        Table: Table,
        TableRows: TableRows,
        TableView: TableView,
        buildDayTableModel: buildDayTableModel,
        DayGridView: DayTableView
    };

    core.globalPlugins.push(plugin);

    exports.Internal = internal;
    exports["default"] = plugin;

    Object.defineProperty(exports, '__esModule', { value: true });

    return exports;

})({}, FullCalendar, FullCalendar.Internal, FullCalendar.Preact);
