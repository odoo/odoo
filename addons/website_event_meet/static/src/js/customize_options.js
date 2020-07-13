odoo.define('website_event_meet.set_customize_options', function (require) {
"use strict";

let EventSpecificOptions = require('website_event.set_customize_options').EventSpecificOptions;

EventSpecificOptions.include({
    xmlDependencies: (EventSpecificOptions.prototype.xmlDependencies || [])
        .concat([
            '/website_event_meet/static/src/xml/customize_options.xml',
        ]),

    events: _.extend({}, EventSpecificOptions.prototype.events, {
        'change #display-community': '_onDisplayCommunityChange',
    }),

    start: function () {
        this.$displayCommunityInput = this.$('#display-community');
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onDisplayCommunityChange: function () {
        var checkboxValue = this.$displayCommunityInput.is(':checked');
        this._toggleDisplayCommunity(checkboxValue);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getCheckboxFields: function () {
        var fields = this._super();
        fields = _.union(fields, ['meeting_room_menu']);
        return fields;
    },

    _getCheckboxFieldMatch: function (checkboxField) {
        if (checkboxField === 'meeting_room_menu') {
            return this.$displayCommunityInput;
        }
        return this._super(checkboxField);
    },

    _initCheckboxCallback: function (rpcData) {
        this._super(rpcData);
        if (rpcData[0]['meeting_room_menu']) {
            var submenuInput = this._getCheckboxFieldMatch('meeting_room_menu');
            submenuInput.attr('checked', 'checked');
        }
    },

    _toggleDisplayCommunity: async function (val) {
        await this._rpc({
            model: this.modelName,
            method: 'write',
            args: [[this.eventId], {
                meeting_room_menu: val
            }],
        });

        this._reloadEventPage();
    }

});

});
