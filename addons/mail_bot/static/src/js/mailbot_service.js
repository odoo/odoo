odoo.define('mail_bot.MailBotService', function (require) {
"use strict";

const AbstractService = require('web.AbstractService');
var { _t, serviceRegistry } = require('web.core');
var session = require('web.session');

class MailBotService extends AbstractService {

    /**
     * @override
     */
    start() {
        this._hasRequest = (window.Notification && window.Notification.permission === "default") || false;
        if ('odoobot_initialized' in session && ! session.odoobot_initialized) {
            this._showOdoobotTimeout();
        }
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get the previews related to the OdooBot (conversation not included).
     * For instance, when there is no conversation with OdooBot and OdooBot has
     * a request, it should display a preview in the systray messaging menu.
     *
     * @param {string|undefined} [filter]
     * @returns {Object[]} list of objects that are compatible with the
     *   'mail.Preview' template.
     */
    getPreviews(filter) {
        if (!this.isRequestingForNativeNotifications()) {
            return [];
        }
        if (filter && filter !== 'mailbox_inbox') {
            return [];
        }
        var previews = [{
            title: _t("OdooBot has a request"),
            imageSRC: "/mail/static/src/img/odoobot.png",
            status: 'bot',
            body:  _t("Enable desktop notifications to chat"),
            id: 'request_notification',
            unreadCounter: 1,
        }];
        return previews;
    }

    /**
     * Tell whether OdooBot is requesting to enable push notifications.
     *
     * @returns {boolean}
     */
    isRequestingForNativeNotifications() {
        return this._hasRequest;
    }

    /**
     * Called when user either accepts or refuses push notifications.
     */
    removeRequest() {
        this._hasRequest = false;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _showOdoobotTimeout() {
        var self = this;
        setTimeout(function () {
            session.odoobot_initialized = true;
            self.env.services.rpc({
                model: 'mail.channel',
                method: 'init_odoobot',
            });
        }, 2*60*1000);
    }
}

serviceRegistry.add('mailbot_service', MailBotService);

return MailBotService;

});
