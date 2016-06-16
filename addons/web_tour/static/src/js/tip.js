odoo.define('web_tour.Tip', function(require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');

return Widget.extend({
    template: "Tip",
    events: {
        mouseenter: "_to_info_mode",
        mouseleave: "_to_bubble_mode",
    },
    /**
     * @param {$anchor} [JQuery] the node on which the tip should be placed
     * @param {info} [Object] description of the tip, containing the following keys:
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
    init: function(parent, $anchor, info) {
        this._super(parent);
        this.$anchor = $anchor;
        this.info = _.defaults(info, {
            position: "right",
            width: 270,
            space: 10,
            overlay: {
                x: 50,
                y: 50,
            },
        });
    },
    start: function() {
        this.$tooltip_overlay = this.$(".o_tooltip_overlay");
        this.$tooltip_content = this.$(".o_tooltip_content");
        this.init_width = this.$el.innerWidth();
        this.init_height = this.$el.innerHeight();
        this.border_width = this.$el.outerWidth() - this.init_width;
        this.content_width = this.$tooltip_content.outerWidth(true);
        this.content_height = this.$tooltip_content.outerHeight(true);
        this.$window = $(window);

        _.each(this.info.event_handlers, (function(data) {
            this.$tooltip_content.on(data.event, data.selector, data.handler);
        }).bind(this));
        this._bind_anchor_events();

        this._reposition();
        core.bus.on('scroll resize', this, function() {
            if (this.tip_opened) {
                this._to_bubble_mode();
            }
            this._reposition();
        });
        this.$tooltip_content.css({
            width: "100%",
            height: "100%",
        });

        return this._super.apply(this, arguments);
    },
    update: function($anchor) {
        if (!$anchor.is(this.$anchor)) {
            this.$anchor.off();
            this.$anchor = $anchor;
            this._bind_anchor_events();
        }
        this._reposition();
    },
    _reposition: function() {
        if (this.tip_opened) return;
        this.$el.removeClass("o_animated");

        this.$el.position({
            my: this._get_spaced_inverted_position(this.info.position),
            at: this.info.position,
            of: this.$anchor,
            collision: "none",
        });

        var offset = this.$el.offset();
        offset.left += this.border_width;
        offset.top += this.border_width;
        this.$tooltip_overlay.css({
            top: -Math.min((this.info.position === "bottom" ? this.info.space : this.info.overlay.y), offset.top),
            right: -Math.min((this.info.position === "left" ? this.info.space : this.info.overlay.x), this.$window.width() - (offset.left + this.init_width)),
            bottom: -Math.min((this.info.position === "top" ? this.info.space : this.info.overlay.y), this.$window.height() - (offset.top + this.init_height)),
            left: -Math.min((this.info.position === "right" ? this.info.space : this.info.overlay.x), offset.left),
        });

        this.$el.addClass("o_animated");
    },
    _bind_anchor_events: function () {
        var consume_event = this.$anchor.is('input,textarea') ? 'change' : 'mousedown';
        this.$anchor.one(consume_event, this.trigger.bind(this, 'tip_consumed'));
        this.$anchor.on('mouseenter', this._to_info_mode.bind(this));
        this.$anchor.on('mouseleave', this._to_bubble_mode.bind(this));
    },
    _get_spaced_inverted_position: function (position) {
        if (position === "right") return "left+" + this.info.space;
        if (position === "left") return "right-" + this.info.space;
        if (position === "bottom") return "top+" + this.info.space;
        return "bottom-" + this.info.space;
    },
    _to_info_mode: function(force) {
        if (this.timerOut !== undefined) {
            clearTimeout(this.timerOut);
            this.timerOut = undefined;
            return;
        }

        if (force === true) {
            this.__to_info_mode();
        } else {
            this.timerIn = setTimeout(this.__to_info_mode.bind(this), 100);
        }
    },
    __to_info_mode: function() {
        clearTimeout(this.timerIn);
        this.timerIn = undefined;

        this.tip_opened = true;

        var offset = this.$el.offset();
        var mbLeft = 0;
        var mbTop = 0;
        var overflow = false;
        var posVertical = (this.info.position === "top" || this.info.position === "bottom");
        if (posVertical) {
            overflow = (offset.left + this.content_width + 2 * this.border_width + this.info.overlay.x > this.$window.width());
        } else {
            overflow = (offset.top + this.content_height + 2 * this.border_width + this.info.overlay.y > this.$window.height());
        }
        if (posVertical && overflow || this.info.position === "left") {
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

        if (force === true) {
            this.__to_bubble_mode();
        } else {
            this.timerOut = setTimeout(this.__to_bubble_mode.bind(this), 300);
        }
    },
    __to_bubble_mode: function() {
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
});
});
