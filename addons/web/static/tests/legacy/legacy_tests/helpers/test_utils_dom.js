// @ts-check

/** @odoo-module alias=@web/../tests/legacy_tests/helpers/test_utils_dom default=false */

import { delay } from "@web/core/utils/concurrency";

    /**
     * DOM Test Utils
     *
     * This module defines various utility functions to help simulate DOM events.
     *
     * Note that all methods defined in this module are exported in the main
     * testUtils file.
     */

    //-------------------------------------------------------------------------
    // Private functions
    //-------------------------------------------------------------------------

    // TriggerEvent helpers
    const keyboardEventBubble = args => Object.assign({}, args, { bubbles: true});
    const mouseEventMapping = args => Object.assign({}, args, {
        bubbles: true,
        cancelable: true,
        clientX: args ? args.clientX || args.pageX : undefined,
        clientY: args ? args.clientY || args.pageY : undefined,
        view: window,
    });
    const mouseEventNoBubble = args => Object.assign({}, args, {
        bubbles: false,
        cancelable: false,
        clientX: args ? args.clientX || args.pageX : undefined,
        clientY: args ? args.clientY || args.pageY : undefined,
        view: window,
    });
    const touchEventMapping = args => Object.assign({}, args, {
        cancelable: true,
        bubbles: true,
        composed: true,
        view: window,
        rotation: 0.0,
        zoom: 1.0,
    });
    const touchEventCancelMapping = args => Object.assign({}, touchEventMapping(args), {
        cancelable: false,
    });
    const noBubble = args => Object.assign({}, args, { bubbles: false });
    const onlyBubble = args => Object.assign({}, args, { bubbles: true });
    // TriggerEvent constructor/args processor mapping
    const EVENT_TYPES = {
        auxclick: { constructor: MouseEvent, processParameters: mouseEventMapping },
        click: { constructor: MouseEvent, processParameters: mouseEventMapping },
        contextmenu: { constructor: MouseEvent, processParameters: mouseEventMapping },
        dblclick: { constructor: MouseEvent, processParameters: mouseEventMapping },
        mousedown: { constructor: MouseEvent, processParameters: mouseEventMapping },
        mouseup: { constructor: MouseEvent, processParameters: mouseEventMapping },

        mousemove: { constructor: MouseEvent, processParameters: mouseEventMapping },
        mouseenter: { constructor: MouseEvent, processParameters: mouseEventNoBubble },
        mouseleave: { constructor: MouseEvent, processParameters: mouseEventNoBubble },
        mouseover: { constructor: MouseEvent, processParameters: mouseEventMapping },
        mouseout: { constructor: MouseEvent, processParameters: mouseEventMapping },

        focus: { constructor: FocusEvent, processParameters: noBubble },
        focusin: { constructor: FocusEvent, processParameters: onlyBubble },
        blur: { constructor: FocusEvent, processParameters: noBubble },

        cut: { constructor: ClipboardEvent, processParameters: onlyBubble },
        copy: { constructor: ClipboardEvent, processParameters: onlyBubble },
        paste: { constructor: ClipboardEvent, processParameters: onlyBubble },

        keydown: { constructor: KeyboardEvent, processParameters: keyboardEventBubble },
        keypress: { constructor: KeyboardEvent, processParameters: keyboardEventBubble },
        keyup: { constructor: KeyboardEvent, processParameters: keyboardEventBubble },

        drag: { constructor: DragEvent, processParameters: onlyBubble },
        dragend: { constructor: DragEvent, processParameters: onlyBubble },
        dragenter: { constructor: DragEvent, processParameters: onlyBubble },
        dragstart: { constructor: DragEvent, processParameters: onlyBubble },
        dragleave: { constructor: DragEvent, processParameters: onlyBubble },
        dragover: { constructor: DragEvent, processParameters: onlyBubble },
        drop: { constructor: DragEvent, processParameters: onlyBubble },

        input: { constructor: InputEvent, processParameters: onlyBubble },

        compositionstart: { constructor: CompositionEvent, processParameters: onlyBubble },
        compositionend: { constructor: CompositionEvent, processParameters: onlyBubble },
    };

    if (typeof TouchEvent === 'function') {
        Object.assign(EVENT_TYPES, {
            touchstart: {constructor: TouchEvent, processParameters: touchEventMapping},
            touchend: {constructor: TouchEvent, processParameters: touchEventMapping},
            touchmove: {constructor: TouchEvent, processParameters: touchEventMapping},
            touchcancel: {constructor: TouchEvent, processParameters: touchEventCancelMapping},
        });
    }

    /**
     * Check if an object is an instance of EventTarget.
     *
     * @param {Object} node
     * @returns {boolean}
     */
    function _isEventTarget(node) {
        if (!node) {
            throw new Error(`Provided node is ${node}.`);
        }
        if (node instanceof window.top.EventTarget) {
            return true;
        }
        const contextWindow = node.defaultView || // document
            (node.ownerDocument && node.ownerDocument.defaultView); // iframe node
        return contextWindow && node instanceof contextWindow.EventTarget;
    }

    /**
     * Check whether an element is visible (has layout dimensions).
     *
     * @param {Element} el
     * @returns {boolean}
     */
    function _isVisible(el) {
        return el.offsetWidth > 0 && el.offsetHeight > 0;
    }

    /**
     * Return the page offset (top/left relative to the document) for an element,
     * equivalent to the former jQuery .offset() method.
     *
     * @param {Element} el
     * @returns {{top: number, left: number}}
     */
    function _offset(el) {
        const rect = el.getBoundingClientRect();
        return {
            top: rect.top + window.scrollY,
            left: rect.left + window.scrollX,
        };
    }

    //-------------------------------------------------------------------------
    // Public functions
    //-------------------------------------------------------------------------

    /**
     * Click on a specified element. If the option first or last is not specified,
     * this method also check the unicity and the visibility of the target.
     *
     * @param {string|EventTarget|EventTarget[]} el (if string: it is a CSS selector)
     * @param {Object} [options={}] click options
     * @param {boolean} [options.allowInvisible=false] if true, clicks on the
     *   element event if it is invisible
     * @param {boolean} [options.first=false] if true, clicks on the first element
     * @param {boolean} [options.last=false] if true, clicks on the last element
     * @returns {Promise}
     */
    export async function click(el, options = {}) {
        let matches, target;
        let selectorMsg = "";
        if (typeof el === 'string') {
            matches = [...document.querySelectorAll(el)];
            selectorMsg = `(selector: "${el}")`;
        } else if (_isEventTarget(el)) {
            matches = [el];
        } else {
            // Any other iterable object containing EventTarget objects (NodeList, HTMLCollection, etc.)
            matches = [...el];
        }
        if (matches.length > 0 && matches[0].disabled) {
            throw new Error("Can't click on a disabled button");
        }

        const validMatches = options.allowInvisible ?
            matches : matches.filter(t => _isVisible(t));

        if (options.first) {
            if (validMatches.length === 1) {
                throw new Error(`There should be more than one visible target ${selectorMsg}.  If` +
                    ' you are sure that there is exactly one target, please use the ' +
                    'click function instead of the clickFirst function');
            }
            target = validMatches[0];
        } else if (options.last) {
            if (validMatches.length === 1) {
                throw new Error(`There should be more than one visible target ${selectorMsg}.  If` +
                    ' you are sure that there is exactly one target, please use the ' +
                    'click function instead of the clickLast function');
            }
            target = validMatches[validMatches.length - 1];
        } else if (validMatches.length !== 1) {
            throw new Error(`Found ${validMatches.length} elements to click on, instead of 1 ${selectorMsg}`);
        } else {
            target = validMatches[0];
        }
        if (validMatches.length === 0 && matches.length > 0) {
            throw new Error(`Element to click on is not visible ${selectorMsg}`);
        }
        if (target.disabled) {
            return;
        }

        return triggerEvent(target, 'click');
    }

    /**
     * Click on the first element of a list of elements.  Note that if the list has
     * only one visible element, we trigger an error. In that case, it is better to
     * use the click helper instead.
     *
     * @param {string|EventTarget|EventTarget[]} el (if string: it is a CSS selector)
     * @param {boolean} [options={}] click options
     * @param {boolean} [options.allowInvisible=false] if true, clicks on the
     *   element event if it is invisible
     * @returns {Promise}
     */
    async function clickFirst(el, options) {
        return click(el, Object.assign({}, options, { first: true }));
    }

    /**
     * Simulate a drag and drop operation between 2 DOM elements.
     * This is a crude simulation, with only the mousedown, mousemove and mouseup
     * events, but it is enough to help test drag and drop operations with native
     * sortable.
     *
     * @param {Element} el the element to drag
     * @param {Element} to the drop target element
     * @param {Object} [options]
     * @param {string|Object} [options.position='center'] target position:
     *   can either be one of {'top', 'bottom', 'left', 'right'} or
     *   an object with two attributes (top and left))
     * @param {boolean} [options.disableDrop=false] whether to trigger the drop action
     * @param {boolean} [options.continueMove=false] whether to trigger the
     *   mousedown action (will only work after another call of this function with
     *   without this option)
     * @param {boolean} [options.withTrailingClick=false] if true, this utility
     *   function will also trigger a click on the target after the mouseup event
     *   (this is actually what happens when a drag and drop operation is done)
     * @param {Element} [options.mouseenterTarget=undefined] target of the mouseenter event
     * @param {Element} [options.mousedownTarget=undefined] target of the mousedown event
     * @param {Element} [options.mousemoveTarget=undefined] target of the mousemove event
     * @param {Element} [options.mouseupTarget=undefined] target of the mouseup event
     * @param {boolean} [options.ctrlKey=undefined] if the ctrl key should be considered pressed at the time of mouseup
     * @returns {Promise}
     */
    async function dragAndDrop(el, to, options) {
        options = options || {};
        const position = options.position || 'center';
        const elementCenter = _offset(el);
        const toOffset = _offset(to);

        if (typeof position === 'object') {
            toOffset.top += position.top + 1;
            toOffset.left += position.left + 1;
        } else {
            toOffset.top += to.offsetHeight / 2;
            toOffset.left += to.offsetWidth / 2;
            const vertical_offset = (toOffset.top < elementCenter.top) ? -1 : 1;
            if (position === 'top') {
                toOffset.top -= to.offsetHeight / 2 + vertical_offset;
            } else if (position === 'bottom') {
                toOffset.top += to.offsetHeight / 2 - vertical_offset;
            } else if (position === 'left') {
                toOffset.left -= to.offsetWidth / 2;
            } else if (position === 'right') {
                toOffset.left += to.offsetWidth / 2;
            }
        }

        if (to.ownerDocument !== document) {
            // we are in an iframe
            const bound = document.querySelector('iframe').getBoundingClientRect();
            toOffset.left += bound.left;
            toOffset.top += bound.top;
        }
        await triggerEvent(options.mouseenterTarget || el, 'mouseover', {}, true);
        if (!(options.continueMove)) {
            elementCenter.left += el.offsetWidth / 2;
            elementCenter.top += el.offsetHeight / 2;

            await triggerEvent(options.mousedownTarget || el, 'mousedown', {
                which: 1,
                pageX: elementCenter.left,
                pageY: elementCenter.top
            }, true);
        }
        await triggerEvent(options.mousemoveTarget || el, 'mousemove', {
            which: 1,
            pageX: toOffset.left,
            pageY: toOffset.top
        }, true);

        if (!options.disableDrop) {
            await triggerEvent(options.mouseupTarget || el, 'mouseup', {
                which: 1,
                pageX: toOffset.left,
                pageY: toOffset.top,
                ctrlKey: options.ctrlKey,
            }, true);
            if (options.withTrailingClick) {
                await triggerEvent(options.mouseupTarget || el, 'click', {}, true);
            }
        } else {
            // It's impossible to drag another element when one is already
            // being dragged. So it's necessary to finish the drop when the test is
            // over otherwise it's impossible for the next tests to drag and
            // drop elements.
            const observer = new MutationObserver((mutations) => {
                for (const mutation of mutations) {
                    for (const removed of mutation.removedNodes) {
                        if (removed === el || removed.contains(el)) {
                            observer.disconnect();
                            triggerEvent(el, 'mouseup', {}, true);
                            return;
                        }
                    }
                }
            });
            observer.observe(el.parentNode || document.body, { childList: true, subtree: true });
        }
        return returnAfterNextAnimationFrame();
    }

    /**
     * Returns a promise that will be resolved after the nextAnimationFrame after
     * the next tick
     *
     * This is useful to guarantee that OWL has had the time to render
     *
     * @returns {Promise}
     */
    async function returnAfterNextAnimationFrame() {
        await delay(0);
        await new Promise(resolve => {
            window.requestAnimationFrame(resolve);
        });
    }

    /**
     * Trigger an event on the specified target.
     * This function will dispatch a native DOM event to an EventTarget.
     *
     * @param {EventTarget|EventTarget[]} el
     * @param {string} eventType event type
     * @param {Object} [eventAttrs] event attributes
     * @param {Boolean} [fast=false] true if the trigger event have to wait for a single tick instead of waiting for the next animation frame
     * @returns {Promise}
     */
    export async function triggerEvent(el, eventType, eventAttrs = {}, fast = false) {
        let matches;
        let selectorMsg = "";
        if (_isEventTarget(el)) {
            matches = [el];
        } else {
            matches = [...el];
        }

        if (matches.length !== 1) {
            throw new Error(`Found ${matches.length} elements to trigger "${eventType}" on, instead of 1 ${selectorMsg}`);
        }

        const target = matches[0];
        let event;

        if (!EVENT_TYPES[eventType] && !EVENT_TYPES[eventType.type]) {
            event = new Event(eventType, Object.assign({}, eventAttrs, { bubbles: true }));
        } else {
            if (typeof eventType === "object") {
                const { constructor, processParameters } = EVENT_TYPES[eventType.type];
                const eventParameters = processParameters(eventType);
                event = new constructor(eventType.type, eventParameters);
            } else {
                const { constructor, processParameters } = EVENT_TYPES[eventType];
                event = new constructor(eventType, processParameters(eventAttrs));
            }
        }
        target.dispatchEvent(event);
        return fast ? undefined : returnAfterNextAnimationFrame();
    }

    /**
     * Trigger multiple events on the specified element.
     *
     * @param {EventTarget} el
     * @param {string[]} events the events you want to trigger
     * @returns {Promise}
     */
    async function triggerEvents(el, events) {
        if (typeof events === 'string') {
            events = [events];
        }

        for (let e = 0; e < events.length; e++) {
            await triggerEvent(el, events[e]);
        }
    }

    export default {
        click,
        clickFirst,
        dragAndDrop,
        returnAfterNextAnimationFrame,
        triggerEvent,
        triggerEvents,
    };
