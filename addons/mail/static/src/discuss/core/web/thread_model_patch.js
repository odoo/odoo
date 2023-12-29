/* @odoo-module */

import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    foldStateCount: 0,
    addNewMessage(message, { afterInitBus = false } = {}) {
        super.addNewMessage(...arguments);
        if (
            message.originThread.model !== "discuss.channel" ||
            this._store.env.services.ui.isSmall ||
            message.isSelfAuthored
        ) {
            return;
        }
        if (
            message.originThread.correspondent?.eq(this._store.odoobot) &&
            this._store.odoobotOnboarding
        ) {
            // this cancels odoobot onboarding auto-opening of chat window
            this._store.odoobotOnboarding = false;
            return;
        }
        this._store.env.services["mail.thread"].notifyMessageToUser(message);
    },
});
