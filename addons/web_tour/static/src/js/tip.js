odoo.define('web_tour.Tip', function(require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var Widget = require('web.Widget');
var _t = core._t;

var Tip = Widget.extend({
    template: "Tip",
    xmlDependencies: ['/web_tour/static/src/xml/tip.xml'],
    events: {
        click: '_onTipClicked',
        mouseenter: "_to_info_mode",
        mouseleave: "_to_bubble_mode",
    },
    /**
     * @param {Widget} parent
     * @param {Object} [info] description of the tip, containing the following keys:
     *  - content [String] the html content of the tip
     *  - event_handlers [Object] description of optional event handlers to bind to the tip:
     *    - event [String] the event name
     *    - selector [String] the jQuery selector on which the event should be bound
     *    - handler [function] the handler
     *  - position [String] tip's position ('top', 'right', 'left' or 'bottom'), default 'right'
     *  - width [int] the width in px of the tip when opened, default 270
     *  - space [int] space in px between anchor and tip, default 10
     *  - overlay [Object] x and y values for the number of pixels the mouseout detection area
     *    overlaps the opened tip, default {x: 50, y: 50}
     */
    init: function(parent, info) {
        this._super(parent);
        this.info = _.defaults(info, {
            position: "right",
            width: 270,
            space: 10,
            overlay: {
                x: 50,
                y: 50,
            },
        });
        this.position = {
            top: "50%",
            left: "50%",
        };
    },
    /**
     * @param {jQuery} $anchor the node on which the tip should be placed
     */
    attach_to: function ($anchor) {
        this.$anchor = $anchor;
        this.$ideal_location = this._get_ideal_location();

        var position = this.$ideal_location.css("position");
        if (position === "static" || position === "relative") {
            this.$ideal_location.addClass("o_tooltip_parent");
        }

        return this.appendTo(this.$ideal_location);
    },
    start: function() {
        this.$tooltip_overlay = this.$(".o_tooltip_overlay");
        this.$tooltip_content = this.$(".o_tooltip_content");
        this.init_width = this.$el.innerWidth();
        this.init_height = this.$el.innerHeight();
        this.double_border_width = this.$el.outerWidth() - this.init_width;
        this.content_width = this.$tooltip_content.outerWidth(true);
        this.content_height = this.$tooltip_content.outerHeight(true);
        this.$window = $(window);

        this.$tooltip_content.css({
            width: "100%",
            height: "100%",
        });

        _.each(this.info.event_handlers, (function(data) {
            this.$tooltip_content.on(data.event, data.selector, data.handler);
        }).bind(this));
        this._bind_anchor_events();

        this._reposition();
        this.$el.css("opacity", 1);
        core.bus.on("resize", this, _.debounce(function () {
            if (this.tip_opened) {
                this._to_bubble_mode(true);
            }
            this._reposition();
        }, 500));

        this.$el.on("transitionend oTransitionEnd webkitTransitionEnd", (function () {
            if (!this.tip_opened && this.$el.parent()[0] === document.body) {
                this.$el.detach();
                this.$el.css(this.position);
                this.$el.appendTo(this.$ideal_location);
            }
        }).bind(this));

        return this._super.apply(this, arguments);
    },
    destroy: function () {
        this._unbind_anchor_events();
        clearTimeout(this.timerIn);
        clearTimeout(this.timerOut);

        // Do not remove the parent class if it contains other tooltips
        if (this.$ideal_location.children(".o_tooltip").not(this.$el[0]).length === 0) {
            this.$ideal_location.removeClass("o_tooltip_parent");
        }

        return this._super.apply(this, arguments);
    },
    update: function ($anchor) {
        if (!$anchor.is(this.$anchor)) {
            this._unbind_anchor_events();
            this.$anchor = $anchor;
            this.$ideal_location = this._get_ideal_location();
            if (this.$el.parent()[0] !== document.body) {
                this.$el.appendTo(this.$ideal_location);
            }
            this._bind_anchor_events();
        }
        this._reposition();
    },
    _get_ideal_location: function () {
        var $location = this.$anchor;
        if ($location.is("html,body")) {
            return $(document.body);
        }

        var o;
        var p;
        do {
            $location = $location.parent();
            o = $location.css("overflow");
            p = $location.css("position");
        } while (
            $location.hasClass('dropdown-menu') ||
            (
                (o === "visible" || o === "hidden") &&
                p !== "fixed" &&
                $location[0].tagName.toUpperCase() !== 'BODY'
            )
        );

        return $location;
    },
    _reposition: function () {
        if (this.tip_opened) return;
        this.$el.removeClass("o_animated");

        // Reverse left/right position if direction is right to left
        var appendAt = this.info.position;
        if (_t.database.parameters.direction === 'rtl') {
            appendAt = appendAt === 'right' ? 'left': 'right';
        }
        this.$el.position({
            my: this._get_spaced_inverted_position(appendAt),
            at: appendAt,
            of: this.$anchor,
            collision: "none",
        });

        // Reverse overlay if direction is right to left
        var positionRight = _t.database.parameters.direction === 'rtl' ? "right" : "left";
        var positionLeft = _t.database.parameters.direction === 'rtl' ? "left" : "right";
        var offset = this.$el.offset();
        this.$tooltip_overlay.css({
            top: -Math.min((this.info.position === "bottom" ? this.info.space : this.info.overlay.y), offset.top),
            right: -Math.min((this.info.position === positionRight ? this.info.space : this.info.overlay.x), this.$window.width() - (offset.left + this.init_width + this.double_border_width)),
            bottom: -Math.min((this.info.position === "top" ? this.info.space : this.info.overlay.y), this.$window.height() - (offset.top + this.init_height + this.double_border_width)),
            left: -Math.min((this.info.position === positionLeft ? this.info.space : this.info.overlay.x), offset.left),
        });

        this.position = this.$el.position();

        this.$el.addClass("o_animated");
    },
    _bind_anchor_events: function () {
        this.consume_event = Tip.getConsumeEventType(this.$anchor);
        this.$anchor.on(this.consume_event + ".anchor", (function (e) {
            if (e.type !== "mousedown" || e.which === 1) { // only left click
                this.trigger("tip_consumed");
                this._unbind_anchor_events();
            }
        }).bind(this));
        this.$anchor.on('mouseenter.anchor', this._to_info_mode.bind(this));
        this.$anchor.on('mouseleave.anchor', this._to_bubble_mode.bind(this));
    },
    _unbind_anchor_events: function () {
        this.$anchor.off(".anchor");
    },
    _get_spaced_inverted_position: function (position) {
        if (position === "right") return "left+" + this.info.space;
        if (position === "left") return "right-" + this.info.space;
        if (position === "bottom") return "top+" + this.info.space;
        return "bottom-" + this.info.space;
    },
    _to_info_mode: function (force) {
        if (this.timerOut !== undefined) {
            clearTimeout(this.timerOut);
            this.timerOut = undefined;
            return;
        }
        if (this.tip_opened) {
            return;
        }

        if (force === true) {
            this._build_info_mode();
        } else {
            this.timerIn = setTimeout(this._build_info_mode.bind(this), 100);
        }
    },
    _build_info_mode: function () {
        clearTimeout(this.timerIn);
        this.timerIn = undefined;

        this.tip_opened = true;

        var offset = this.$el.offset();

        if (this.$el.parent()[0] !== document.body) {
            this.$el.detach();
            this.$el.css(offset);
            this.$el.appendTo(document.body);
        }

        var mbLeft = 0;
        var mbTop = 0;
        var overflow = false;
        var posVertical = (this.info.position === "top" || this.info.position === "bottom");
        if (posVertical) {
            overflow = (offset.left + this.content_width + this.double_border_width + this.info.overlay.x > this.$window.width());
        } else {
            overflow = (offset.top + this.content_height + this.double_border_width + this.info.overlay.y > this.$window.height());
        }
        if (posVertical && overflow || this.info.position === "left" || (_t.database.parameters.direction === 'rtl' && this.info.position == "right")) {
            mbLeft -= (this.content_width - this.init_width);
        }
        if (!posVertical && overflow || this.info.position === "top") {
            mbTop -= (this.content_height - this.init_height);
        }

        this.$el.toggleClass("inverse", overflow);
        this.$el.removeClass("o_animated").addClass("active");
        this.$el.css({
            width: this.content_width,
            height: this.content_height,
            "margin-left": mbLeft,
            "margin-top": mbTop,
        });
    },
    _to_bubble_mode: function (force) {
        if (this.timerIn !== undefined) {
            clearTimeout(this.timerIn);
            this.timerIn = undefined;
            return;
        }
        if (!this.tip_opened) {
            return;
        }

        if (force === true) {
            this._build_bubble_mode();
        } else {
            this.timerOut = setTimeout(this._build_bubble_mode.bind(this), 300);
        }
    },
    _build_bubble_mode: function () {
        clearTimeout(this.timerOut);
        this.timerOut = undefined;

        this.tip_opened = false;

        this.$el.removeClass("active").addClass("o_animated");
        this.$el.css({
            width: this.init_width,
            height: this.init_height,
            margin: 0,
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * On touch devices, closes the tip when clicked.
     *
     * @private
     */
    _onTipClicked: function () {
        if (config.device.touch && this.tip_opened) {
            this._to_bubble_mode();
        }
    },
});

Tip.getConsumeEventType = function ($element) {
    if ($element.is("textarea") || $element.filter("input").is(function () {
        var type = $(this).attr("type");
        return !type || !!type.match(/^(email|number|password|search|tel|text|url)$/);
    })) {
        return "input";
    }
    return "mousedown";
};

return Tip;

});
