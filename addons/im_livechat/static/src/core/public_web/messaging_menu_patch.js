import { MessagingMenu } from "@mail/core/public_web/messaging_menu/messaging_menu";

import { useEffect } from "@odoo/owl";

import { memoize } from "@web/core/utils/functions";
import { patch } from "@web/core/utils/patch";

/** @type {MessagingMenu} */
const messagingMenuPatch = {
    setup() {
        super.setup(...arguments);
        const ensureLookingForHelpBusSubscription = memoize(() => {
            this.env.services.bus_service.addChannel("im_livechat.looking_for_help");
        });
        useEffect(() => {
            if (this.state().activeTab.eq(this.store.messagingMenu.livechatTab)) {
                ensureLookingForHelpBusSubscription();
            }
        });
    },
};
patch(MessagingMenu.prototype, messagingMenuPatch);
