odoo.define('web.FlashMessages', function (require) {
"use strict";

var session = require('web.session');
var Widget = require('web.Widget');

session.on('flash_remove', session, function (e) {
    this.flashes.splice(e.data.index, 1);
});

/**
 * Displays "flash" messages (stored in the session), closing any message
 * will remove it from the current session and any other extant flash
 * instance.
 *
 * @class web.FlashMessages
 */
return Widget.extend({
    'template': 'web.FlashMessages',
    events: {
        'click button.close': '_onClose',
    },
    init: function () {
        this._super.apply(this, arguments);
        // not all tests instantiating discuss fully set up the session
        this.flashes = session.flashes || [];
    },
    /**
     * Re-render all flash messages any time the session was told to remove
     * one.
     */
    start: function () {
        session.on('flash_remove', this, this.renderElement);
        return this._super();
    },
    /**
     * On closing a flash message, notify the session that we need it to
     * be removed.
     *
     * @param {MouseEvent} e click event from the "close" button of the
     *                       alert-dismissible bootstrap widget thing
     *
     * @private
     */
    _onClose: function (e) {
        var msgIndex = $(e.currentTarget).data('msgIndex');
        session.trigger_up('flash_remove', {index: msgIndex});
        return false;
    },
});
});
