/* @odoo-module */

import { DiscussClientAction } from "@mail/core/web/discuss_client_action";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(DiscussClientAction.prototype, {
    setup() {
        super.setup();
        this.menu = useService("menu");
    },

    async restoreDiscussThread(props) {
        await super.restoreDiscussThread(props);
        const menuId = this.props.action.params?.menu_id;
        const appData = this.menu.getCurrentApp() || this.menu.getMenu(menuId);
        const fromLivechatMenu = appData?.xmlid === "im_livechat.menu_livechat_root";
        if (this.store.discuss.thread?.readonly && !fromLivechatMenu) {
            this.threadService.setDiscussThread(this.store.discuss.inbox);
        }
    },
});
