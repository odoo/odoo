import { Message } from "@mail/core/common/message";
import { onWillStart } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";

patch(Message.prototype, {
    setup() {
        super.setup();
        onWillStart(async () => {
            this.hasLivechatAccess = await user.hasGroup("im_livechat.im_livechat_group_user");
        });
    },

    get shouldShowLivechatActions() {
        if (this.props.thread?.livechat_end_dt) {
            return this.hasLivechatAccess;
        }
        return true;
    }
});
