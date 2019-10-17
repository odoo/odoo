odoo.define('website_event.geolocation', function (require) {
'use strict';

var sAnimation = require('website.content.snippets.animation');

sAnimation.registry.visitor = sAnimation.Class.extend({
    selector: ".oe_country_events, .country_events",

    /**
     * @override
     */
    start: function () {
        var defs = [this._super.apply(this, arguments)];
        var self = this;
        var $eventList = this.$('.country_events_list');
        this._originalContent = $eventList[0].outerHTML;
        defs.push(this._rpc({route: '/event/get_country_event_list'}).then(function (data) {
            if (data) {
                self._$loadedContent = $(data);
                $eventList.replaceWith(self._$loadedContent);
            }
        }));
        return $.when.apply($, defs);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        this._$loadedContent.replaceWith(this._originalContent);
    },
});
});
