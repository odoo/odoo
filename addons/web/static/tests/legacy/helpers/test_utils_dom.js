odoo.define('web.test_utils_dom', function (require) {
    "use strict";

    const concurrency = require('web.concurrency');
    const Widget = require('web.Widget');

    const { Component } = owl;

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
    const keyboardEventBubble = args => Object.assign({}, args, { bubbles: true, keyCode: args.which });
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

    //-------------------------------------------------------------------------
    // Public functions
    //-------------------------------------------------------------------------

    /**
     * Click on a specified element. If the option first or last is not specified,
     * this method also check the unicity and the visibility of the target.
     *
     * @param {string|EventTarget|EventTarget[]} el (if string: it is a (jquery) selector)
     * @param {Object} [options={}] click options
     * @param {boolean} [options.allowInvisible=false] if true, clicks on the
     *   element event if it is invisible
     * @param {boolean} [options.first=false] if true, clicks on the first element
     * @param {boolean} [options.last=false] if true, clicks on the last element
     * @returns {Promise}
     */
    async function click(el, options = {}) {
        let matches, target;
        let selectorMsg = "";
        if (typeof el === 'string') {
            el = $(el);
        }
        if (_isEventTarget(el)) {
            // EventTarget
            matches = [el];
        } else {
            // Any other iterable object containing EventTarget objects (jQuery, HTMLCollection, etc.)
            matches = [...el];
        }

        const validMatches = options.allowInvisible ?
            matches : matches.filter(t => $(t).is(':visible'));

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
     * @param {string|EventTarget|EventTarget[]} el (if string: it is a (jquery) selector)
     * @param {boolean} [options={}] click options
     * @param {boolean} [options.allowInvisible=false] if true, clicks on the
     *   element event if it is invisible
     * @returns {Promise}
     */
    async function clickFirst(el, options) {
        return click(el, Object.assign({}, options, { first: true }));
    }

    /**
     * Click on the last element of a list of elements.  Note that if the list has
     * only one visible element, we trigger an error. In that case, it is better to
     * use the click helper instead.
     *
     * @param {string|EventTarget|EventTarget[]} el (if string: it is a (jquery) selector)
     * @param {boolean} [options={}] click options
     * @param {boolean} [options.allowInvisible=false] if true, clicks on the
     *   element event if it is invisible
     * @returns {Promise}
     */
    async function clickLast(el, options) {
        return click(el, Object.assign({}, options, { last: true }));
    }

    /**
     * Simulate a drag and drop operation between 2 jquery nodes: $el and $to.
     * This is a crude simulation, with only the mousedown, mousemove and mouseup
     * events, but it is enough to help test drag and drop operations with jqueryUI
     * sortable.
     *
     * @todo: remove the withTrailingClick option when the jquery update branch is
     *   merged.  This is not the default as of now, because handlers are triggered
     *   synchronously, which is not the same as the 'reality'.
     *
     * @param {jQuery|EventTarget} $el
     * @param {jQuery|EventTarget} $to
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
     * @param {jQuery|EventTarget} [options.mouseenterTarget=undefined] target of the mouseenter event
     * @param {jQuery|EventTarget} [options.mousedownTarget=undefined] target of the mousedown event
     * @param {jQuery|EventTarget} [options.mousemoveTarget=undefined] target of the mousemove event
     * @param {jQuery|EventTarget} [options.mouseupTarget=undefined] target of the mouseup event
     * @param {jQuery|EventTarget} [options.ctrlKey=undefined] if the ctrl key should be considered pressed at the time of mouseup
     * @returns {Promise}
     */
    async function dragAndDrop($el, $to, options) {
        let el = null;
        if (_isEventTarget($el)) {
            el = $el;
            $el = $(el);
        }
        if (_isEventTarget($to)) {
            $to = $($to);
        }
        options = options || {};
        const position = options.position || 'center';
        const elementCenter = $el.offset();
        const toOffset = $to.offset();

        if (typeof position === 'object') {
            toOffset.top += position.top + 1;
            toOffset.left += position.left + 1;
        } else {
            toOffset.top += $to.outerHeight() / 2;
            toOffset.left += $to.outerWidth() / 2;
            const vertical_offset = (toOffset.top < elementCenter.top) ? -1 : 1;
            if (position === 'top') {
                toOffset.top -= $to.outerHeight() / 2 + vertical_offset;
            } else if (position === 'bottom') {
                toOffset.top += $to.outerHeight() / 2 - vertical_offset;
            } else if (position === 'left') {
                toOffset.left -= $to.outerWidth() / 2;
            } else if (position === 'right') {
                toOffset.left += $to.outerWidth() / 2;
            }
        }

        if ($to[0].ownerDocument !== document) {
            // we are in an iframe
            const bound = $('iframe')[0].getBoundingClientRect();
            toOffset.left += bound.left;
            toOffset.top += bound.top;
        }
        await triggerEvent(options.mouseenterTarget || el || $el, 'mouseover', {}, true);
        if (!(options.continueMove)) {
            elementCenter.left += $el.outerWidth() / 2;
            elementCenter.top += $el.outerHeight() / 2;

            await triggerEvent(options.mousedownTarget || el || $el, 'mousedown', {
                which: 1,
                pageX: elementCenter.left,
                pageY: elementCenter.top
            }, true);
        }
        await triggerEvent(options.mousemoveTarget || el || $el, 'mousemove', {
            which: 1,
            pageX: toOffset.left,
            pageY: toOffset.top
        }, true);

        if (!options.disableDrop) {
            await triggerEvent(options.mouseupTarget || el || $el, 'mouseup', {
                which: 1,
                pageX: toOffset.left,
                pageY: toOffset.top,
                ctrlKey: options.ctrlKey,
            }, true);
            if (options.withTrailingClick) {
                await triggerEvent(options.mouseupTarget || el || $el, 'click', {}, true);
            }
        } else {
            // It's impossible to drag another element when one is already
            // being dragged. So it's necessary to finish the drop when the test is
            // over otherwise it's impossible for the next tests to drag and
            // drop elements.
            $el.on('remove', function () {
                triggerEvent($el, 'mouseup', {}, true);
            });
        }
        return returnAfterNextAnimationFrame();
    }

    /**
     * Helper method to retrieve a distinct item from a collection of elements defined
     * by the given "selector" string. It can either be the index of the item or its
     * inner text.
     * @param {Element} el
     * @param {string} selector
     * @param {number | string} [elFinder=0]
     * @returns {Element | null}
     */
    function findItem(el, selector, elFinder = 0) {
        const elements = [...getNode(el).querySelectorAll(selector)];
        if (!elements.length) {
            throw new Error(`No element found with selector "${selector}".`);
        }
        switch (typeof elFinder) {
            case "number": {
                const match = elements[elFinder];
                if (!match) {
                    throw new Error(
                        `No element with selector "${selector}" at index ${elFinder}.`
                    );
                }
                return match;
            }
            case "string": {
                const match = elements.find(
                    (el) => el.innerText.trim().toLowerCase() === elFinder.toLowerCase()
                );
                if (!match) {
                    throw new Error(
                        `No element with selector "${selector}" containing "${elFinder}".
                    `);
                }
                return match;
            }
            default: throw new Error(
                `Invalid provided element finder: must be a number|string|function.`
            );
        }
    }

    /**
     * Helper function used to extract an HTML EventTarget element from a given
     * target. The extracted element will depend on the target type:
     * - Component|Widget -> el
     * - jQuery -> associated element (must have 1)
     * - HTMLCollection (or similar) -> first element (must have 1)
     * - string -> result of document.querySelector with string
     * - else -> as is
     * @private
     * @param {(Component|Widget|jQuery|HTMLCollection|HTMLElement|string)} target
     * @returns {EventTarget}
     */
    function getNode(target) {
        let nodes;
        if (target instanceof Component || target instanceof Widget) {
            nodes = [target.el];
        } else if (typeof target === 'string') {
            nodes = document.querySelectorAll(target);
        } else if (target === jQuery) { // jQuery (or $)
            nodes = [document.body];
        } else if (target.length) { // jQuery instance, HTMLCollection or array
            nodes = target;
        } else {
            nodes = [target];
        }
        if (nodes.length !== 1) {
            throw new Error(`Found ${nodes.length} nodes instead of 1.`);
        }
        const node = nodes[0];
        if (!node) {
            throw new Error(`Expected a node and got ${node}.`);
        }
        if (!_isEventTarget(node)) {
            throw new Error(`Expected node to be an instance of EventTarget and got ${node.constructor.name}.`);
        }
        return node;
    }

    /**
     * Open the datepicker of a given element.
     *
     * @param {jQuery} $datepickerEl element to which a datepicker is attached
     */
    async function openDatepicker($datepickerEl) {
        return click($datepickerEl.find('.o_datepicker_input'));
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
        await concurrency.delay(0);
        await new Promise(resolve => {
            window.requestAnimationFrame(resolve);
        });
    }

    /**
     * Trigger an event on the specified target.
     * This function will dispatch a native event to an EventTarget or a
     * jQuery event to a jQuery object. This behaviour can be overridden by the
     * jquery option.
     *
     * @param {EventTarget|EventTarget[]} el
     * @param {string} eventType event type
     * @param {Object} [eventAttrs] event attributes
     *   on a jQuery element with the `$.fn.trigger` function
     * @param {Boolean} [fast=false] true if the trigger event have to wait for a single tick instead of waiting for the next animation frame
     * @returns {Promise}
     */
    async function triggerEvent(el, eventType, eventAttrs = {}, fast = false) {
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
     * @param {EventTarget|EventTarget[]} el
     * @param {string[]} events the events you want to trigger
     * @returns {Promise}
     */
    async function triggerEvents(el, events) {
        if (el instanceof jQuery) {
            if (el.length !== 1) {
                throw new Error(`target has length ${el.length} instead of 1`);
            }
        }
        if (typeof events === 'string') {
            events = [events];
        }

        for (let e = 0; e < events.length; e++) {
            await triggerEvent(el, events[e]);
        }
    }

    /**
     * Simulate a keypress event for a given character
     *
     * @param {string} char the character, or 'ENTER'
     * @returns {Promise}
     */
    async function triggerKeypressEvent(char) {
        let keycode;
        if (char === 'Enter') {
            keycode = $.ui.keyCode.ENTER;
        } else if (char === "Tab") {
            keycode = $.ui.keyCode.TAB;
        } else {
            keycode = char.charCodeAt(0);
        }
        return triggerEvent(document.body, 'keypress', {
            key: char,
            keyCode: keycode,
            which: keycode,
        });
    }

    /**
     * simulate a mouse event with a custom event who add the item position. This is
     * sometimes necessary because the basic way to trigger an event (such as
     * $el.trigger('mousemove')); ) is too crude for some uses.
     *
     * @param {jQuery|EventTarget} $el
     * @param {string} type a mouse event type, such as 'mousedown' or 'mousemove'
     * @returns {Promise}
     */
    async function triggerMouseEvent($el, type) {
        const el = $el instanceof jQuery ? $el[0] : $el;
        if (!el) {
            throw new Error(`no target found to trigger MouseEvent`);
        }
        const rect = el.getBoundingClientRect();
        // try to click around the center of the element, biased to the bottom
        // right as chrome  messes up when clicking on the top-left corner...
        const left = rect.x + Math.ceil(rect.width / 2);
        const top = rect.y + Math.ceil(rect.height / 2);
        return triggerEvent(el, type, {which: 1, clientX: left, clientY: top});
    }

    /**
     * simulate a mouse event with a custom event on a position x and y. This is
     * sometimes necessary because the basic way to trigger an event (such as
     * $el.trigger('mousemove')); ) is too crude for some uses.
     *
     * @param {integer} x
     * @param {integer} y
     * @param {string} type a mouse event type, such as 'mousedown' or 'mousemove'
     * @returns {HTMLElement}
     */
    async function triggerPositionalMouseEvent(x, y, type) {
        const ev = document.createEvent("MouseEvent");
        const el = document.elementFromPoint(x, y);
        ev.initMouseEvent(
            type,
            true /* bubble */,
            true /* cancelable */,
            window, null,
            x, y, x, y, /* coordinates */
            false, false, false, false, /* modifier keys */
            0 /*left button*/, null
        );
        el.dispatchEvent(ev);
        return el;
    }

    /**
     * Simulate a "TAP" (touch) event with a custom position x and y.
     *
     * @param {number} x
     * @param {number} y
     * @returns {HTMLElement}
     */
    async function triggerPositionalTapEvents(x, y) {
        const element = document.elementFromPoint(x, y);
        const touch = new Touch({
            identifier: 0,
            target: element,
            clientX: x,
            clientY: y,
            pageX: x,
            pageY: y,
        });
        await triggerEvent(element, 'touchstart', {
            touches: [touch],
            targetTouches: [touch],
            changedTouches: [touch],
        });
        await triggerEvent(element, 'touchmove', {
            touches: [touch],
            targetTouches: [touch],
            changedTouches: [touch],
        });
        await triggerEvent(element, 'touchend', {
            changedTouches: [touch],
        });
        return element;
    }

    return {
        click,
        clickFirst,
        clickLast,
        dragAndDrop,
        findItem,
        getNode,
        openDatepicker,
        returnAfterNextAnimationFrame,
        triggerEvent,
        triggerEvents,
        triggerKeypressEvent,
        triggerMouseEvent,
        triggerPositionalMouseEvent,
        triggerPositionalTapEvents,
    };
});
