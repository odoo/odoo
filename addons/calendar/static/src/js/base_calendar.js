odoo.define('base_calendar.base_calendar', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');
var fieldRegistry = require('web.field_registry');
var relationalFields = require('web.relational_fields');

const FieldMany2ManyTagsAvatar = relationalFields.FieldMany2ManyTagsAvatar;

BasicModel.include({
    /**
     * @private
     * @param {Object} record
     * @param {string} fieldName
     * @returns {Promise}
     */
    _fetchSpecialAttendeeStatus: function (record, fieldName) {
        var context = record.getContext({fieldName: fieldName});
        var attendeeIDs = record.data[fieldName] ? this.localData[record.data[fieldName]].res_ids : [];
        var meetingID = _.isNumber(record.res_id) ? record.res_id : false;
        return this._rpc({
            model: 'res.partner',
            method: 'get_attendee_detail',
            args: [attendeeIDs, meetingID],
            context: context,
        }).then(function (result) {
            return _.map(result, function (d) {
                return _.object(['id', 'display_name', 'status', 'color'], d);
            });
        });
    },
});

const Many2ManyAttendee = FieldMany2ManyTagsAvatar.extend({
    // as this widget is model dependant (rpc on res.partner), use it in another
    // context probably won't work
    // supportedFieldTypes: ['many2many'],
    tag_template: "Many2ManyAttendeeTag",
    specialData: "_fetchSpecialAttendeeStatus",

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _getRenderTagsContext: function () {
        var result = this._super.apply(this, arguments);
        result.attendeesData = this.record.specialData.partner_ids;
        return result;
    },
});

fieldRegistry.add('many2manyattendee', Many2ManyAttendee);

});
