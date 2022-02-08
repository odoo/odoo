
odoo.define('web_tour.RunningTourActionHelper', function (require) {
"use strict";

var core = require('web.core');
var utils = require('web_tour.utils');
var Tip = require('web_tour.Tip');

var get_first_visible_element = utils.get_first_visible_element;
var get_jquery_element_from_selector = utils.get_jquery_element_from_selector;

var RunningTourActionHelper = core.Class.extend({
    init: function (tip_widget) {
        this.tip_widget = tip_widget;
    },
    click: function (element) {
        this._click(this._get_action_values(element));
    },
    dblclick: function (element) {
        this._click(this._get_action_values(element), 2);
    },
    tripleclick: function (element) {
        this._click(this._get_action_values(element), 3);
    },
    clicknoleave: function (element) {
        this._click(this._get_action_values(element), 1, false);
    },
    text: function (text, element) {
        this._text(this._get_action_values(element), text);
    },
    text_blur: function (text, element) {
        this._text_blur(this._get_action_values(element), text);
    },
    drag_and_drop: function (to, element) {
        this._drag_and_drop(this._get_action_values(element), to);
    },
    keydown: function (keyCodes, element) {
        this._keydown(this._get_action_values(element), keyCodes.split(/[,\s]+/));
    },
    auto: function (element) {
        var values = this._get_action_values(element);
        if (values.consume_event === "input") {
            this._text(values);
        } else {
            this._click(values);
        }
    },
    _get_action_values: function (element) {
        var $e = get_jquery_element_from_selector(element);
        var $element = element ? get_first_visible_element($e) : this.tip_widget.$anchor;
        if ($element.length === 0) {
            $element = $e.first();
        }
        var consume_event = element ? Tip.getConsumeEventType($element) : this.tip_widget.consume_event;
        return {
            $element: $element,
            consume_event: consume_event,
        };
    },
    _click: function (values, nb, leave) {
        trigger_mouse_event(values.$element, "mouseover");
        values.$element.trigger("mouseenter");
        for (var i = 1 ; i <= (nb || 1) ; i++) {
            trigger_mouse_event(values.$element, "mousedown");
            trigger_mouse_event(values.$element, "mouseup");
            trigger_mouse_event(values.$element, "click", i);
            if (i % 2 === 0) {
                trigger_mouse_event(values.$element, "dblclick");
            }
        }
        if (leave !== false) {
            trigger_mouse_event(values.$element, "mouseout");
            values.$element.trigger("mouseleave");
        }

        function trigger_mouse_event($element, type, count) {
            var e = document.createEvent("MouseEvents");
            e.initMouseEvent(type, true, true, window, count || 0, 0, 0, 0, 0, false, false, false, false, 0, $element[0]);
            $element[0].dispatchEvent(e);
        }
    },
    _text: function (values, text) {
        this._click(values);

        text = text || "Test";
        if (values.consume_event === "input") {
            values.$element
                .trigger({ type: 'keydown', key: text[text.length - 1] })
                .val(text)
                .trigger({ type: 'keyup', key: text[text.length - 1] });
            values.$element[0].dispatchEvent(new InputEvent('input', {
                bubbles: true,
            }));
        } else if (values.$element.is("select")) {
            var $options = values.$element.children("option");
            $options.prop("selected", false).removeProp("selected");
            var $selectedOption = $options.filter(function () { return $(this).val() === text; });
            if ($selectedOption.length === 0) {
                $selectedOption = $options.filter(function () { return $(this).text().trim() === text; });
            }
            $selectedOption.prop("selected", true);
            this._click(values);
        } else {
            values.$element.focusIn();
            values.$element.trigger($.Event( "keydown", {key: '_', keyCode: 95}));
            values.$element.text(text).trigger("input");
            values.$element.focusInEnd();
            values.$element.trigger($.Event( "keyup", {key: '_', keyCode: 95}));
        }
        values.$element.trigger("change");
    },
    _text_blur: function (values, text) {
        this._text(values, text);
        values.$element.trigger('focusout');
        values.$element.trigger('blur');
    },
    _drag_and_drop: function (values, to) {
        var $to;
        var elementCenter = values.
        $element.offset();
        elementCenter.left += values.$element.outerWidth() / 2;
        elementCenter.top += values.$element.outerHeight() / 2;
        if (to) {
            $to = get_jquery_element_from_selector(to);
        } else {
            $to = $(document.body);
        }

        const calculateCenter = () => {
            const toCenter = $to.offset();

            if (to && to.indexOf('iframe') !== -1) {
                const iFrameOffset = $('iframe').offset();
                toCenter.left += iFrameOffset.left;
                toCenter.top += iFrameOffset.top;
            }
            toCenter.left += $to.outerWidth() / 2;
            toCenter.top += $to.outerHeight() / 2;
            return toCenter;
        };

        values.$element.trigger($.Event("mouseenter"));
        values.$element.trigger($.Event("mousedown", {which: 1, pageX: elementCenter.left, pageY: elementCenter.top}));
        // Some tests depends on elements present only when the element to drag
        // start to move while some other tests break while moving.
        if (!$to.length) {
            values.$element.trigger($.Event("mousemove", {which: 1, pageX: elementCenter.left + 1, pageY: elementCenter.top}));
            $to = get_jquery_element_from_selector(to);
        }

        let toCenter = calculateCenter();
        values.$element.trigger($.Event("mousemove", {which: 1, pageX: toCenter.left, pageY: toCenter.top}));
        // Recalculate the center as the mousemove might have made the element bigger.
        toCenter = calculateCenter();
        values.$element.trigger($.Event("mouseup", {which: 1, pageX: toCenter.left, pageY: toCenter.top}));
     },
    _keydown: function (values, keyCodes) {
        while (keyCodes.length) {
            const eventOptions = {};
            const keyCode = keyCodes.shift();
            let insertedText = null;
            if (isNaN(keyCode)) {
                eventOptions.key = keyCode;
            } else {
                const code = parseInt(keyCode, 10);
                eventOptions.keyCode = code;
                eventOptions.which = code;
                if (
                    code === 32 || // spacebar
                    (code > 47 && code < 58) || // number keys
                    (code > 64 && code < 91) || // letter keys
                    (code > 95 && code < 112) || // numpad keys
                    (code > 185 && code < 193) || // ;=,-./` (in order)
                    (code > 218 && code < 223) // [\]' (in order))
                ) {
                    insertedText = String.fromCharCode(code);
                }
            }
            values.$element.trigger(Object.assign({ type: "keydown" }, eventOptions));
            if (insertedText) {
                document.execCommand("insertText", 0, insertedText);
            }
            values.$element.trigger(Object.assign({ type: "keyup" }, eventOptions));
        }
    },
});

return RunningTourActionHelper;
});
