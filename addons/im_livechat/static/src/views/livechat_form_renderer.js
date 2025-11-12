import { Discuss } from "@mail/core/public_web/discuss";

import { onWillDestroy, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { FormRenderer } from "@web/views/form/form_renderer";

export class LivechatSessionFormRenderer extends FormRenderer {
    static template = "im_livechat.LivechatDiscuss";
    static components = {
        ...FormRenderer.components,
        Discuss,
    };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        onWillStart(async () => {
            await this.getChannel(this.props);
            this.setCurrentThreadShadowedBySelf(true);
        });
        onWillUpdateProps(async (nextProps) => {
            if (nextProps.record.resId === this.props.record.resId) {
                return;
            }
            this.setCurrentThreadShadowedBySelf(false);
            await this.getChannel(nextProps);
            this.setCurrentThreadShadowedBySelf(true);
        });
        onWillDestroy(() => this.setCurrentThreadShadowedBySelf(false));
    }

    setCurrentThreadShadowedBySelf(shadowedBySelf) {
        if (this.thread) {
            this.thread.shadowedBySelf = shadowedBySelf;
        }
    }

    /**
     * Restore the discuss thread according to record id in the props if
     * necessary.
     *
     * @param {Props} props
     */
    async getChannel(props) {
        this.thread = await this.store.Thread.getOrFetch({
            model: "discuss.channel",
            id: props.record.resId,
        });
    }

    redirectToSessions() {
        this.env.services.action.doAction("im_livechat.discuss_channel_action", {
            clearBreadcrumbs: true,
        });
    }
}
