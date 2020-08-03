odoo.define('website_event_meet.set_customize_options', function (require) {
"use strict";

let EventSpecificOptions = require('website_event.set_customize_options').EventSpecificOptions;

EventSpecificOptions.include({
    xmlDependencies: (EventSpecificOptions.prototype.xmlDependencies || [])
        .concat([
            '/website_event_meet/static/src/xml/customize_options.xml',
        ]),

    events: _.extend({}, EventSpecificOptions.prototype.events, {
        'change #allow-room-creation': '_onAllowRoomCreationChange',
    }),

    start: function () {
        this.$allowRoomCreationInput = this.$('#allow-room-creation');
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onAllowRoomCreationChange: function () {
        let checkboxValue = this.$allowRoomCreationInput.is(':checked');
        this._toggleAllowRoomCreation(checkboxValue);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getCheckboxFields: function () {
        let fields = this._super();
        fields = _.union(fields, ['meeting_room_allow_creation']);
        return fields;
    },

    _getCheckboxFieldMatch: function (checkboxField) {
        if (checkboxField === 'meeting_room_allow_creation') {
            return this.$allowRoomCreationInput;
        }
        return this._super(checkboxField);
    },

    _initCheckboxCallback: function (rpcData) {
        this._super(rpcData);
        if (rpcData[0]['meeting_room_allow_creation']) {
            let submenuInput = this._getCheckboxFieldMatch('meeting_room_allow_creation');
            submenuInput.attr('checked', 'checked');
        }
    },

    _toggleAllowRoomCreation: async function (val) {
        await this._rpc({
            model: this.modelName,
            method: 'write',
            args: [[this.eventId], {
                meeting_room_allow_creation: val
            }],
        });

        this._reloadEventPage();
    },

});

});
