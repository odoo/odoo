import { CloseConfirmation } from "@im_livechat/core/common/close_confirmation";

import { ChatWindow } from "@mail/core/common/chat_window";

import { patch } from "@web/core/utils/patch";
import { CW_LIVECHAT_STEP } from "./chat_window_model_patch";
import { useEffect, useRef } from "@odoo/owl";

Object.assign(ChatWindow.components, { CloseConfirmation });

patch(ChatWindow.prototype, {
    setup() {
        super.setup(...arguments);
        this.CW_LIVECHAT_STEP = CW_LIVECHAT_STEP;
        this.ref = useRef("chatWindow");
        useEffect(
            (focus) => {
                if (
                    focus &&
                    this.ref.el &&
                    this.props.chatWindow.thread.channel_type === "livechat" &&
                    !this.props.chatWindow.thread.livechat_active
                ) {
                    this.ref.el.focus();
                }
            },
            () => [this.props.chatWindow.autofocus]
        );
    },
    onCloseConfirmationDialog() {
        this.props.chatWindow.autofocus++;
        this.props.chatWindow.actionsDisabled = false;
        this.props.chatWindow.livechatStep = CW_LIVECHAT_STEP.NONE;
    },
});
