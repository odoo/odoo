odoo.define('web.Priority', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var Priority = Widget.extend({
    template: "Priority",
    events: {
        'mouseover > a': function(e) {
            clearTimeout(this.hover_timer);

            this.$stars.removeClass('fa-star-o').addClass('fa-star');
            $(e.target).nextAll().removeClass('fa-star').addClass('fa-star-o');
        },
        'mouseout > a': function(e) {
            clearTimeout(this.hover_timer);

            var self = this;
            this.hover_timer = setTimeout(function() {
                self._render_value();
            }, 200);
        },
        'click > a': function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            var old_value = this.value;
            this.value = String($(e.target).data('value'));
            if(old_value === this.value) {
                this.value = this.empty_value;
            }

            this._render_value();
            this.trigger('update', {value: this.value});
        },
    },
    init: function(parent, options) {
        this._super.apply(this, arguments);

        options = _.defaults(options || {}, {
            readonly: true,
            value: 0,
            values: [
                [0, _t("Normal")],
                [1, _t("Low")],
                [2, _t("High")],
                [3, _t("Very High")]
            ],
        });

        this.readonly = options.readonly;
        this.value = options.value;
        this.values = options.values;
        this.empty_value = this.values[0][0];
    },
    start: function() {
        this._render_value();
        return this._super();
    },
    set_value: function(value) {
        this.value = value;
        this._render_value();
    },
    _render_value: function() {
        var self = this;
        var index_value = this.value ? _.findIndex(this.values, function (v) {
            return v[0] === self.value;
        }) : 0;
        this.$stars = this.$('.o_priority_star');
        this.$stars.each(function(i, el) {
            var $star = $(el);
            $star.toggleClass('fa-star', (i+1 <= index_value))
                 .toggleClass('fa-star-o', (i+1 > index_value));
        });
    },
});

return Priority;

});
