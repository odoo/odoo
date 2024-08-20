import { patch } from "@web/core/utils/patch";
import { Store } from "@mail/core/common/store_service";

/** @type {import("models").Store} */
const StorePatch = {
    onStarted() {
        super.onStarted(...arguments);
        this.env.bus.addEventListener(
            "discuss.channel/new_message",
            ({ detail: { channel, message } }) => {
                if (this.env.services.ui.isSmall || message.isSelfAuthored) {
                    return;
                }
                if (channel.isCorrespondentOdooBot && this.store.odoobotOnboarding) {
                    // this cancels odoobot onboarding auto-opening of chat window
                    this.store.odoobotOnboarding = false;
                    return;
                }
                channel.notifyMessageToUser(message);
            }
        );
    },
};

patch(Store.prototype, StorePatch);
