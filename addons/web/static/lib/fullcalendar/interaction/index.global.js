/*!
FullCalendar Interaction Plugin v6.1.15
Docs & License: https://fullcalendar.io/docs/editable
(c) 2024 Adam Shaw
*/
FullCalendar.Interaction = (function (exports, core, internal) {
    'use strict';

    internal.config.touchMouseIgnoreWait = 500;
    let ignoreMouseDepth = 0;
    let listenerCnt = 0;
    let isWindowTouchMoveCancelled = false;
    /*
    Uses a "pointer" abstraction, which monitors UI events for both mouse and touch.
    Tracks when the pointer "drags" on a certain element, meaning down+move+up.

    Also, tracks if there was touch-scrolling.
    Also, can prevent touch-scrolling from happening.
    Also, can fire pointermove events when scrolling happens underneath, even when no real pointer movement.

    emits:
    - pointerdown
    - pointermove
    - pointerup
    */
    class PointerDragging {
        constructor(containerEl) {
            this.subjectEl = null;
            // options that can be directly assigned by caller
            this.selector = ''; // will cause subjectEl in all emitted events to be this element
            this.handleSelector = '';
            this.shouldIgnoreMove = false;
            this.shouldWatchScroll = true; // for simulating pointermove on scroll
            // internal states
            this.isDragging = false;
            this.isTouchDragging = false;
            this.wasTouchScroll = false;
            // Mouse
            // ----------------------------------------------------------------------------------------------------
            this.handleMouseDown = (ev) => {
                if (!this.shouldIgnoreMouse() &&
                    isPrimaryMouseButton(ev) &&
                    this.tryStart(ev)) {
                    let pev = this.createEventFromMouse(ev, true);
                    this.emitter.trigger('pointerdown', pev);
                    this.initScrollWatch(pev);
                    if (!this.shouldIgnoreMove) {
                        document.addEventListener('mousemove', this.handleMouseMove);
                    }
                    document.addEventListener('mouseup', this.handleMouseUp);
                }
            };
            this.handleMouseMove = (ev) => {
                let pev = this.createEventFromMouse(ev);
                this.recordCoords(pev);
                this.emitter.trigger('pointermove', pev);
            };
            this.handleMouseUp = (ev) => {
                document.removeEventListener('mousemove', this.handleMouseMove);
                document.removeEventListener('mouseup', this.handleMouseUp);
                this.emitter.trigger('pointerup', this.createEventFromMouse(ev));
                this.cleanup(); // call last so that pointerup has access to props
            };
            // Touch
            // ----------------------------------------------------------------------------------------------------
            this.handleTouchStart = (ev) => {
                if (this.tryStart(ev)) {
                    this.isTouchDragging = true;
                    let pev = this.createEventFromTouch(ev, true);
                    this.emitter.trigger('pointerdown', pev);
                    this.initScrollWatch(pev);
                    // unlike mouse, need to attach to target, not document
                    // https://stackoverflow.com/a/45760014
                    let targetEl = ev.target;
                    if (!this.shouldIgnoreMove) {
                        targetEl.addEventListener('touchmove', this.handleTouchMove);
                    }
                    targetEl.addEventListener('touchend', this.handleTouchEnd);
                    targetEl.addEventListener('touchcancel', this.handleTouchEnd); // treat it as a touch end
                    // attach a handler to get called when ANY scroll action happens on the page.
                    // this was impossible to do with normal on/off because 'scroll' doesn't bubble.
                    // http://stackoverflow.com/a/32954565/96342
                    window.addEventListener('scroll', this.handleTouchScroll, true);
                }
            };
            this.handleTouchMove = (ev) => {
                let pev = this.createEventFromTouch(ev);
                this.recordCoords(pev);
                this.emitter.trigger('pointermove', pev);
            };
            this.handleTouchEnd = (ev) => {
                if (this.isDragging) { // done to guard against touchend followed by touchcancel
                    let targetEl = ev.target;
                    targetEl.removeEventListener('touchmove', this.handleTouchMove);
                    targetEl.removeEventListener('touchend', this.handleTouchEnd);
                    targetEl.removeEventListener('touchcancel', this.handleTouchEnd);
                    window.removeEventListener('scroll', this.handleTouchScroll, true); // useCaptured=true
                    this.emitter.trigger('pointerup', this.createEventFromTouch(ev));
                    this.cleanup(); // call last so that pointerup has access to props
                    this.isTouchDragging = false;
                    startIgnoringMouse();
                }
            };
            this.handleTouchScroll = () => {
                this.wasTouchScroll = true;
            };
            this.handleScroll = (ev) => {
                if (!this.shouldIgnoreMove) {
                    let pageX = (window.scrollX - this.prevScrollX) + this.prevPageX;
                    let pageY = (window.scrollY - this.prevScrollY) + this.prevPageY;
                    this.emitter.trigger('pointermove', {
                        origEvent: ev,
                        isTouch: this.isTouchDragging,
                        subjectEl: this.subjectEl,
                        pageX,
                        pageY,
                        deltaX: pageX - this.origPageX,
                        deltaY: pageY - this.origPageY,
                    });
                }
            };
            this.containerEl = containerEl;
            this.emitter = new internal.Emitter();
            containerEl.addEventListener('mousedown', this.handleMouseDown);
            containerEl.addEventListener('touchstart', this.handleTouchStart, { passive: true });
            listenerCreated();
        }
        destroy() {
            this.containerEl.removeEventListener('mousedown', this.handleMouseDown);
            this.containerEl.removeEventListener('touchstart', this.handleTouchStart, { passive: true });
            listenerDestroyed();
        }
        tryStart(ev) {
            let subjectEl = this.querySubjectEl(ev);
            let downEl = ev.target;
            if (subjectEl &&
                (!this.handleSelector || internal.elementClosest(downEl, this.handleSelector))) {
                this.subjectEl = subjectEl;
                this.isDragging = true; // do this first so cancelTouchScroll will work
                this.wasTouchScroll = false;
                return true;
            }
            return false;
        }
        cleanup() {
            isWindowTouchMoveCancelled = false;
            this.isDragging = false;
            this.subjectEl = null;
            // keep wasTouchScroll around for later access
            this.destroyScrollWatch();
        }
        querySubjectEl(ev) {
            if (this.selector) {
                return internal.elementClosest(ev.target, this.selector);
            }
            return this.containerEl;
        }
        shouldIgnoreMouse() {
            return ignoreMouseDepth || this.isTouchDragging;
        }
        // can be called by user of this class, to cancel touch-based scrolling for the current drag
        cancelTouchScroll() {
            if (this.isDragging) {
                isWindowTouchMoveCancelled = true;
            }
        }
        // Scrolling that simulates pointermoves
        // ----------------------------------------------------------------------------------------------------
        initScrollWatch(ev) {
            if (this.shouldWatchScroll) {
                this.recordCoords(ev);
                window.addEventListener('scroll', this.handleScroll, true); // useCapture=true
            }
        }
        recordCoords(ev) {
            if (this.shouldWatchScroll) {
                this.prevPageX = ev.pageX;
                this.prevPageY = ev.pageY;
                this.prevScrollX = window.scrollX;
                this.prevScrollY = window.scrollY;
            }
        }
        destroyScrollWatch() {
            if (this.shouldWatchScroll) {
                window.removeEventListener('scroll', this.handleScroll, true); // useCaptured=true
            }
        }
        // Event Normalization
        // ----------------------------------------------------------------------------------------------------
        createEventFromMouse(ev, isFirst) {
            let deltaX = 0;
            let deltaY = 0;
            // TODO: repeat code
            if (isFirst) {
                this.origPageX = ev.pageX;
                this.origPageY = ev.pageY;
            }
            else {
                deltaX = ev.pageX - this.origPageX;
                deltaY = ev.pageY - this.origPageY;
            }
            return {
                origEvent: ev,
                isTouch: false,
                subjectEl: this.subjectEl,
                pageX: ev.pageX,
                pageY: ev.pageY,
                deltaX,
                deltaY,
            };
        }
        createEventFromTouch(ev, isFirst) {
            let touches = ev.touches;
            let pageX;
            let pageY;
            let deltaX = 0;
            let deltaY = 0;
            // if touch coords available, prefer,
            // because FF would give bad ev.pageX ev.pageY
            if (touches && touches.length) {
                pageX = touches[0].pageX;
                pageY = touches[0].pageY;
            }
            else {
                pageX = ev.pageX;
                pageY = ev.pageY;
            }
            // TODO: repeat code
            if (isFirst) {
                this.origPageX = pageX;
                this.origPageY = pageY;
            }
            else {
                deltaX = pageX - this.origPageX;
                deltaY = pageY - this.origPageY;
            }
            return {
                origEvent: ev,
                isTouch: true,
                subjectEl: this.subjectEl,
                pageX,
                pageY,
                deltaX,
                deltaY,
            };
        }
    }
    // Returns a boolean whether this was a left mouse click and no ctrl key (which means right click on Mac)
    function isPrimaryMouseButton(ev) {
        return ev.button === 0 && !ev.ctrlKey;
    }
    // Ignoring fake mouse events generated by touch
    // ----------------------------------------------------------------------------------------------------
    function startIgnoringMouse() {
        ignoreMouseDepth += 1;
        setTimeout(() => {
            ignoreMouseDepth -= 1;
        }, internal.config.touchMouseIgnoreWait);
    }
    // We want to attach touchmove as early as possible for Safari
    // ----------------------------------------------------------------------------------------------------
    function listenerCreated() {
        listenerCnt += 1;
        if (listenerCnt === 1) {
            window.addEventListener('touchmove', onWindowTouchMove, { passive: false });
        }
    }
    function listenerDestroyed() {
        listenerCnt -= 1;
        if (!listenerCnt) {
            window.removeEventListener('touchmove', onWindowTouchMove, { passive: false });
        }
    }
    function onWindowTouchMove(ev) {
        if (isWindowTouchMoveCancelled) {
            ev.preventDefault();
        }
    }

    /*
    An effect in which an element follows the movement of a pointer across the screen.
    The moving element is a clone of some other element.
    Must call start + handleMove + stop.
    */
    class ElementMirror {
        constructor() {
            this.isVisible = false; // must be explicitly enabled
            this.sourceEl = null;
            this.mirrorEl = null;
            this.sourceElRect = null; // screen coords relative to viewport
            // options that can be set directly by caller
            this.parentNode = document.body; // HIGHLY SUGGESTED to set this to sidestep ShadowDOM issues
            this.zIndex = 9999;
            this.revertDuration = 0;
        }
        start(sourceEl, pageX, pageY) {
            this.sourceEl = sourceEl;
            this.sourceElRect = this.sourceEl.getBoundingClientRect();
            this.origScreenX = pageX - window.scrollX;
            this.origScreenY = pageY - window.scrollY;
            this.deltaX = 0;
            this.deltaY = 0;
            this.updateElPosition();
        }
        handleMove(pageX, pageY) {
            this.deltaX = (pageX - window.scrollX) - this.origScreenX;
            this.deltaY = (pageY - window.scrollY) - this.origScreenY;
            this.updateElPosition();
        }
        // can be called before start
        setIsVisible(bool) {
            if (bool) {
                if (!this.isVisible) {
                    if (this.mirrorEl) {
                        this.mirrorEl.style.display = '';
                    }
                    this.isVisible = bool; // needs to happen before updateElPosition
                    this.updateElPosition(); // because was not updating the position while invisible
                }
            }
            else if (this.isVisible) {
                if (this.mirrorEl) {
                    this.mirrorEl.style.display = 'none';
                }
                this.isVisible = bool;
            }
        }
        // always async
        stop(needsRevertAnimation, callback) {
            let done = () => {
                this.cleanup();
                callback();
            };
            if (needsRevertAnimation &&
                this.mirrorEl &&
                this.isVisible &&
                this.revertDuration && // if 0, transition won't work
                (this.deltaX || this.deltaY) // if same coords, transition won't work
            ) {
                this.doRevertAnimation(done, this.revertDuration);
            }
            else {
                setTimeout(done, 0);
            }
        }
        doRevertAnimation(callback, revertDuration) {
            let mirrorEl = this.mirrorEl;
            let finalSourceElRect = this.sourceEl.getBoundingClientRect(); // because autoscrolling might have happened
            mirrorEl.style.transition =
                'top ' + revertDuration + 'ms,' +
                    'left ' + revertDuration + 'ms';
            internal.applyStyle(mirrorEl, {
                left: finalSourceElRect.left,
                top: finalSourceElRect.top,
            });
            internal.whenTransitionDone(mirrorEl, () => {
                mirrorEl.style.transition = '';
                callback();
            });
        }
        cleanup() {
            if (this.mirrorEl) {
                internal.removeElement(this.mirrorEl);
                this.mirrorEl = null;
            }
            this.sourceEl = null;
        }
        updateElPosition() {
            if (this.sourceEl && this.isVisible) {
                internal.applyStyle(this.getMirrorEl(), {
                    left: this.sourceElRect.left + this.deltaX,
                    top: this.sourceElRect.top + this.deltaY,
                });
            }
        }
        getMirrorEl() {
            let sourceElRect = this.sourceElRect;
            let mirrorEl = this.mirrorEl;
            if (!mirrorEl) {
                mirrorEl = this.mirrorEl = this.sourceEl.cloneNode(true); // cloneChildren=true
                // we don't want long taps or any mouse interaction causing selection/menus.
                // would use preventSelection(), but that prevents selectstart, causing problems.
                mirrorEl.style.userSelect = 'none';
                mirrorEl.style.webkitUserSelect = 'none';
                mirrorEl.style.pointerEvents = 'none';
                mirrorEl.classList.add('fc-event-dragging');
                internal.applyStyle(mirrorEl, {
                    position: 'fixed',
                    zIndex: this.zIndex,
                    visibility: '',
                    boxSizing: 'border-box',
                    width: sourceElRect.right - sourceElRect.left,
                    height: sourceElRect.bottom - sourceElRect.top,
                    right: 'auto',
                    bottom: 'auto',
                    margin: 0,
                });
                this.parentNode.appendChild(mirrorEl);
            }
            return mirrorEl;
        }
    }

    /*
    Is a cache for a given element's scroll information (all the info that ScrollController stores)
    in addition the "client rectangle" of the element.. the area within the scrollbars.

    The cache can be in one of two modes:
    - doesListening:false - ignores when the container is scrolled by someone else
    - doesListening:true - watch for scrolling and update the cache
    */
    class ScrollGeomCache extends internal.ScrollController {
        constructor(scrollController, doesListening) {
            super();
            this.handleScroll = () => {
                this.scrollTop = this.scrollController.getScrollTop();
                this.scrollLeft = this.scrollController.getScrollLeft();
                this.handleScrollChange();
            };
            this.scrollController = scrollController;
            this.doesListening = doesListening;
            this.scrollTop = this.origScrollTop = scrollController.getScrollTop();
            this.scrollLeft = this.origScrollLeft = scrollController.getScrollLeft();
            this.scrollWidth = scrollController.getScrollWidth();
            this.scrollHeight = scrollController.getScrollHeight();
            this.clientWidth = scrollController.getClientWidth();
            this.clientHeight = scrollController.getClientHeight();
            this.clientRect = this.computeClientRect(); // do last in case it needs cached values
            if (this.doesListening) {
                this.getEventTarget().addEventListener('scroll', this.handleScroll);
            }
        }
        destroy() {
            if (this.doesListening) {
                this.getEventTarget().removeEventListener('scroll', this.handleScroll);
            }
        }
        getScrollTop() {
            return this.scrollTop;
        }
        getScrollLeft() {
            return this.scrollLeft;
        }
        setScrollTop(top) {
            this.scrollController.setScrollTop(top);
            if (!this.doesListening) {
                // we are not relying on the element to normalize out-of-bounds scroll values
                // so we need to sanitize ourselves
                this.scrollTop = Math.max(Math.min(top, this.getMaxScrollTop()), 0);
                this.handleScrollChange();
            }
        }
        setScrollLeft(top) {
            this.scrollController.setScrollLeft(top);
            if (!this.doesListening) {
                // we are not relying on the element to normalize out-of-bounds scroll values
                // so we need to sanitize ourselves
                this.scrollLeft = Math.max(Math.min(top, this.getMaxScrollLeft()), 0);
                this.handleScrollChange();
            }
        }
        getClientWidth() {
            return this.clientWidth;
        }
        getClientHeight() {
            return this.clientHeight;
        }
        getScrollWidth() {
            return this.scrollWidth;
        }
        getScrollHeight() {
            return this.scrollHeight;
        }
        handleScrollChange() {
        }
    }

    class ElementScrollGeomCache extends ScrollGeomCache {
        constructor(el, doesListening) {
            super(new internal.ElementScrollController(el), doesListening);
        }
        getEventTarget() {
            return this.scrollController.el;
        }
        computeClientRect() {
            return internal.computeInnerRect(this.scrollController.el);
        }
    }

    class WindowScrollGeomCache extends ScrollGeomCache {
        constructor(doesListening) {
            super(new internal.WindowScrollController(), doesListening);
        }
        getEventTarget() {
            return window;
        }
        computeClientRect() {
            return {
                left: this.scrollLeft,
                right: this.scrollLeft + this.clientWidth,
                top: this.scrollTop,
                bottom: this.scrollTop + this.clientHeight,
            };
        }
        // the window is the only scroll object that changes it's rectangle relative
        // to the document's topleft as it scrolls
        handleScrollChange() {
            this.clientRect = this.computeClientRect();
        }
    }

    // If available we are using native "performance" API instead of "Date"
    // Read more about it on MDN:
    // https://developer.mozilla.org/en-US/docs/Web/API/Performance
    const getTime = typeof performance === 'function' ? performance.now : Date.now;
    /*
    For a pointer interaction, automatically scrolls certain scroll containers when the pointer
    approaches the edge.

    The caller must call start + handleMove + stop.
    */
    class AutoScroller {
        constructor() {
            // options that can be set by caller
            this.isEnabled = true;
            this.scrollQuery = [window, '.fc-scroller'];
            this.edgeThreshold = 50; // pixels
            this.maxVelocity = 300; // pixels per second
            // internal state
            this.pointerScreenX = null;
            this.pointerScreenY = null;
            this.isAnimating = false;
            this.scrollCaches = null;
            // protect against the initial pointerdown being too close to an edge and starting the scroll
            this.everMovedUp = false;
            this.everMovedDown = false;
            this.everMovedLeft = false;
            this.everMovedRight = false;
            this.animate = () => {
                if (this.isAnimating) { // wasn't cancelled between animation calls
                    let edge = this.computeBestEdge(this.pointerScreenX + window.scrollX, this.pointerScreenY + window.scrollY);
                    if (edge) {
                        let now = getTime();
                        this.handleSide(edge, (now - this.msSinceRequest) / 1000);
                        this.requestAnimation(now);
                    }
                    else {
                        this.isAnimating = false; // will stop animation
                    }
                }
            };
        }
        start(pageX, pageY, scrollStartEl) {
            if (this.isEnabled) {
                this.scrollCaches = this.buildCaches(scrollStartEl);
                this.pointerScreenX = null;
                this.pointerScreenY = null;
                this.everMovedUp = false;
                this.everMovedDown = false;
                this.everMovedLeft = false;
                this.everMovedRight = false;
                this.handleMove(pageX, pageY);
            }
        }
        handleMove(pageX, pageY) {
            if (this.isEnabled) {
                let pointerScreenX = pageX - window.scrollX;
                let pointerScreenY = pageY - window.scrollY;
                let yDelta = this.pointerScreenY === null ? 0 : pointerScreenY - this.pointerScreenY;
                let xDelta = this.pointerScreenX === null ? 0 : pointerScreenX - this.pointerScreenX;
                if (yDelta < 0) {
                    this.everMovedUp = true;
                }
                else if (yDelta > 0) {
                    this.everMovedDown = true;
                }
                if (xDelta < 0) {
                    this.everMovedLeft = true;
                }
                else if (xDelta > 0) {
                    this.everMovedRight = true;
                }
                this.pointerScreenX = pointerScreenX;
                this.pointerScreenY = pointerScreenY;
                if (!this.isAnimating) {
                    this.isAnimating = true;
                    this.requestAnimation(getTime());
                }
            }
        }
        stop() {
            if (this.isEnabled) {
                this.isAnimating = false; // will stop animation
                for (let scrollCache of this.scrollCaches) {
                    scrollCache.destroy();
                }
                this.scrollCaches = null;
            }
        }
        requestAnimation(now) {
            this.msSinceRequest = now;
            requestAnimationFrame(this.animate);
        }
        handleSide(edge, seconds) {
            let { scrollCache } = edge;
            let { edgeThreshold } = this;
            let invDistance = edgeThreshold - edge.distance;
            let velocity = // the closer to the edge, the faster we scroll
             ((invDistance * invDistance) / (edgeThreshold * edgeThreshold)) * // quadratic
                this.maxVelocity * seconds;
            let sign = 1;
            switch (edge.name) {
                case 'left':
                    sign = -1;
                // falls through
                case 'right':
                    scrollCache.setScrollLeft(scrollCache.getScrollLeft() + velocity * sign);
                    break;
                case 'top':
                    sign = -1;
                // falls through
                case 'bottom':
                    scrollCache.setScrollTop(scrollCache.getScrollTop() + velocity * sign);
                    break;
            }
        }
        // left/top are relative to document topleft
        computeBestEdge(left, top) {
            let { edgeThreshold } = this;
            let bestSide = null;
            let scrollCaches = this.scrollCaches || [];
            for (let scrollCache of scrollCaches) {
                let rect = scrollCache.clientRect;
                let leftDist = left - rect.left;
                let rightDist = rect.right - left;
                let topDist = top - rect.top;
                let bottomDist = rect.bottom - top;
                // completely within the rect?
                if (leftDist >= 0 && rightDist >= 0 && topDist >= 0 && bottomDist >= 0) {
                    if (topDist <= edgeThreshold && this.everMovedUp && scrollCache.canScrollUp() &&
                        (!bestSide || bestSide.distance > topDist)) {
                        bestSide = { scrollCache, name: 'top', distance: topDist };
                    }
                    if (bottomDist <= edgeThreshold && this.everMovedDown && scrollCache.canScrollDown() &&
                        (!bestSide || bestSide.distance > bottomDist)) {
                        bestSide = { scrollCache, name: 'bottom', distance: bottomDist };
                    }
                    /*
                    TODO: fix broken RTL scrolling. canScrollLeft always returning false
                    https://github.com/fullcalendar/fullcalendar/issues/4837
                    */
                    if (leftDist <= edgeThreshold && this.everMovedLeft && scrollCache.canScrollLeft() &&
                        (!bestSide || bestSide.distance > leftDist)) {
                        bestSide = { scrollCache, name: 'left', distance: leftDist };
                    }
                    if (rightDist <= edgeThreshold && this.everMovedRight && scrollCache.canScrollRight() &&
                        (!bestSide || bestSide.distance > rightDist)) {
                        bestSide = { scrollCache, name: 'right', distance: rightDist };
                    }
                }
            }
            return bestSide;
        }
        buildCaches(scrollStartEl) {
            return this.queryScrollEls(scrollStartEl).map((el) => {
                if (el === window) {
                    return new WindowScrollGeomCache(false); // false = don't listen to user-generated scrolls
                }
                return new ElementScrollGeomCache(el, false); // false = don't listen to user-generated scrolls
            });
        }
        queryScrollEls(scrollStartEl) {
            let els = [];
            for (let query of this.scrollQuery) {
                if (typeof query === 'object') {
                    els.push(query);
                }
                else {
                    /*
                    TODO: in the future, always have auto-scroll happen on element where current Hit came from
                    Ticket: https://github.com/fullcalendar/fullcalendar/issues/4593
                    */
                    els.push(...Array.prototype.slice.call(scrollStartEl.getRootNode().querySelectorAll(query)));
                }
            }
            return els;
        }
    }

    /*
    Monitors dragging on an element. Has a number of high-level features:
    - minimum distance required before dragging
    - minimum wait time ("delay") before dragging
    - a mirror element that follows the pointer
    */
    class FeaturefulElementDragging extends internal.ElementDragging {
        constructor(containerEl, selector) {
            super(containerEl);
            this.containerEl = containerEl;
            // options that can be directly set by caller
            // the caller can also set the PointerDragging's options as well
            this.delay = null;
            this.minDistance = 0;
            this.touchScrollAllowed = true; // prevents drag from starting and blocks scrolling during drag
            this.mirrorNeedsRevert = false;
            this.isInteracting = false; // is the user validly moving the pointer? lasts until pointerup
            this.isDragging = false; // is it INTENTFULLY dragging? lasts until after revert animation
            this.isDelayEnded = false;
            this.isDistanceSurpassed = false;
            this.delayTimeoutId = null;
            this.onPointerDown = (ev) => {
                if (!this.isDragging) { // so new drag doesn't happen while revert animation is going
                    this.isInteracting = true;
                    this.isDelayEnded = false;
                    this.isDistanceSurpassed = false;
                    internal.preventSelection(document.body);
                    internal.preventContextMenu(document.body);
                    // prevent links from being visited if there's an eventual drag.
                    // also prevents selection in older browsers (maybe?).
                    // not necessary for touch, besides, browser would complain about passiveness.
                    if (!ev.isTouch) {
                        ev.origEvent.preventDefault();
                    }
                    this.emitter.trigger('pointerdown', ev);
                    if (this.isInteracting && // not destroyed via pointerdown handler
                        !this.pointer.shouldIgnoreMove) {
                        // actions related to initiating dragstart+dragmove+dragend...
                        this.mirror.setIsVisible(false); // reset. caller must set-visible
                        this.mirror.start(ev.subjectEl, ev.pageX, ev.pageY); // must happen on first pointer down
                        this.startDelay(ev);
                        if (!this.minDistance) {
                            this.handleDistanceSurpassed(ev);
                        }
                    }
                }
            };
            this.onPointerMove = (ev) => {
                if (this.isInteracting) {
                    this.emitter.trigger('pointermove', ev);
                    if (!this.isDistanceSurpassed) {
                        let minDistance = this.minDistance;
                        let distanceSq; // current distance from the origin, squared
                        let { deltaX, deltaY } = ev;
                        distanceSq = deltaX * deltaX + deltaY * deltaY;
                        if (distanceSq >= minDistance * minDistance) { // use pythagorean theorem
                            this.handleDistanceSurpassed(ev);
                        }
                    }
                    if (this.isDragging) {
                        // a real pointer move? (not one simulated by scrolling)
                        if (ev.origEvent.type !== 'scroll') {
                            this.mirror.handleMove(ev.pageX, ev.pageY);
                            this.autoScroller.handleMove(ev.pageX, ev.pageY);
                        }
                        this.emitter.trigger('dragmove', ev);
                    }
                }
            };
            this.onPointerUp = (ev) => {
                if (this.isInteracting) {
                    this.isInteracting = false;
                    internal.allowSelection(document.body);
                    internal.allowContextMenu(document.body);
                    this.emitter.trigger('pointerup', ev); // can potentially set mirrorNeedsRevert
                    if (this.isDragging) {
                        this.autoScroller.stop();
                        this.tryStopDrag(ev); // which will stop the mirror
                    }
                    if (this.delayTimeoutId) {
                        clearTimeout(this.delayTimeoutId);
                        this.delayTimeoutId = null;
                    }
                }
            };
            let pointer = this.pointer = new PointerDragging(containerEl);
            pointer.emitter.on('pointerdown', this.onPointerDown);
            pointer.emitter.on('pointermove', this.onPointerMove);
            pointer.emitter.on('pointerup', this.onPointerUp);
            if (selector) {
                pointer.selector = selector;
            }
            this.mirror = new ElementMirror();
            this.autoScroller = new AutoScroller();
        }
        destroy() {
            this.pointer.destroy();
            // HACK: simulate a pointer-up to end the current drag
            // TODO: fire 'dragend' directly and stop interaction. discourage use of pointerup event (b/c might not fire)
            this.onPointerUp({});
        }
        startDelay(ev) {
            if (typeof this.delay === 'number') {
                this.delayTimeoutId = setTimeout(() => {
                    this.delayTimeoutId = null;
                    this.handleDelayEnd(ev);
                }, this.delay); // not assignable to number!
            }
            else {
                this.handleDelayEnd(ev);
            }
        }
        handleDelayEnd(ev) {
            this.isDelayEnded = true;
            this.tryStartDrag(ev);
        }
        handleDistanceSurpassed(ev) {
            this.isDistanceSurpassed = true;
            this.tryStartDrag(ev);
        }
        tryStartDrag(ev) {
            if (this.isDelayEnded && this.isDistanceSurpassed) {
                if (!this.pointer.wasTouchScroll || this.touchScrollAllowed) {
                    this.isDragging = true;
                    this.mirrorNeedsRevert = false;
                    this.autoScroller.start(ev.pageX, ev.pageY, this.containerEl);
                    this.emitter.trigger('dragstart', ev);
                    if (this.touchScrollAllowed === false) {
                        this.pointer.cancelTouchScroll();
                    }
                }
            }
        }
        tryStopDrag(ev) {
            // .stop() is ALWAYS asynchronous, which we NEED because we want all pointerup events
            // that come from the document to fire beforehand. much more convenient this way.
            this.mirror.stop(this.mirrorNeedsRevert, this.stopDrag.bind(this, ev));
        }
        stopDrag(ev) {
            this.isDragging = false;
            this.emitter.trigger('dragend', ev);
        }
        // fill in the implementations...
        setIgnoreMove(bool) {
            this.pointer.shouldIgnoreMove = bool;
        }
        setMirrorIsVisible(bool) {
            this.mirror.setIsVisible(bool);
        }
        setMirrorNeedsRevert(bool) {
            this.mirrorNeedsRevert = bool;
        }
        setAutoScrollEnabled(bool) {
            this.autoScroller.isEnabled = bool;
        }
    }

    /*
    When this class is instantiated, it records the offset of an element (relative to the document topleft),
    and continues to monitor scrolling, updating the cached coordinates if it needs to.
    Does not access the DOM after instantiation, so highly performant.

    Also keeps track of all scrolling/overflow:hidden containers that are parents of the given element
    and an determine if a given point is inside the combined clipping rectangle.
    */
    class OffsetTracker {
        constructor(el) {
            this.el = el;
            this.origRect = internal.computeRect(el);
            // will work fine for divs that have overflow:hidden
            this.scrollCaches = internal.getClippingParents(el).map((scrollEl) => new ElementScrollGeomCache(scrollEl, true));
        }
        destroy() {
            for (let scrollCache of this.scrollCaches) {
                scrollCache.destroy();
            }
        }
        computeLeft() {
            let left = this.origRect.left;
            for (let scrollCache of this.scrollCaches) {
                left += scrollCache.origScrollLeft - scrollCache.getScrollLeft();
            }
            return left;
        }
        computeTop() {
            let top = this.origRect.top;
            for (let scrollCache of this.scrollCaches) {
                top += scrollCache.origScrollTop - scrollCache.getScrollTop();
            }
            return top;
        }
        isWithinClipping(pageX, pageY) {
            let point = { left: pageX, top: pageY };
            for (let scrollCache of this.scrollCaches) {
                if (!isIgnoredClipping(scrollCache.getEventTarget()) &&
                    !internal.pointInsideRect(point, scrollCache.clientRect)) {
                    return false;
                }
            }
            return true;
        }
    }
    // certain clipping containers should never constrain interactions, like <html> and <body>
    // https://github.com/fullcalendar/fullcalendar/issues/3615
    function isIgnoredClipping(node) {
        let tagName = node.tagName;
        return tagName === 'HTML' || tagName === 'BODY';
    }

    /*
    Tracks movement over multiple droppable areas (aka "hits")
    that exist in one or more DateComponents.
    Relies on an existing draggable.

    emits:
    - pointerdown
    - dragstart
    - hitchange - fires initially, even if not over a hit
    - pointerup
    - (hitchange - again, to null, if ended over a hit)
    - dragend
    */
    class HitDragging {
        constructor(dragging, droppableStore) {
            // options that can be set by caller
            this.useSubjectCenter = false;
            this.requireInitial = true; // if doesn't start out on a hit, won't emit any events
            this.disablePointCheck = false;
            this.initialHit = null;
            this.movingHit = null;
            this.finalHit = null; // won't ever be populated if shouldIgnoreMove
            this.handlePointerDown = (ev) => {
                let { dragging } = this;
                this.initialHit = null;
                this.movingHit = null;
                this.finalHit = null;
                this.prepareHits();
                this.processFirstCoord(ev);
                if (this.initialHit || !this.requireInitial) {
                    dragging.setIgnoreMove(false);
                    // TODO: fire this before computing processFirstCoord, so listeners can cancel. this gets fired by almost every handler :(
                    this.emitter.trigger('pointerdown', ev);
                }
                else {
                    dragging.setIgnoreMove(true);
                }
            };
            this.handleDragStart = (ev) => {
                this.emitter.trigger('dragstart', ev);
                this.handleMove(ev, true); // force = fire even if initially null
            };
            this.handleDragMove = (ev) => {
                this.emitter.trigger('dragmove', ev);
                this.handleMove(ev);
            };
            this.handlePointerUp = (ev) => {
                this.releaseHits();
                this.emitter.trigger('pointerup', ev);
            };
            this.handleDragEnd = (ev) => {
                if (this.movingHit) {
                    this.emitter.trigger('hitupdate', null, true, ev);
                }
                this.finalHit = this.movingHit;
                this.movingHit = null;
                this.emitter.trigger('dragend', ev);
            };
            this.droppableStore = droppableStore;
            dragging.emitter.on('pointerdown', this.handlePointerDown);
            dragging.emitter.on('dragstart', this.handleDragStart);
            dragging.emitter.on('dragmove', this.handleDragMove);
            dragging.emitter.on('pointerup', this.handlePointerUp);
            dragging.emitter.on('dragend', this.handleDragEnd);
            this.dragging = dragging;
            this.emitter = new internal.Emitter();
        }
        // sets initialHit
        // sets coordAdjust
        processFirstCoord(ev) {
            let origPoint = { left: ev.pageX, top: ev.pageY };
            let adjustedPoint = origPoint;
            let subjectEl = ev.subjectEl;
            let subjectRect;
            if (subjectEl instanceof HTMLElement) { // i.e. not a Document/ShadowRoot
                subjectRect = internal.computeRect(subjectEl);
                adjustedPoint = internal.constrainPoint(adjustedPoint, subjectRect);
            }
            let initialHit = this.initialHit = this.queryHitForOffset(adjustedPoint.left, adjustedPoint.top);
            if (initialHit) {
                if (this.useSubjectCenter && subjectRect) {
                    let slicedSubjectRect = internal.intersectRects(subjectRect, initialHit.rect);
                    if (slicedSubjectRect) {
                        adjustedPoint = internal.getRectCenter(slicedSubjectRect);
                    }
                }
                this.coordAdjust = internal.diffPoints(adjustedPoint, origPoint);
            }
            else {
                this.coordAdjust = { left: 0, top: 0 };
            }
        }
        handleMove(ev, forceHandle) {
            let hit = this.queryHitForOffset(ev.pageX + this.coordAdjust.left, ev.pageY + this.coordAdjust.top);
            if (forceHandle || !isHitsEqual(this.movingHit, hit)) {
                this.movingHit = hit;
                this.emitter.trigger('hitupdate', hit, false, ev);
            }
        }
        prepareHits() {
            this.offsetTrackers = internal.mapHash(this.droppableStore, (interactionSettings) => {
                interactionSettings.component.prepareHits();
                return new OffsetTracker(interactionSettings.el);
            });
        }
        releaseHits() {
            let { offsetTrackers } = this;
            for (let id in offsetTrackers) {
                offsetTrackers[id].destroy();
            }
            this.offsetTrackers = {};
        }
        queryHitForOffset(offsetLeft, offsetTop) {
            let { droppableStore, offsetTrackers } = this;
            let bestHit = null;
            for (let id in droppableStore) {
                let component = droppableStore[id].component;
                let offsetTracker = offsetTrackers[id];
                if (offsetTracker && // wasn't destroyed mid-drag
                    offsetTracker.isWithinClipping(offsetLeft, offsetTop)) {
                    let originLeft = offsetTracker.computeLeft();
                    let originTop = offsetTracker.computeTop();
                    let positionLeft = offsetLeft - originLeft;
                    let positionTop = offsetTop - originTop;
                    let { origRect } = offsetTracker;
                    let width = origRect.right - origRect.left;
                    let height = origRect.bottom - origRect.top;
                    if (
                    // must be within the element's bounds
                    positionLeft >= 0 && positionLeft < width &&
                        positionTop >= 0 && positionTop < height) {
                        let hit = component.queryHit(positionLeft, positionTop, width, height);
                        if (hit && (
                        // make sure the hit is within activeRange, meaning it's not a dead cell
                        internal.rangeContainsRange(hit.dateProfile.activeRange, hit.dateSpan.range)) &&
                            // Ensure the component we are querying for the hit is accessibly my the pointer
                            // Prevents obscured calendars (ex: under a modal dialog) from accepting hit
                            // https://github.com/fullcalendar/fullcalendar/issues/5026
                            (this.disablePointCheck ||
                                offsetTracker.el.contains(offsetTracker.el.getRootNode().elementFromPoint(
                                // add-back origins to get coordinate relative to top-left of window viewport
                                positionLeft + originLeft - window.scrollX, positionTop + originTop - window.scrollY))) &&
                            (!bestHit || hit.layer > bestHit.layer)) {
                            hit.componentId = id;
                            hit.context = component.context;
                            // TODO: better way to re-orient rectangle
                            hit.rect.left += originLeft;
                            hit.rect.right += originLeft;
                            hit.rect.top += originTop;
                            hit.rect.bottom += originTop;
                            bestHit = hit;
                        }
                    }
                }
            }
            return bestHit;
        }
    }
    function isHitsEqual(hit0, hit1) {
        if (!hit0 && !hit1) {
            return true;
        }
        if (Boolean(hit0) !== Boolean(hit1)) {
            return false;
        }
        return internal.isDateSpansEqual(hit0.dateSpan, hit1.dateSpan);
    }

    function buildDatePointApiWithContext(dateSpan, context) {
        let props = {};
        for (let transform of context.pluginHooks.datePointTransforms) {
            Object.assign(props, transform(dateSpan, context));
        }
        Object.assign(props, buildDatePointApi(dateSpan, context.dateEnv));
        return props;
    }
    function buildDatePointApi(span, dateEnv) {
        return {
            date: dateEnv.toDate(span.range.start),
            dateStr: dateEnv.formatIso(span.range.start, { omitTime: span.allDay }),
            allDay: span.allDay,
        };
    }

    /*
    Monitors when the user clicks on a specific date/time of a component.
    A pointerdown+pointerup on the same "hit" constitutes a click.
    */
    class DateClicking extends internal.Interaction {
        constructor(settings) {
            super(settings);
            this.handlePointerDown = (pev) => {
                let { dragging } = this;
                let downEl = pev.origEvent.target;
                // do this in pointerdown (not dragend) because DOM might be mutated by the time dragend is fired
                dragging.setIgnoreMove(!this.component.isValidDateDownEl(downEl));
            };
            // won't even fire if moving was ignored
            this.handleDragEnd = (ev) => {
                let { component } = this;
                let { pointer } = this.dragging;
                if (!pointer.wasTouchScroll) {
                    let { initialHit, finalHit } = this.hitDragging;
                    if (initialHit && finalHit && isHitsEqual(initialHit, finalHit)) {
                        let { context } = component;
                        let arg = Object.assign(Object.assign({}, buildDatePointApiWithContext(initialHit.dateSpan, context)), { dayEl: initialHit.dayEl, jsEvent: ev.origEvent, view: context.viewApi || context.calendarApi.view });
                        context.emitter.trigger('dateClick', arg);
                    }
                }
            };
            // we DO want to watch pointer moves because otherwise finalHit won't get populated
            this.dragging = new FeaturefulElementDragging(settings.el);
            this.dragging.autoScroller.isEnabled = false;
            let hitDragging = this.hitDragging = new HitDragging(this.dragging, internal.interactionSettingsToStore(settings));
            hitDragging.emitter.on('pointerdown', this.handlePointerDown);
            hitDragging.emitter.on('dragend', this.handleDragEnd);
        }
        destroy() {
            this.dragging.destroy();
        }
    }

    /*
    Tracks when the user selects a portion of time of a component,
    constituted by a drag over date cells, with a possible delay at the beginning of the drag.
    */
    class DateSelecting extends internal.Interaction {
        constructor(settings) {
            super(settings);
            this.dragSelection = null;
            this.handlePointerDown = (ev) => {
                let { component, dragging } = this;
                let { options } = component.context;
                let canSelect = options.selectable &&
                    component.isValidDateDownEl(ev.origEvent.target);
                // don't bother to watch expensive moves if component won't do selection
                dragging.setIgnoreMove(!canSelect);
                // if touch, require user to hold down
                dragging.delay = ev.isTouch ? getComponentTouchDelay$1(component) : null;
            };
            this.handleDragStart = (ev) => {
                this.component.context.calendarApi.unselect(ev); // unselect previous selections
            };
            this.handleHitUpdate = (hit, isFinal) => {
                let { context } = this.component;
                let dragSelection = null;
                let isInvalid = false;
                if (hit) {
                    let initialHit = this.hitDragging.initialHit;
                    let disallowed = hit.componentId === initialHit.componentId
                        && this.isHitComboAllowed
                        && !this.isHitComboAllowed(initialHit, hit);
                    if (!disallowed) {
                        dragSelection = joinHitsIntoSelection(initialHit, hit, context.pluginHooks.dateSelectionTransformers);
                    }
                    if (!dragSelection || !internal.isDateSelectionValid(dragSelection, hit.dateProfile, context)) {
                        isInvalid = true;
                        dragSelection = null;
                    }
                }
                if (dragSelection) {
                    context.dispatch({ type: 'SELECT_DATES', selection: dragSelection });
                }
                else if (!isFinal) { // only unselect if moved away while dragging
                    context.dispatch({ type: 'UNSELECT_DATES' });
                }
                if (!isInvalid) {
                    internal.enableCursor();
                }
                else {
                    internal.disableCursor();
                }
                if (!isFinal) {
                    this.dragSelection = dragSelection; // only clear if moved away from all hits while dragging
                }
            };
            this.handlePointerUp = (pev) => {
                if (this.dragSelection) {
                    // selection is already rendered, so just need to report selection
                    internal.triggerDateSelect(this.dragSelection, pev, this.component.context);
                    this.dragSelection = null;
                }
            };
            let { component } = settings;
            let { options } = component.context;
            let dragging = this.dragging = new FeaturefulElementDragging(settings.el);
            dragging.touchScrollAllowed = false;
            dragging.minDistance = options.selectMinDistance || 0;
            dragging.autoScroller.isEnabled = options.dragScroll;
            let hitDragging = this.hitDragging = new HitDragging(this.dragging, internal.interactionSettingsToStore(settings));
            hitDragging.emitter.on('pointerdown', this.handlePointerDown);
            hitDragging.emitter.on('dragstart', this.handleDragStart);
            hitDragging.emitter.on('hitupdate', this.handleHitUpdate);
            hitDragging.emitter.on('pointerup', this.handlePointerUp);
        }
        destroy() {
            this.dragging.destroy();
        }
    }
    function getComponentTouchDelay$1(component) {
        let { options } = component.context;
        let delay = options.selectLongPressDelay;
        if (delay == null) {
            delay = options.longPressDelay;
        }
        return delay;
    }
    function joinHitsIntoSelection(hit0, hit1, dateSelectionTransformers) {
        let dateSpan0 = hit0.dateSpan;
        let dateSpan1 = hit1.dateSpan;
        let ms = [
            dateSpan0.range.start,
            dateSpan0.range.end,
            dateSpan1.range.start,
            dateSpan1.range.end,
        ];
        ms.sort(internal.compareNumbers);
        let props = {};
        for (let transformer of dateSelectionTransformers) {
            let res = transformer(hit0, hit1);
            if (res === false) {
                return null;
            }
            if (res) {
                Object.assign(props, res);
            }
        }
        props.range = { start: ms[0], end: ms[3] };
        props.allDay = dateSpan0.allDay;
        return props;
    }

    class EventDragging extends internal.Interaction {
        constructor(settings) {
            super(settings);
            // internal state
            this.subjectEl = null;
            this.subjectSeg = null; // the seg being selected/dragged
            this.isDragging = false;
            this.eventRange = null;
            this.relevantEvents = null; // the events being dragged
            this.receivingContext = null;
            this.validMutation = null;
            this.mutatedRelevantEvents = null;
            this.handlePointerDown = (ev) => {
                let origTarget = ev.origEvent.target;
                let { component, dragging } = this;
                let { mirror } = dragging;
                let { options } = component.context;
                let initialContext = component.context;
                this.subjectEl = ev.subjectEl;
                let subjectSeg = this.subjectSeg = internal.getElSeg(ev.subjectEl);
                let eventRange = this.eventRange = subjectSeg.eventRange;
                let eventInstanceId = eventRange.instance.instanceId;
                this.relevantEvents = internal.getRelevantEvents(initialContext.getCurrentData().eventStore, eventInstanceId);
                dragging.minDistance = ev.isTouch ? 0 : options.eventDragMinDistance;
                dragging.delay =
                    // only do a touch delay if touch and this event hasn't been selected yet
                    (ev.isTouch && eventInstanceId !== component.props.eventSelection) ?
                        getComponentTouchDelay(component) :
                        null;
                if (options.fixedMirrorParent) {
                    mirror.parentNode = options.fixedMirrorParent;
                }
                else {
                    mirror.parentNode = internal.elementClosest(origTarget, '.fc');
                }
                mirror.revertDuration = options.dragRevertDuration;
                let isValid = component.isValidSegDownEl(origTarget) &&
                    !internal.elementClosest(origTarget, '.fc-event-resizer'); // NOT on a resizer
                dragging.setIgnoreMove(!isValid);
                // disable dragging for elements that are resizable (ie, selectable)
                // but are not draggable
                this.isDragging = isValid &&
                    ev.subjectEl.classList.contains('fc-event-draggable');
            };
            this.handleDragStart = (ev) => {
                let initialContext = this.component.context;
                let eventRange = this.eventRange;
                let eventInstanceId = eventRange.instance.instanceId;
                if (ev.isTouch) {
                    // need to select a different event?
                    if (eventInstanceId !== this.component.props.eventSelection) {
                        initialContext.dispatch({ type: 'SELECT_EVENT', eventInstanceId });
                    }
                }
                else {
                    // if now using mouse, but was previous touch interaction, clear selected event
                    initialContext.dispatch({ type: 'UNSELECT_EVENT' });
                }
                if (this.isDragging) {
                    initialContext.calendarApi.unselect(ev); // unselect *date* selection
                    initialContext.emitter.trigger('eventDragStart', {
                        el: this.subjectEl,
                        event: new internal.EventImpl(initialContext, eventRange.def, eventRange.instance),
                        jsEvent: ev.origEvent,
                        view: initialContext.viewApi,
                    });
                }
            };
            this.handleHitUpdate = (hit, isFinal) => {
                if (!this.isDragging) {
                    return;
                }
                let relevantEvents = this.relevantEvents;
                let initialHit = this.hitDragging.initialHit;
                let initialContext = this.component.context;
                // states based on new hit
                let receivingContext = null;
                let mutation = null;
                let mutatedRelevantEvents = null;
                let isInvalid = false;
                let interaction = {
                    affectedEvents: relevantEvents,
                    mutatedEvents: internal.createEmptyEventStore(),
                    isEvent: true,
                };
                if (hit) {
                    receivingContext = hit.context;
                    let receivingOptions = receivingContext.options;
                    if (initialContext === receivingContext ||
                        (receivingOptions.editable && receivingOptions.droppable)) {
                        mutation = computeEventMutation(initialHit, hit, this.eventRange.instance.range.start, receivingContext.getCurrentData().pluginHooks.eventDragMutationMassagers);
                        if (mutation) {
                            mutatedRelevantEvents = internal.applyMutationToEventStore(relevantEvents, receivingContext.getCurrentData().eventUiBases, mutation, receivingContext);
                            interaction.mutatedEvents = mutatedRelevantEvents;
                            if (!internal.isInteractionValid(interaction, hit.dateProfile, receivingContext)) {
                                isInvalid = true;
                                mutation = null;
                                mutatedRelevantEvents = null;
                                interaction.mutatedEvents = internal.createEmptyEventStore();
                            }
                        }
                    }
                    else {
                        receivingContext = null;
                    }
                }
                this.displayDrag(receivingContext, interaction);
                if (!isInvalid) {
                    internal.enableCursor();
                }
                else {
                    internal.disableCursor();
                }
                if (!isFinal) {
                    if (initialContext === receivingContext && // TODO: write test for this
                        isHitsEqual(initialHit, hit)) {
                        mutation = null;
                    }
                    this.dragging.setMirrorNeedsRevert(!mutation);
                    // render the mirror if no already-rendered mirror
                    // TODO: wish we could somehow wait for dispatch to guarantee render
                    this.dragging.setMirrorIsVisible(!hit || !this.subjectEl.getRootNode().querySelector('.fc-event-mirror'));
                    // assign states based on new hit
                    this.receivingContext = receivingContext;
                    this.validMutation = mutation;
                    this.mutatedRelevantEvents = mutatedRelevantEvents;
                }
            };
            this.handlePointerUp = () => {
                if (!this.isDragging) {
                    this.cleanup(); // because handleDragEnd won't fire
                }
            };
            this.handleDragEnd = (ev) => {
                if (this.isDragging) {
                    let initialContext = this.component.context;
                    let initialView = initialContext.viewApi;
                    let { receivingContext, validMutation } = this;
                    let eventDef = this.eventRange.def;
                    let eventInstance = this.eventRange.instance;
                    let eventApi = new internal.EventImpl(initialContext, eventDef, eventInstance);
                    let relevantEvents = this.relevantEvents;
                    let mutatedRelevantEvents = this.mutatedRelevantEvents;
                    let { finalHit } = this.hitDragging;
                    this.clearDrag(); // must happen after revert animation
                    initialContext.emitter.trigger('eventDragStop', {
                        el: this.subjectEl,
                        event: eventApi,
                        jsEvent: ev.origEvent,
                        view: initialView,
                    });
                    if (validMutation) {
                        // dropped within same calendar
                        if (receivingContext === initialContext) {
                            let updatedEventApi = new internal.EventImpl(initialContext, mutatedRelevantEvents.defs[eventDef.defId], eventInstance ? mutatedRelevantEvents.instances[eventInstance.instanceId] : null);
                            initialContext.dispatch({
                                type: 'MERGE_EVENTS',
                                eventStore: mutatedRelevantEvents,
                            });
                            let eventChangeArg = {
                                oldEvent: eventApi,
                                event: updatedEventApi,
                                relatedEvents: internal.buildEventApis(mutatedRelevantEvents, initialContext, eventInstance),
                                revert() {
                                    initialContext.dispatch({
                                        type: 'MERGE_EVENTS',
                                        eventStore: relevantEvents, // the pre-change data
                                    });
                                },
                            };
                            let transformed = {};
                            for (let transformer of initialContext.getCurrentData().pluginHooks.eventDropTransformers) {
                                Object.assign(transformed, transformer(validMutation, initialContext));
                            }
                            initialContext.emitter.trigger('eventDrop', Object.assign(Object.assign(Object.assign({}, eventChangeArg), transformed), { el: ev.subjectEl, delta: validMutation.datesDelta, jsEvent: ev.origEvent, view: initialView }));
                            initialContext.emitter.trigger('eventChange', eventChangeArg);
                            // dropped in different calendar
                        }
                        else if (receivingContext) {
                            let eventRemoveArg = {
                                event: eventApi,
                                relatedEvents: internal.buildEventApis(relevantEvents, initialContext, eventInstance),
                                revert() {
                                    initialContext.dispatch({
                                        type: 'MERGE_EVENTS',
                                        eventStore: relevantEvents,
                                    });
                                },
                            };
                            initialContext.emitter.trigger('eventLeave', Object.assign(Object.assign({}, eventRemoveArg), { draggedEl: ev.subjectEl, view: initialView }));
                            initialContext.dispatch({
                                type: 'REMOVE_EVENTS',
                                eventStore: relevantEvents,
                            });
                            initialContext.emitter.trigger('eventRemove', eventRemoveArg);
                            let addedEventDef = mutatedRelevantEvents.defs[eventDef.defId];
                            let addedEventInstance = mutatedRelevantEvents.instances[eventInstance.instanceId];
                            let addedEventApi = new internal.EventImpl(receivingContext, addedEventDef, addedEventInstance);
                            receivingContext.dispatch({
                                type: 'MERGE_EVENTS',
                                eventStore: mutatedRelevantEvents,
                            });
                            let eventAddArg = {
                                event: addedEventApi,
                                relatedEvents: internal.buildEventApis(mutatedRelevantEvents, receivingContext, addedEventInstance),
                                revert() {
                                    receivingContext.dispatch({
                                        type: 'REMOVE_EVENTS',
                                        eventStore: mutatedRelevantEvents,
                                    });
                                },
                            };
                            receivingContext.emitter.trigger('eventAdd', eventAddArg);
                            if (ev.isTouch) {
                                receivingContext.dispatch({
                                    type: 'SELECT_EVENT',
                                    eventInstanceId: eventInstance.instanceId,
                                });
                            }
                            receivingContext.emitter.trigger('drop', Object.assign(Object.assign({}, buildDatePointApiWithContext(finalHit.dateSpan, receivingContext)), { draggedEl: ev.subjectEl, jsEvent: ev.origEvent, view: finalHit.context.viewApi }));
                            receivingContext.emitter.trigger('eventReceive', Object.assign(Object.assign({}, eventAddArg), { draggedEl: ev.subjectEl, view: finalHit.context.viewApi }));
                        }
                    }
                    else {
                        initialContext.emitter.trigger('_noEventDrop');
                    }
                }
                this.cleanup();
            };
            let { component } = this;
            let { options } = component.context;
            let dragging = this.dragging = new FeaturefulElementDragging(settings.el);
            dragging.pointer.selector = EventDragging.SELECTOR;
            dragging.touchScrollAllowed = false;
            dragging.autoScroller.isEnabled = options.dragScroll;
            let hitDragging = this.hitDragging = new HitDragging(this.dragging, internal.interactionSettingsStore);
            hitDragging.useSubjectCenter = settings.useEventCenter;
            hitDragging.emitter.on('pointerdown', this.handlePointerDown);
            hitDragging.emitter.on('dragstart', this.handleDragStart);
            hitDragging.emitter.on('hitupdate', this.handleHitUpdate);
            hitDragging.emitter.on('pointerup', this.handlePointerUp);
            hitDragging.emitter.on('dragend', this.handleDragEnd);
        }
        destroy() {
            this.dragging.destroy();
        }
        // render a drag state on the next receivingCalendar
        displayDrag(nextContext, state) {
            let initialContext = this.component.context;
            let prevContext = this.receivingContext;
            // does the previous calendar need to be cleared?
            if (prevContext && prevContext !== nextContext) {
                // does the initial calendar need to be cleared?
                // if so, don't clear all the way. we still need to to hide the affectedEvents
                if (prevContext === initialContext) {
                    prevContext.dispatch({
                        type: 'SET_EVENT_DRAG',
                        state: {
                            affectedEvents: state.affectedEvents,
                            mutatedEvents: internal.createEmptyEventStore(),
                            isEvent: true,
                        },
                    });
                    // completely clear the old calendar if it wasn't the initial
                }
                else {
                    prevContext.dispatch({ type: 'UNSET_EVENT_DRAG' });
                }
            }
            if (nextContext) {
                nextContext.dispatch({ type: 'SET_EVENT_DRAG', state });
            }
        }
        clearDrag() {
            let initialCalendar = this.component.context;
            let { receivingContext } = this;
            if (receivingContext) {
                receivingContext.dispatch({ type: 'UNSET_EVENT_DRAG' });
            }
            // the initial calendar might have an dummy drag state from displayDrag
            if (initialCalendar !== receivingContext) {
                initialCalendar.dispatch({ type: 'UNSET_EVENT_DRAG' });
            }
        }
        cleanup() {
            this.subjectSeg = null;
            this.isDragging = false;
            this.eventRange = null;
            this.relevantEvents = null;
            this.receivingContext = null;
            this.validMutation = null;
            this.mutatedRelevantEvents = null;
        }
    }
    // TODO: test this in IE11
    // QUESTION: why do we need it on the resizable???
    EventDragging.SELECTOR = '.fc-event-draggable, .fc-event-resizable';
    function computeEventMutation(hit0, hit1, eventInstanceStart, massagers) {
        let dateSpan0 = hit0.dateSpan;
        let dateSpan1 = hit1.dateSpan;
        let date0 = dateSpan0.range.start;
        let date1 = dateSpan1.range.start;
        let standardProps = {};
        if (dateSpan0.allDay !== dateSpan1.allDay) {
            standardProps.allDay = dateSpan1.allDay;
            standardProps.hasEnd = hit1.context.options.allDayMaintainDuration;
            if (dateSpan1.allDay) {
                // means date1 is already start-of-day,
                // but date0 needs to be converted
                date0 = internal.startOfDay(eventInstanceStart);
            }
            else {
                // Moving from allDate->timed
                // Doesn't matter where on the event the drag began, mutate the event's start-date to date1
                date0 = eventInstanceStart;
            }
        }
        let delta = internal.diffDates(date0, date1, hit0.context.dateEnv, hit0.componentId === hit1.componentId ?
            hit0.largeUnit :
            null);
        if (delta.milliseconds) { // has hours/minutes/seconds
            standardProps.allDay = false;
        }
        let mutation = {
            datesDelta: delta,
            standardProps,
        };
        for (let massager of massagers) {
            massager(mutation, hit0, hit1);
        }
        return mutation;
    }
    function getComponentTouchDelay(component) {
        let { options } = component.context;
        let delay = options.eventLongPressDelay;
        if (delay == null) {
            delay = options.longPressDelay;
        }
        return delay;
    }

    class EventResizing extends internal.Interaction {
        constructor(settings) {
            super(settings);
            // internal state
            this.draggingSegEl = null;
            this.draggingSeg = null; // TODO: rename to resizingSeg? subjectSeg?
            this.eventRange = null;
            this.relevantEvents = null;
            this.validMutation = null;
            this.mutatedRelevantEvents = null;
            this.handlePointerDown = (ev) => {
                let { component } = this;
                let segEl = this.querySegEl(ev);
                let seg = internal.getElSeg(segEl);
                let eventRange = this.eventRange = seg.eventRange;
                this.dragging.minDistance = component.context.options.eventDragMinDistance;
                // if touch, need to be working with a selected event
                this.dragging.setIgnoreMove(!this.component.isValidSegDownEl(ev.origEvent.target) ||
                    (ev.isTouch && this.component.props.eventSelection !== eventRange.instance.instanceId));
            };
            this.handleDragStart = (ev) => {
                let { context } = this.component;
                let eventRange = this.eventRange;
                this.relevantEvents = internal.getRelevantEvents(context.getCurrentData().eventStore, this.eventRange.instance.instanceId);
                let segEl = this.querySegEl(ev);
                this.draggingSegEl = segEl;
                this.draggingSeg = internal.getElSeg(segEl);
                context.calendarApi.unselect();
                context.emitter.trigger('eventResizeStart', {
                    el: segEl,
                    event: new internal.EventImpl(context, eventRange.def, eventRange.instance),
                    jsEvent: ev.origEvent,
                    view: context.viewApi,
                });
            };
            this.handleHitUpdate = (hit, isFinal, ev) => {
                let { context } = this.component;
                let relevantEvents = this.relevantEvents;
                let initialHit = this.hitDragging.initialHit;
                let eventInstance = this.eventRange.instance;
                let mutation = null;
                let mutatedRelevantEvents = null;
                let isInvalid = false;
                let interaction = {
                    affectedEvents: relevantEvents,
                    mutatedEvents: internal.createEmptyEventStore(),
                    isEvent: true,
                };
                if (hit) {
                    let disallowed = hit.componentId === initialHit.componentId
                        && this.isHitComboAllowed
                        && !this.isHitComboAllowed(initialHit, hit);
                    if (!disallowed) {
                        mutation = computeMutation(initialHit, hit, ev.subjectEl.classList.contains('fc-event-resizer-start'), eventInstance.range);
                    }
                }
                if (mutation) {
                    mutatedRelevantEvents = internal.applyMutationToEventStore(relevantEvents, context.getCurrentData().eventUiBases, mutation, context);
                    interaction.mutatedEvents = mutatedRelevantEvents;
                    if (!internal.isInteractionValid(interaction, hit.dateProfile, context)) {
                        isInvalid = true;
                        mutation = null;
                        mutatedRelevantEvents = null;
                        interaction.mutatedEvents = null;
                    }
                }
                if (mutatedRelevantEvents) {
                    context.dispatch({
                        type: 'SET_EVENT_RESIZE',
                        state: interaction,
                    });
                }
                else {
                    context.dispatch({ type: 'UNSET_EVENT_RESIZE' });
                }
                if (!isInvalid) {
                    internal.enableCursor();
                }
                else {
                    internal.disableCursor();
                }
                if (!isFinal) {
                    if (mutation && isHitsEqual(initialHit, hit)) {
                        mutation = null;
                    }
                    this.validMutation = mutation;
                    this.mutatedRelevantEvents = mutatedRelevantEvents;
                }
            };
            this.handleDragEnd = (ev) => {
                let { context } = this.component;
                let eventDef = this.eventRange.def;
                let eventInstance = this.eventRange.instance;
                let eventApi = new internal.EventImpl(context, eventDef, eventInstance);
                let relevantEvents = this.relevantEvents;
                let mutatedRelevantEvents = this.mutatedRelevantEvents;
                context.emitter.trigger('eventResizeStop', {
                    el: this.draggingSegEl,
                    event: eventApi,
                    jsEvent: ev.origEvent,
                    view: context.viewApi,
                });
                if (this.validMutation) {
                    let updatedEventApi = new internal.EventImpl(context, mutatedRelevantEvents.defs[eventDef.defId], eventInstance ? mutatedRelevantEvents.instances[eventInstance.instanceId] : null);
                    context.dispatch({
                        type: 'MERGE_EVENTS',
                        eventStore: mutatedRelevantEvents,
                    });
                    let eventChangeArg = {
                        oldEvent: eventApi,
                        event: updatedEventApi,
                        relatedEvents: internal.buildEventApis(mutatedRelevantEvents, context, eventInstance),
                        revert() {
                            context.dispatch({
                                type: 'MERGE_EVENTS',
                                eventStore: relevantEvents, // the pre-change events
                            });
                        },
                    };
                    context.emitter.trigger('eventResize', Object.assign(Object.assign({}, eventChangeArg), { el: this.draggingSegEl, startDelta: this.validMutation.startDelta || internal.createDuration(0), endDelta: this.validMutation.endDelta || internal.createDuration(0), jsEvent: ev.origEvent, view: context.viewApi }));
                    context.emitter.trigger('eventChange', eventChangeArg);
                }
                else {
                    context.emitter.trigger('_noEventResize');
                }
                // reset all internal state
                this.draggingSeg = null;
                this.relevantEvents = null;
                this.validMutation = null;
                // okay to keep eventInstance around. useful to set it in handlePointerDown
            };
            let { component } = settings;
            let dragging = this.dragging = new FeaturefulElementDragging(settings.el);
            dragging.pointer.selector = '.fc-event-resizer';
            dragging.touchScrollAllowed = false;
            dragging.autoScroller.isEnabled = component.context.options.dragScroll;
            let hitDragging = this.hitDragging = new HitDragging(this.dragging, internal.interactionSettingsToStore(settings));
            hitDragging.emitter.on('pointerdown', this.handlePointerDown);
            hitDragging.emitter.on('dragstart', this.handleDragStart);
            hitDragging.emitter.on('hitupdate', this.handleHitUpdate);
            hitDragging.emitter.on('dragend', this.handleDragEnd);
        }
        destroy() {
            this.dragging.destroy();
        }
        querySegEl(ev) {
            return internal.elementClosest(ev.subjectEl, '.fc-event');
        }
    }
    function computeMutation(hit0, hit1, isFromStart, instanceRange) {
        let dateEnv = hit0.context.dateEnv;
        let date0 = hit0.dateSpan.range.start;
        let date1 = hit1.dateSpan.range.start;
        let delta = internal.diffDates(date0, date1, dateEnv, hit0.largeUnit);
        if (isFromStart) {
            if (dateEnv.add(instanceRange.start, delta) < instanceRange.end) {
                return { startDelta: delta };
            }
        }
        else if (dateEnv.add(instanceRange.end, delta) > instanceRange.start) {
            return { endDelta: delta };
        }
        return null;
    }

    class UnselectAuto {
        constructor(context) {
            this.context = context;
            this.isRecentPointerDateSelect = false; // wish we could use a selector to detect date selection, but uses hit system
            this.matchesCancel = false;
            this.matchesEvent = false;
            this.onSelect = (selectInfo) => {
                if (selectInfo.jsEvent) {
                    this.isRecentPointerDateSelect = true;
                }
            };
            this.onDocumentPointerDown = (pev) => {
                let unselectCancel = this.context.options.unselectCancel;
                let downEl = internal.getEventTargetViaRoot(pev.origEvent);
                this.matchesCancel = !!internal.elementClosest(downEl, unselectCancel);
                this.matchesEvent = !!internal.elementClosest(downEl, EventDragging.SELECTOR); // interaction started on an event?
            };
            this.onDocumentPointerUp = (pev) => {
                let { context } = this;
                let { documentPointer } = this;
                let calendarState = context.getCurrentData();
                // touch-scrolling should never unfocus any type of selection
                if (!documentPointer.wasTouchScroll) {
                    if (calendarState.dateSelection && // an existing date selection?
                        !this.isRecentPointerDateSelect // a new pointer-initiated date selection since last onDocumentPointerUp?
                    ) {
                        let unselectAuto = context.options.unselectAuto;
                        if (unselectAuto && (!unselectAuto || !this.matchesCancel)) {
                            context.calendarApi.unselect(pev);
                        }
                    }
                    if (calendarState.eventSelection && // an existing event selected?
                        !this.matchesEvent // interaction DIDN'T start on an event
                    ) {
                        context.dispatch({ type: 'UNSELECT_EVENT' });
                    }
                }
                this.isRecentPointerDateSelect = false;
            };
            let documentPointer = this.documentPointer = new PointerDragging(document);
            documentPointer.shouldIgnoreMove = true;
            documentPointer.shouldWatchScroll = false;
            documentPointer.emitter.on('pointerdown', this.onDocumentPointerDown);
            documentPointer.emitter.on('pointerup', this.onDocumentPointerUp);
            /*
            TODO: better way to know about whether there was a selection with the pointer
            */
            context.emitter.on('select', this.onSelect);
        }
        destroy() {
            this.context.emitter.off('select', this.onSelect);
            this.documentPointer.destroy();
        }
    }

    const OPTION_REFINERS = {
        fixedMirrorParent: internal.identity,
    };
    const LISTENER_REFINERS = {
        dateClick: internal.identity,
        eventDragStart: internal.identity,
        eventDragStop: internal.identity,
        eventDrop: internal.identity,
        eventResizeStart: internal.identity,
        eventResizeStop: internal.identity,
        eventResize: internal.identity,
        drop: internal.identity,
        eventReceive: internal.identity,
        eventLeave: internal.identity,
    };

    /*
    Given an already instantiated draggable object for one-or-more elements,
    Interprets any dragging as an attempt to drag an events that lives outside
    of a calendar onto a calendar.
    */
    class ExternalElementDragging {
        constructor(dragging, suppliedDragMeta) {
            this.receivingContext = null;
            this.droppableEvent = null; // will exist for all drags, even if create:false
            this.suppliedDragMeta = null;
            this.dragMeta = null;
            this.handleDragStart = (ev) => {
                this.dragMeta = this.buildDragMeta(ev.subjectEl);
            };
            this.handleHitUpdate = (hit, isFinal, ev) => {
                let { dragging } = this.hitDragging;
                let receivingContext = null;
                let droppableEvent = null;
                let isInvalid = false;
                let interaction = {
                    affectedEvents: internal.createEmptyEventStore(),
                    mutatedEvents: internal.createEmptyEventStore(),
                    isEvent: this.dragMeta.create,
                };
                if (hit) {
                    receivingContext = hit.context;
                    if (this.canDropElOnCalendar(ev.subjectEl, receivingContext)) {
                        droppableEvent = computeEventForDateSpan(hit.dateSpan, this.dragMeta, receivingContext);
                        interaction.mutatedEvents = internal.eventTupleToStore(droppableEvent);
                        isInvalid = !internal.isInteractionValid(interaction, hit.dateProfile, receivingContext);
                        if (isInvalid) {
                            interaction.mutatedEvents = internal.createEmptyEventStore();
                            droppableEvent = null;
                        }
                    }
                }
                this.displayDrag(receivingContext, interaction);
                // show mirror if no already-rendered mirror element OR if we are shutting down the mirror (?)
                // TODO: wish we could somehow wait for dispatch to guarantee render
                dragging.setMirrorIsVisible(isFinal || !droppableEvent || !document.querySelector('.fc-event-mirror'));
                if (!isInvalid) {
                    internal.enableCursor();
                }
                else {
                    internal.disableCursor();
                }
                if (!isFinal) {
                    dragging.setMirrorNeedsRevert(!droppableEvent);
                    this.receivingContext = receivingContext;
                    this.droppableEvent = droppableEvent;
                }
            };
            this.handleDragEnd = (pev) => {
                let { receivingContext, droppableEvent } = this;
                this.clearDrag();
                if (receivingContext && droppableEvent) {
                    let finalHit = this.hitDragging.finalHit;
                    let finalView = finalHit.context.viewApi;
                    let dragMeta = this.dragMeta;
                    receivingContext.emitter.trigger('drop', Object.assign(Object.assign({}, buildDatePointApiWithContext(finalHit.dateSpan, receivingContext)), { draggedEl: pev.subjectEl, jsEvent: pev.origEvent, view: finalView }));
                    if (dragMeta.create) {
                        let addingEvents = internal.eventTupleToStore(droppableEvent);
                        receivingContext.dispatch({
                            type: 'MERGE_EVENTS',
                            eventStore: addingEvents,
                        });
                        if (pev.isTouch) {
                            receivingContext.dispatch({
                                type: 'SELECT_EVENT',
                                eventInstanceId: droppableEvent.instance.instanceId,
                            });
                        }
                        // signal that an external event landed
                        receivingContext.emitter.trigger('eventReceive', {
                            event: new internal.EventImpl(receivingContext, droppableEvent.def, droppableEvent.instance),
                            relatedEvents: [],
                            revert() {
                                receivingContext.dispatch({
                                    type: 'REMOVE_EVENTS',
                                    eventStore: addingEvents,
                                });
                            },
                            draggedEl: pev.subjectEl,
                            view: finalView,
                        });
                    }
                }
                this.receivingContext = null;
                this.droppableEvent = null;
            };
            let hitDragging = this.hitDragging = new HitDragging(dragging, internal.interactionSettingsStore);
            hitDragging.requireInitial = false; // will start outside of a component
            hitDragging.emitter.on('dragstart', this.handleDragStart);
            hitDragging.emitter.on('hitupdate', this.handleHitUpdate);
            hitDragging.emitter.on('dragend', this.handleDragEnd);
            this.suppliedDragMeta = suppliedDragMeta;
        }
        buildDragMeta(subjectEl) {
            if (typeof this.suppliedDragMeta === 'object') {
                return internal.parseDragMeta(this.suppliedDragMeta);
            }
            if (typeof this.suppliedDragMeta === 'function') {
                return internal.parseDragMeta(this.suppliedDragMeta(subjectEl));
            }
            return getDragMetaFromEl(subjectEl);
        }
        displayDrag(nextContext, state) {
            let prevContext = this.receivingContext;
            if (prevContext && prevContext !== nextContext) {
                prevContext.dispatch({ type: 'UNSET_EVENT_DRAG' });
            }
            if (nextContext) {
                nextContext.dispatch({ type: 'SET_EVENT_DRAG', state });
            }
        }
        clearDrag() {
            if (this.receivingContext) {
                this.receivingContext.dispatch({ type: 'UNSET_EVENT_DRAG' });
            }
        }
        canDropElOnCalendar(el, receivingContext) {
            let dropAccept = receivingContext.options.dropAccept;
            if (typeof dropAccept === 'function') {
                return dropAccept.call(receivingContext.calendarApi, el);
            }
            if (typeof dropAccept === 'string' && dropAccept) {
                return Boolean(internal.elementMatches(el, dropAccept));
            }
            return true;
        }
    }
    // Utils for computing event store from the DragMeta
    // ----------------------------------------------------------------------------------------------------
    function computeEventForDateSpan(dateSpan, dragMeta, context) {
        let defProps = Object.assign({}, dragMeta.leftoverProps);
        for (let transform of context.pluginHooks.externalDefTransforms) {
            Object.assign(defProps, transform(dateSpan, dragMeta));
        }
        let { refined, extra } = internal.refineEventDef(defProps, context);
        let def = internal.parseEventDef(refined, extra, dragMeta.sourceId, dateSpan.allDay, context.options.forceEventDuration || Boolean(dragMeta.duration), // hasEnd
        context);
        let start = dateSpan.range.start;
        // only rely on time info if drop zone is all-day,
        // otherwise, we already know the time
        if (dateSpan.allDay && dragMeta.startTime) {
            start = context.dateEnv.add(start, dragMeta.startTime);
        }
        let end = dragMeta.duration ?
            context.dateEnv.add(start, dragMeta.duration) :
            internal.getDefaultEventEnd(dateSpan.allDay, start, context);
        let instance = internal.createEventInstance(def.defId, { start, end });
        return { def, instance };
    }
    // Utils for extracting data from element
    // ----------------------------------------------------------------------------------------------------
    function getDragMetaFromEl(el) {
        let str = getEmbeddedElData(el, 'event');
        let obj = str ?
            JSON.parse(str) :
            { create: false }; // if no embedded data, assume no event creation
        return internal.parseDragMeta(obj);
    }
    internal.config.dataAttrPrefix = '';
    function getEmbeddedElData(el, name) {
        let prefix = internal.config.dataAttrPrefix;
        let prefixedName = (prefix ? prefix + '-' : '') + name;
        return el.getAttribute('data-' + prefixedName) || '';
    }

    /*
    Makes an element (that is *external* to any calendar) draggable.
    Can pass in data that determines how an event will be created when dropped onto a calendar.
    Leverages FullCalendar's internal drag-n-drop functionality WITHOUT a third-party drag system.
    */
    class ExternalDraggable {
        constructor(el, settings = {}) {
            this.handlePointerDown = (ev) => {
                let { dragging } = this;
                let { minDistance, longPressDelay } = this.settings;
                dragging.minDistance =
                    minDistance != null ?
                        minDistance :
                        (ev.isTouch ? 0 : internal.BASE_OPTION_DEFAULTS.eventDragMinDistance);
                dragging.delay =
                    ev.isTouch ? // TODO: eventually read eventLongPressDelay instead vvv
                        (longPressDelay != null ? longPressDelay : internal.BASE_OPTION_DEFAULTS.longPressDelay) :
                        0;
            };
            this.handleDragStart = (ev) => {
                if (ev.isTouch &&
                    this.dragging.delay &&
                    ev.subjectEl.classList.contains('fc-event')) {
                    this.dragging.mirror.getMirrorEl().classList.add('fc-event-selected');
                }
            };
            this.settings = settings;
            let dragging = this.dragging = new FeaturefulElementDragging(el);
            dragging.touchScrollAllowed = false;
            if (settings.itemSelector != null) {
                dragging.pointer.selector = settings.itemSelector;
            }
            if (settings.appendTo != null) {
                dragging.mirror.parentNode = settings.appendTo; // TODO: write tests
            }
            dragging.emitter.on('pointerdown', this.handlePointerDown);
            dragging.emitter.on('dragstart', this.handleDragStart);
            new ExternalElementDragging(dragging, settings.eventData); // eslint-disable-line no-new
        }
        destroy() {
            this.dragging.destroy();
        }
    }

    /*
    Detects when a *THIRD-PARTY* drag-n-drop system interacts with elements.
    The third-party system is responsible for drawing the visuals effects of the drag.
    This class simply monitors for pointer movements and fires events.
    It also has the ability to hide the moving element (the "mirror") during the drag.
    */
    class InferredElementDragging extends internal.ElementDragging {
        constructor(containerEl) {
            super(containerEl);
            this.shouldIgnoreMove = false;
            this.mirrorSelector = '';
            this.currentMirrorEl = null;
            this.handlePointerDown = (ev) => {
                this.emitter.trigger('pointerdown', ev);
                if (!this.shouldIgnoreMove) {
                    // fire dragstart right away. does not support delay or min-distance
                    this.emitter.trigger('dragstart', ev);
                }
            };
            this.handlePointerMove = (ev) => {
                if (!this.shouldIgnoreMove) {
                    this.emitter.trigger('dragmove', ev);
                }
            };
            this.handlePointerUp = (ev) => {
                this.emitter.trigger('pointerup', ev);
                if (!this.shouldIgnoreMove) {
                    // fire dragend right away. does not support a revert animation
                    this.emitter.trigger('dragend', ev);
                }
            };
            let pointer = this.pointer = new PointerDragging(containerEl);
            pointer.emitter.on('pointerdown', this.handlePointerDown);
            pointer.emitter.on('pointermove', this.handlePointerMove);
            pointer.emitter.on('pointerup', this.handlePointerUp);
        }
        destroy() {
            this.pointer.destroy();
        }
        setIgnoreMove(bool) {
            this.shouldIgnoreMove = bool;
        }
        setMirrorIsVisible(bool) {
            if (bool) {
                // restore a previously hidden element.
                // use the reference in case the selector class has already been removed.
                if (this.currentMirrorEl) {
                    this.currentMirrorEl.style.visibility = '';
                    this.currentMirrorEl = null;
                }
            }
            else {
                let mirrorEl = this.mirrorSelector
                    // TODO: somehow query FullCalendars WITHIN shadow-roots
                    ? document.querySelector(this.mirrorSelector)
                    : null;
                if (mirrorEl) {
                    this.currentMirrorEl = mirrorEl;
                    mirrorEl.style.visibility = 'hidden';
                }
            }
        }
    }

    /*
    Bridges third-party drag-n-drop systems with FullCalendar.
    Must be instantiated and destroyed by caller.
    */
    class ThirdPartyDraggable {
        constructor(containerOrSettings, settings) {
            let containerEl = document;
            if (
            // wish we could just test instanceof EventTarget, but doesn't work in IE11
            containerOrSettings === document ||
                containerOrSettings instanceof Element) {
                containerEl = containerOrSettings;
                settings = settings || {};
            }
            else {
                settings = (containerOrSettings || {});
            }
            let dragging = this.dragging = new InferredElementDragging(containerEl);
            if (typeof settings.itemSelector === 'string') {
                dragging.pointer.selector = settings.itemSelector;
            }
            else if (containerEl === document) {
                dragging.pointer.selector = '[data-event]';
            }
            if (typeof settings.mirrorSelector === 'string') {
                dragging.mirrorSelector = settings.mirrorSelector;
            }
            let externalDragging = new ExternalElementDragging(dragging, settings.eventData);
            // The hit-detection system requires that the dnd-mirror-element be pointer-events:none,
            // but this can't be guaranteed for third-party draggables, so disable
            externalDragging.hitDragging.disablePointCheck = true;
        }
        destroy() {
            this.dragging.destroy();
        }
    }

    var plugin = core.createPlugin({
        name: '@fullcalendar/interaction',
        componentInteractions: [DateClicking, DateSelecting, EventDragging, EventResizing],
        calendarInteractions: [UnselectAuto],
        elementDraggingImpl: FeaturefulElementDragging,
        optionRefiners: OPTION_REFINERS,
        listenerRefiners: LISTENER_REFINERS,
    });

    core.globalPlugins.push(plugin);

    exports.Draggable = ExternalDraggable;
    exports.ThirdPartyDraggable = ThirdPartyDraggable;
    exports["default"] = plugin;

    Object.defineProperty(exports, '__esModule', { value: true });

    return exports;

})({}, FullCalendar, FullCalendar.Internal);
