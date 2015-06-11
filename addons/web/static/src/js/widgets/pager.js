odoo.define('web.Pager', function (require) {
"use strict";

var Widget = require('web.Widget');

var direction = {
    previous: -1,
    next: 1,
};

var Pager = Widget.extend({
    template: "Pager",

    events: {
        'click .o-pager-previous': 'previous',
        'click .o-pager-next': 'next',
    },

    // pager goes from 1 to size (included).
    // current value is current_min (if limit === 1)
    //              or the interval [current_min, current_min + limit[ if limit > 1
    init: function (parent, size, current_min, limit, options) {
        this.state = {
            size: size,
            current_min: current_min,
            limit: limit,
        };
        Object.defineProperty(this.state, 'current_max', {
            get: function() {
                return Math.min(this.current_min + this.limit - 1, this.size);
            }
        });
        this.options = options || {};
        this._super(parent);
    },

    start: function () {
        this.$content = this.$('.o-pager-value');
        this._render();
        return this._super();
    },

    set_state: function (options) {
        _.extend(this.state, options);
        this._render();
    },

    previous: function(e) {
        this._change_selection(direction.previous);
    },

    next: function() {
        this._change_selection(direction.next);
    },

    disable: function() {
        this.$('button').prop("disabled", true);
    },

    enable: function() {
        this.$('button').prop("disabled", false);
    },

    _render: function () {
        var state;
        var size = this.state.size;
        var current_min = this.state.current_min;
        var current_max = this.state.current_max;
        var single_page = 1 === current_min && current_max === size;

        if (size === 0 || (single_page && this.options.single_page_hidden)) {
            this.$el.hide();
        } else {
            this.$el.show();

            if (single_page) {
                this.disable();
            } else {
                this.enable();
            }

            if (this.state.limit === 1) {
                state = "" + current_min + " / " + size;
            } else {
                state = "" + current_min + "-" + current_max + " / " + size;
            }
            this.$content.html(state);
        }
    },

    _change_selection: function (direction) {
        var size = this.state.size;
        var current_min = this.state.current_min;
        var limit = this.state.limit;
        current_min = (current_min + limit*direction);
        if (current_min > size) {
            current_min = 1;
        } else if ((current_min < 1) && (limit === 1)) {
            current_min = size;
        } else if ((current_min < 1) && (limit > 1)) {
            current_min = size - ((size % limit) || limit) + 1;
        }
        this.state.current_min = current_min;
        this.trigger('pager_changed', _.clone(this.state));
        this._render();
    },
});

return Pager;

});