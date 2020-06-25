odoo.define('website_event_track_exhibitor.set_customize_options', function (require) {
"use strict";

var EventSpecificOptions = require('website_event.set_customize_options').EventSpecificOptions;

EventSpecificOptions.include({
    xmlDependencies: (EventSpecificOptions.prototype.xmlDependencies || [])
        .concat([
            '/website_event_track_exhibitor/static/src/xml/website_event_customize_options.xml',
        ]),

    events: _.extend({}, EventSpecificOptions.prototype.events, {
        'change #display-showcase-exhibitors': '_onShowcaseExhibitorsChange',
    }),

    start: function () {
        this.$showcaseExhibitorsInput = this.$('#display-showcase-exhibitors');
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onShowcaseExhibitorsChange: function () {
        var checkboxValue = this.$showcaseExhibitorsInput.is(':checked');
        this._toggleShowcaseExhibitors(checkboxValue);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getCheckboxFields: function () {
        var fields = this._super();
        fields = _.union(fields, ['menu_exhibitor']);
        return fields;
    },

    _getCheckboxFieldMatch: function (checkboxField) {
        if (checkboxField === 'menu_exhibitor') {
            return this.$showcaseExhibitorsInput;
        }
        return this._super(checkboxField);
    },

    _initCheckboxCallback: function (rpcData) {
        this._super(rpcData);
        if (rpcData[0]['menu_exhibitor']) {
            var submenuInput = this._getCheckboxFieldMatch('menu_exhibitor');
            submenuInput.attr('checked', 'checked');
        }
    },

    _toggleShowcaseExhibitors: function (val) {
        var self = this;
        this._rpc({
            model: this.modelName,
            method: 'toggle_menu_exhibitor',
            args: [[this.eventId], val],
        }).then(function () {
            self._reloadEventPage();
        });
    },
});

});
