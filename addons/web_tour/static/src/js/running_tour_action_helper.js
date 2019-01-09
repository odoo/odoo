
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
            values.$element.trigger("keydown").val(text).trigger("keyup").trigger("input");
        } else if (values.$element.is("select")) {
            var $options = values.$element.children("option");
            $options.prop("selected", false).removeProp("selected");
            var $selectedOption = $options.filter(function () { return $(this).val() === text; });
            if ($selectedOption.length === 0) {
                $selectedOption = $options.filter(function () { return $(this).text() === text; });
            }
            $selectedOption.prop("selected", true);
            this._click(values);
        } else {
            values.$element.text(text);
        }
        values.$element.trigger("change");
    },
    _drag_and_drop: function (values, to) {
        var $to;
        if (to) {
            $to = get_jquery_element_from_selector(to);
        } else {
            $to = $(document.body);
        }
        var elementCenter = values.$element.offset();
        elementCenter.left += values.$element.outerWidth()/2;
        elementCenter.top += values.$element.outerHeight()/2;

        var toCenter = $to.offset();

        if (to && to.indexOf('iframe') !== -1) {
            var iFrameOffset = $('iframe').offset();
            toCenter.left += iFrameOffset.left;
            toCenter.top += iFrameOffset.top;
        }
        toCenter.left += $to.outerWidth()/2;
        toCenter.top += $to.outerHeight()/2;

        values.$element.trigger($.Event("mouseenter"));
        values.$element.trigger($.Event("mousedown", {which: 1, pageX: elementCenter.left, pageY: elementCenter.top}));
        values.$element.trigger($.Event("mousemove", {which: 1, pageX: toCenter.left, pageY: toCenter.top}));
        values.$element.trigger($.Event("mouseup", {which: 1, pageX: toCenter.left, pageY: toCenter.top}));
     },
    _keydown: function (values, keyCodes) {
        while (keyCodes.length) {
            var keyCode = +keyCodes.shift();
            values.$element.trigger({type: "keydown", keyCode: keyCode});
            if ((keyCode > 47 && keyCode < 58) // number keys
                || keyCode === 32 // spacebar
                || (keyCode > 64 && keyCode < 91) // letter keys
                || (keyCode > 95 && keyCode < 112) // numpad keys
                || (keyCode > 185 && keyCode < 193) // ;=,-./` (in order)
                || (keyCode > 218 && keyCode < 223)) {   // [\]' (in order))
                document.execCommand("insertText", 0, String.fromCharCode(keyCode));
            }
            values.$element.trigger({type: "keyup", keyCode: keyCode});
        }
    },
});

return RunningTourActionHelper;
});
