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

    _initCheckbox: async function () {
        let data = await this._rpc({
            model: this.modelName,
            method: 'read',
            args: [[this.eventId], ['website_url', 'website_meeting_room']],
        });

        if (data[0]['website_meeting_room']) {
            this.$displayCommunityInput.attr('checked', 'checked');
        }
        this.eventUrl = data[0]['website_url'];
    },

    _onDisplayCommunityChange: async function () {
        let checkboxValue = this.$displayCommunityInput.is(':checked');
        await this._toggleDisplayCommunity(checkboxValue);
    },

    _toggleDisplayCommunity: async function (val) {
        await this._rpc({
            model: this.modelName,
            method: 'write',
            args: [[this.eventId], {website_meeting_room: val}],
        });

        this._reloadEventPage();
    }

});

});
