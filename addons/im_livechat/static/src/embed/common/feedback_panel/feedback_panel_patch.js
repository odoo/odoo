import { FeedbackPanel } from "@im_livechat/core/common/feedback_panel";

import { t, useProps } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(FeedbackPanel.prototype, {
    setup() {
        super.setup(...arguments);
        this.embedProps = useProps({
            onClickNewSession: t.function().optional(),
        });
        this.livechatService = useService("im_livechat.livechat");
    },
    get allowNewSession() {
        return (
            this.store.livechat_rule?.action !== "hide_button" &&
            this.livechatService.options.channel_id
        );
    },
});
