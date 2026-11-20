import { Component, proxy, signal, useEffect } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";

export class LivechatButton extends Component {
    static template = "im_livechat.LivechatButton";
    static DEBOUNCE_DELAY = 500;

    buttonRef = signal.ref();

    setup() {
        this.store = useService("mail.store");
        /** @type {import('@im_livechat/embed/common/livechat_service').LivechatService} */
        this.livechatService = useService("im_livechat.livechat");
        this.onClick = debounce(this.onClick.bind(this), LivechatButton.DEBOUNCE_DELAY, {
            leading: true,
        });
        this.state = proxy({ animateNotification: this.isShown });
        useEffect(() => {
            const rootNodeClassList = this.buttonRef()?.getRootNode().host?.classList;
            if (this.isShown && rootNodeClassList) {
                rootNodeClassList.add("o-livechat-LivechatButton-isVisible");
                return () => {
                    rootNodeClassList.remove("o-livechat-LivechatButton-isVisible");
                };
            }
        });
    }

    onClick() {
        this.state.animateNotification = false;
        this.livechatService.open();
    }

    get isShown() {
        return (
            this.store.livechat_available &&
            this.store.activeVisitorLivechats.length === 0 &&
            this.livechatService.options.channel_id
        );
    }
}
