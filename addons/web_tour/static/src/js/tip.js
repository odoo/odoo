odoo.define('web_tour.Tip', function(require) {
"use strict";

var Widget = require('web.Widget');

return Widget.extend({
    template: "Tip",
    init: function(parent, $anchor, info) {
        this._super(parent);
        this.$anchor = $anchor;
        this.info = _.defaults(info, {
            position: 'right',
        });
        this.consumed = false;
    },
    start: function() {
        this.$breathing = this.$('.o_breathing');
        this.$breathing.on('mouseenter', this._to_info_mode.bind(this));
        this._bind_anchor_events();
        this._reposition();
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
        this.$breathing.position({
            my: this._invert_position(this.info.position),
            at: this.info.position,
            of: this.$anchor,
            collision: 'fit',
        });
    },
    _bind_anchor_events: function () {
        var self = this;
        this.$anchor.on('mouseenter', this._to_info_mode.bind(this));
        this.$anchor.on('mouseleave', this._to_bubble_mode.bind(this));
        this.$anchor.on(this.$anchor.is('input,textarea') ? 'change' : 'mousedown', function () {
            if (self.consumed) return;
            self.consumed = true;
            self.trigger('tip_consumed');
        });
    },
    _invert_position: function (position) {
        if (position === "right") return "left";
        if (position === "left") return "right";
        if (position === "bottom") return "top";
        return "bottom";
    },
    _to_info_mode: function() {
        this.$breathing.fadeOut(300);
        this.$popover = this.$popover || this.$anchor.popover({
            content: this.info.content + (this.info.extra_content || ''),
            html: true,
            animation: false,
            container: this.$el,
            placement: this.info.position,
        });
        this.$popover.popover('show');
        this.$('.popover').on('mouseleave.to_bubble_mode', this._to_bubble_mode.bind(this));
        this.$('.popover').on('click', this.trigger.bind(this, 'popover_clicked'));
    },
    _to_bubble_mode: function () {
        this.$breathing.fadeIn(300);
        if (this.$popover) {
            this.$popover.popover('hide');
            this.$('.popover').off('mouseleave.to_bubble_mode');
            this.$('.popover').off('click');
        }
    },
});

});
