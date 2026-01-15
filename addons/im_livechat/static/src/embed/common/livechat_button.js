import { Component, useRef, useState, useEffect } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";

export class LivechatButton extends Component {
    static template = "im_livechat.LivechatButton";
    static props = {};
    static DEBOUNCE_DELAY = 500;

    setup() {
        this.store = useService("mail.store");
        /** @type {import('@im_livechat/embed/common/livechat_service').LivechatService} */
        this.livechatService = useService("im_livechat.livechat");
        this.onClick = debounce(this.onClick.bind(this), LivechatButton.DEBOUNCE_DELAY, {
            leading: true,
        });
        this.ref = useRef("button");
        this.state = useState({ animateNotification: this.isShown });
        useEffect(
            (isShown, rootNodeClassList) => {
                if (isShown && rootNodeClassList) {
                    rootNodeClassList.add("o-livechat-LivechatButton-isVisible");
                    return () => {
                        rootNodeClassList.remove("o-livechat-LivechatButton-isVisible");
                    };
                }
            },
            () => [this.isShown, this.ref.el?.getRootNode().host?.classList]
        );
    }

    onClick() {
        this.state.animateNotification = false;
        this.livechatService.open();
    }

    get isShown() {
        return (
            this.store.livechat_available &&
            this.store.activeLivechats.length === 0 &&
            this.livechatService.options.channel_id
        );
    }
}
