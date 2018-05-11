odoo.define('web.Banner', function (require) {
"use strict";
var Widget = require('web.Widget');
var Banner = Widget.extend({
    events: {
        'click a, button': '_onActionClicked'
    },
    /**
     * @constructor
     * @override
     * @param {Widget} parent
     * @param {String} html
     */
    init: function (parent, html) {
        this._super.apply(this, arguments);
        this.html = html;
    },
    /**
     * @override
     * @returns {Deferred}
     */
    start: function () {
        this.$el.html(this.html);
        return $.when();
    },
    /**
     * Banner <a> and <button> can have data-route or data-model and
     * data-method attributes to fetch the corresponding action from
     * the backend and `do` them
     *
     * @param {OdooEvent} ev
     */
    _onActionClicked: function (ev) {
        ev.stopPropagation();
        var $target = $(ev.currentTarget);
        var self = this;

        var route = $target.data('route');
        var model = $target.data('model');
        var method = $target.data('method');
        var id = $target.data('id');

        if (route === undefined && (method === undefined || model === undefined)) {
            console.warn("no endpoint provided on banner ", ev.currentTarget);
            return false;
        }
        self._rpc({
            route: route,
            model: model,
            method: method,
            args: [id],
        }).then(function (action) {
            if (action !== undefined) {
                self.do_action(action, {
                    on_close: function () {
                        self.trigger_up('reload');
                    }
                });
            } else {
                self.trigger_up('reload');
            }
        });
    },
});
return Banner;
});
