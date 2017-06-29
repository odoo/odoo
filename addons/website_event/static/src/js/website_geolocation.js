odoo.define('website_event.geolocation', function (require) {
'use strict';

var sAnimation = require('website.content.snippets.animation');

sAnimation.registry.visitor = sAnimation.Class.extend({
    selector: '.oe_country_events',

    /**
     * @override
     */
    start: function () {
        var defs = [this._super.apply(this, arguments)];
        var self = this;
        defs.push(this._rpc({route: '/event/get_country_event_list'}).then(function (data) {
            if (data) {
                self.$('.country_events_list').replaceWith(data);
            }
        }));
        return $.when.apply($, defs);
    },
});
});
