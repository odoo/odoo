import { CloseConfirmation } from "@im_livechat/core/common/close_confirmation";

import { ChatWindow } from "@mail/core/common/chat_window";

import { patch } from "@web/core/utils/patch";
import { CW_LIVECHAT_STEP } from "./chat_window_model_patch";

Object.assign(ChatWindow.components, { CloseConfirmation });

patch(ChatWindow.prototype, {
    setup() {
        super.setup(...arguments);
        this.CW_LIVECHAT_STEP = CW_LIVECHAT_STEP;
    },
    onCloseConfirmationDialog() {
        this.props.chatWindow.actionsDisabled = false;
        this.props.chatWindow.livechatStep = CW_LIVECHAT_STEP.NONE;
    },
});
