odoo.define('mail.model.MailFailure', function (require) {
"use strict";

var Class = require('web.Class');
var core = require('web.core');
var Mixins = require('web.mixins');
var ServicesMixin = require('web.ServicesMixin');
var time = require('web.time');

var _t = core._t;

var MailFailure = Class.extend(Mixins.EventDispatcherMixin, ServicesMixin, {
    /**
     * @param {mail.Manager} parent
     * @param {Object} data
     * @param {string} data.last_message_date
     * @param {integer} data.message_id
     * @param {string} data.model
     * @param {string} data.model_name
     * @param {string} data.module_icon
     * @param {Array} data.notifications
     * @param {string} data.record_name
     * @param {integer} data.res_id
     * @param {string} data.uuid
     */
    init: function (parent, data) {
        Mixins.EventDispatcherMixin.init.call(this, arguments);
        this.setParent(parent);

        this._documentID = data.res_id;
        this._documentModel = data.model;
        this._lastMessageDate = moment(); // by default: current datetime
        this._messageID = data.message_id;
        this._modelName = data.model_name;
        this._moduleIcon = data.module_icon;
        this._notifications = data.notifications;
        this._recordName = data.record_name;
        this._uuid = data.uuid;

        if (data.last_message_date) {
            this._lastMessageDate = moment(time.str_to_datetime(data.last_message_date));
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get the document model that this mail failure is linked to.
     *
     * @returns {string}
     */
    getDocumentModel: function () {
        return this._documentModel;
    },
    /**
     * Get the document ID that this mail failure is linked to.
     *
     * @returns {integer}
     */
    getDocumentID: function () {
        return this._documentID;
    },
    /**
     * Get the ID of the message that this mail failure is related to.
     *
     * @returns {integer}
     */
    getMessageID: function () {
        return this._messageID;
    },
    /**
     * Get a valid object for the 'mail.preview' template
     *
     * @returns {Object}
     */
    getPreview: function () {
        var preview = {
            body: _t("An error occured when sending an email"),
            date: this._lastMessageDate,
            documentID: this._documentID,
            documentModel: this._documentModel,
            id: 'mail_failure',
            imageSRC: this._moduleIcon,
            title: this._modelName,
        };
        return preview;
    },
    /**
     * Tell whether the mail failure comes from a message in a document.
     *
     * @returns {boolean}
     */
    isLinkedToDocument: function () {
        return !!(this._documentModel && this._documentID);
    },
});

return MailFailure;

});
