odoo.define('website_event.set_customize_options', function (require) {
"use strict";

var CustomizeMenu = require('website.customizeMenu');
var publicWidget = require('web.public.widget');

var EventSpecificOptions = publicWidget.Widget.extend({
    template: 'website_event.customize_options',
    xmlDependencies: ['/website_event/static/src/xml/customize_options.xml'],
    events: {
        'change #display-website-menu': '_onDisplaySubmenuChange',
    },

    /**
     * @override
     */
    start: function () {
        this.$submenuInput = this.$('#display-website-menu');
        this.modelName = this._getEventObject().model;
        this.eventId = this._getEventObject().id;
        this._initCheckbox();
    },

    _initCheckbox: function () {
        this._rpc({
            model: this.modelName,
            method: 'read',
            args: [[this.eventId], ['website_menu', 'website_url']],
        }).then((data) => {
            if (data[0]['website_menu']) {
                this.$submenuInput.attr('checked', 'checked');
            }
            this.eventUrl = data[0]['website_url'];
        });
    },

    _onDisplaySubmenuChange: function (ev) {
        var checkboxValue = this.$submenuInput.is(':checked');
        this._toggleSubmenuDisplay(checkboxValue);
    },

    _toggleSubmenuDisplay: function (val) {
        var self = this;
        this._rpc({
            model: this.modelName,
            method: 'toggle_website_menu',
            args: [[this.eventId], val],
        }).then(function () {
            self._reloadEventPage();
        });
    },

    _reloadEventPage: function () {
        window.location = this.eventUrl;
    },

    _getEventObject: function() {
        var repr = $('html').data('main-object');
        var m = repr.match(/(.+)\((\d+),(.*)\)/);
        return {
            model: m[1],
            id: m[2] | 0,
        };
    }

});

CustomizeMenu.include({
    _getEventObject: function() {
        var repr = $('html').data('main-object');
        var m = repr.match(/(.+)\((\d+),(.*)\)/);
        return {
            model: m[1],
            id: m[2] | 0,
        };
    },

    _loadCustomizeOptions: function () {
        var self = this;
        var def = this._super.apply(this, arguments);
        return def.then(function () {
            if (!self.__eventOptionsLoaded && self._getEventObject().model === 'event.event') {
                self.__eventOptionsLoaded = true;
                self.eventOptions = new EventSpecificOptions(self);
                self.eventOptions.insertAfter(self.$el.find('.dropdown-divider:first()'));
            }
        });
    },
});

return {
    EventSpecificOptions: EventSpecificOptions,
};

});
