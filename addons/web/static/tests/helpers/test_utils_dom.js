odoo.define('web.test_utils_dom', function (require) {
"use strict";

/**
 * DOM Test Utils
 *
 * This module defines various utility functions to help simulate DOM events.
 *
 * Note that all methods defined in this module are exported in the main
 * testUtils file.
 */

var concurrency = require('web.concurrency');

/**
 * simulate a drag and drop operation between 2 jquery nodes: $el and $to.
 * This is a crude simulation, with only the mousedown, mousemove and mouseup
 * events, but it is enough to help test drag and drop operations with jqueryUI
 * sortable.
 *
 * @param {jqueryElement} $el
 * @param {jqueryElement} $to
 * @param {Object} [options]
 * @param {string|Object} [options.position='center'] target position:
 *   can either be one of {'top', 'bottom', 'left', 'right'} or
 *   an object with two attributes (top and left))
 * @param {boolean} [options.disableDrop=false] whether to trigger the drop action
 * @param {boolean} [options.continueMove=false] whether to trigger the
 * @param {string} [options.isNativeDragAndDrop=false] whether to trigger jQuery mouse events or use native events
 * @param {string} [options.isExtraMousemove=false] whether to trigger extra mousemove
 * @returns {Deferred}
 *   mousedown action (will only work after another call of this function with
 *   without this option)
 */
function dragAndDrop($el, $to, options) {
    // debugger
    var def = $.Deferred();
    var position = (options && options.position) || 'center';
    var isNativeDragAndDrop = (options && options.nativeDragAndDrop);
    var elementCenter = $el.offset();
    var toOffset = $to.offset();

    if (_.isObject(position)) {
        toOffset.top += position.top;
        toOffset.left += position.left;
    } else {
        toOffset.top += $to.outerHeight() / 2;
        toOffset.left += $to.outerWidth() / 2;
        var vertical_offset = (toOffset.top < elementCenter.top) ? -2 : 2;
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
        var bound = $('iframe')[0].getBoundingClientRect();
        toOffset.left += bound.left;
        toOffset.top += bound.top;
    }
    if (isNativeDragAndDrop) {
        // Need to trigger extra mousemove, like literally we have to trigger mousemove two times
        // if dropping area is available after two or more element
        // for example drag and drop from 1st stage to 3rd or 4th or any stage after 3rd stage
        // https://github.com/RubaXa/Sortable/issues/1303#issuecomment-379166526
        // var isExtraMousemove = (options && options.extraMousemove);
        // in case of extra mousemove (two times) first mousemove shouldn't be till $to element
        // var left = toOffset.left;
        // $el.trigger($.Event("mouseenter"));
        triggerPositionalMouseEvent(elementCenter.left, elementCenter.top, 'mouseenter', $el[0]);
        triggerPositionalMouseEvent(elementCenter.left, elementCenter.top, 'mousedown', $el[0]);
        triggerPositionalMouseEvent(toOffset.left, toOffset.top , 'mousemove', $to[0]);
        // if (isExtraMousemove) {
        //     concurrency.delay(50).then(function () {
        //         triggerPositionalMouseEvent(toOffset.left, toOffset.top, 'mousemove', $to[0]);
        //         return concurrency.delay(50);
        //     }).then(function () {
        //         triggerPositionalMouseEvent(toOffset.left, toOffset.top, 'mouseup', $to[0]);
        //         def.resolve();
        //     });
        // } else {
            concurrency.delay(50).then(function () {
                triggerPositionalMouseEvent(toOffset.left, toOffset.top, 'mouseup', $el[0]);
                def.resolve();
            });
        // }
    } else {
        $el.trigger($.Event("mouseenter"));
        if (!(options && options.continueMove)) {
            elementCenter.left += $el.outerWidth() / 2;
            elementCenter.top += $el.outerHeight() / 2;
    
            $el.trigger($.Event("mousedown", {
                which: 1,
                pageX: elementCenter.left,
                pageY: elementCenter.top
            }));
        }
    
        $el.trigger($.Event("mousemove", {
            which: 1,
            pageX: toOffset.left,
            pageY: toOffset.top
        }));
    
        if (!(options && options.disableDrop)) {
            $el.trigger($.Event("mouseup", {
                which: 1,
                pageX: toOffset.left,
                pageY: toOffset.top
            }));
        } else {
            // It's impossible to drag another element when one is already
            // being dragged. So it's necessary to finish the drop when the test is
            // over otherwise it's impossible for the next tests to drag and
            // drop elements.
            $el.on("remove", function () {
                $el.trigger($.Event("mouseup"));
            });
        }
    }
    return $.when(def);
}

/**
 * simulate a mouse event with a custom event who add the item position. This is
 * sometimes necessary because the basic way to trigger an event (such as
 * $el.trigger('mousemove')); ) is too crude for some uses.
 *
 * @param {jqueryElement} $el
 * @param {string} type a mouse event type, such as 'mousedown' or 'mousemove'
 */
function triggerMouseEvent($el, type) {
    var pos = $el.offset();
    var e = new $.Event(type);
    e.pageX = e.layerX = e.screenX = pos.left;
    e.pageY = e.layerY = e.screenY = pos.top;
    e.which = 1;
    $el.trigger(e);
}

/**
 * simulate a mouse event with a custom event on a position x and y. This is
 * sometimes necessary because the basic way to trigger an event (such as
 * $el.trigger('mousemove')); ) is too crude for some uses.
 *
 * @param {integer} x
 * @param {integer} y
 * @param {string} type a mouse event type, such as 'mousedown' or 'mousemove'
 */
function triggerPositionalMouseEvent(x, y, type, el) {
    var ev = document.createEvent("MouseEvent");
    el = el || document.elementFromPoint(x,y);
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
 * simulate a keypress event for a given character
 *
 * @param {string} char the character, or 'ENTER'
 */
function triggerKeypressEvent(char) {
    var keycode;
    if (char === "Enter") {
        keycode = $.ui.keyCode.ENTER;
    } else {
        keycode = char.charCodeAt(0);
    }
    return $('body').trigger($.Event('keypress', { which: keycode, keyCode: keycode }));
}

/**
 * Opens the datepicker of a given element.
 *
 * @param {jQuery} $datepickerEl element to which a datepicker is attached
 */
function openDatepicker($datepickerEl) {
    $datepickerEl.find('.o_datepicker_input').trigger('focus.datetimepicker');
}

/**
 * Click on a specified element. If the option first or last is not specified,
 * this method also check the unicity and the visibility of the target.
 *
 * @param {string|NodeList|jQuery} el (if string: it is a (jquery) selector)
 * @param {Object} [options]
 * @param {boolean} [options.first=false] if true, clicks on the first element
 * @param {boolean} [options.last=false] if true, clicks on the last element
 */
function click(el, options) {
    options = options || {};
    var matches = typeof el === 'string' ? $(el) : el;
    var selectorMsg = el.selector ? `(selector: ${el.selector})` : '';
    if (!matches.filter) { // it might be an array of dom elements
        matches = $(matches);
    }

    var visibleMatches = matches.filter(':visible');
    if (options.first) {
        if (visibleMatches.length === 1) {
            throw new Error(`There should be more than one visible target ${selectorMsg}.  If` +
                ' you are sure that there is exactly one target, please use the ' +
                'click function instead of the clickFirst function');
        }
        visibleMatches = visibleMatches.first();
    } else if (options.last) {
        if (visibleMatches.length === 1) {
            throw new Error(`There should be more than one visible target ${selectorMsg}.  If` +
                ' you are sure that there is exactly one target, please use the ' +
                'click function instead of the clickLast function');
        }
        visibleMatches = visibleMatches.last();
    }
    if (visibleMatches.length === 0 && matches.length > 0) {
        throw new Error(`Element to click on is not visible ${selectorMsg}`);
    } else if (visibleMatches.length !== 1) {
        throw new Error(`Found ${visibleMatches.length} elements to click on, instead of 1 ${selectorMsg}`);
    }
    visibleMatches.click();
}

/**
 * Click on the first element of a list of elements.  Note that if the list has
 * only one visible element, we trigger an error. In that case, it is better to
 * use the click helper instead.
 *
 * @param {string|NodeList|jQuery} el (if string: it is a (jquery) selector)
 */
function clickFirst(el) {
    click(el, {first: true});
}

/**
 * Click on the last element of a list of elements.  Note that if the list has
 * only one visible element, we trigger an error. In that case, it is better to
 * use the click helper instead.
 *
 * @param {string|NodeList|jQuery} el
 */
function clickLast(el) {
    click(el, {last: true});
}

return {
    triggerKeypressEvent: triggerKeypressEvent,
    triggerMouseEvent: triggerMouseEvent,
    triggerPositionalMouseEvent: triggerPositionalMouseEvent,
    dragAndDrop: dragAndDrop,
    openDatepicker: openDatepicker,
    click: click,
    clickFirst: clickFirst,
    clickLast: clickLast,
};

});
