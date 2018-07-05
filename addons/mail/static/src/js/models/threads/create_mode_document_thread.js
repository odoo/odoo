odoo.define('mail.model.CreateModeDocumentThread', function (require) {
"use strict";

var AbstractMessage = require('mail.model.AbstractMessage');
var AbstractThread = require('mail.model.AbstractThread');

var core = require('web.core');
var session = require('web.session');

var _t = core._t;

/**
 * Special document thread that is linked to a new document that is in create
 * mode. This thread only display a single (fake) message which displays the
 * user avatar and the message 'Creating a new record...'.
 *
 * Note: it uses AbstractThread and AbstractMessage, because this is a fake
 * thread which contains a fake message. We do not want to register both of them
 * in the mail service.
 */
var CreateModeDocumentThread = AbstractThread.extend({

    /**
     * @override
     */
    init: function () {
        var params = {
            data: {
                id: '_createModeDocumentThread'
            }
        };

        this._super(params);

        this._messages = this._forgeCreateMessages();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.model.AbstractMessage[]}
     */
    getMessages: function () {
        return this._messages;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Make a fake list of messages to render in create mode.
     * Instead of rendering no messages at all, it displays a single message
     * with body content "Creating a new record".
     *
     * @private
     * @returns {mail.model.AbstractMessage[]} an array containing a single
     *   message 'Creating a new record...'
     */
    _forgeCreateMessages: function () {
        var createMessage = new AbstractMessage(this, {
            id: 0,
            body: _t("<p>Creating a new record...</p>"),
            author_id: [session.partner_id, session.partner_display_name],
        });
        return [createMessage];
    },

});

return CreateModeDocumentThread;

});
