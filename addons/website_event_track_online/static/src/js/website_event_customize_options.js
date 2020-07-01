odoo.define('website_event_track_online.set_customize_options', function (require) {
"use strict";

var EventSpecificOptions = require('website_event.set_customize_options').EventSpecificOptions;

EventSpecificOptions.include({
    xmlDependencies: (EventSpecificOptions.prototype.xmlDependencies || [])
        .concat([
            '/website_event_track_online/static/src/xml/website_event_customize_options.xml',
        ]),

    events: _.extend({}, EventSpecificOptions.prototype.events, {
        'change #display-location': '_onDisplayLocationChange',
        'change #display-agenda': '_onDisplayAgendaChange',
    }),

    start: function () {
        this.$displayLocation = this.$('#display-location');
        this.$displayAgenda = this.$('#display-agenda');
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onDisplayLocationChange: function () {
        var checkboxValue = this.$displayLocation.is(':checked');
        this._toggleDisplayLocation(checkboxValue);
    },

    _onDisplayAgendaChange: function () {
        var checkboxValue = this.$displayAgenda.is(':checked');
        this._toggleDisplayAgenda(checkboxValue);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getCheckboxFields: function () {
        var fields = this._super();
        fields = _.union(fields, ['menu_location', 'menu_agenda']);
        return fields;
    },

    _getCheckboxFieldMatch: function (checkboxField) {
        if (checkboxField === 'menu_location') {
            return this.$displayLocation;
        }
        else if (checkboxField === 'menu_agenda') {
            return this.$displayAgenda;
        }
        return this._super(checkboxField);
    },

    _initCheckboxCallback: function (rpcData) {
        this._super(rpcData);
        if (rpcData[0]['menu_location']) {
            var submenuInput = this._getCheckboxFieldMatch('menu_location');
            submenuInput.attr('checked', 'checked');
        }
        if (rpcData[0]['menu_agenda']) {
            var submenuInput = this._getCheckboxFieldMatch('menu_agenda');
            submenuInput.attr('checked', 'checked');
        }
    },

    _toggleDisplayLocation: function (val) {
        var self = this;
        this._rpc({
            model: this.modelName,
            method: 'toggle_menu_location',
            args: [[this.eventId], val],
        }).then(function () {
            self._reloadEventPage();
        });
    },

    _toggleDisplayAgenda: function (val) {
        var self = this;
        this._rpc({
            model: this.modelName,
            method: 'toggle_menu_agenda',
            args: [[this.eventId], val],
        }).then(function () {
            self._reloadEventPage();
        });
    },
});

});
