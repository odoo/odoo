import { Discuss } from "@mail/core/public_web/discuss_app/discuss_app";

import { onWillStart, onWillUpdateProps, proxy, signal, untrack, useEffect } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { FormRenderer } from "@web/views/form/form_renderer";

export class LivechatSessionFormRenderer extends FormRenderer {
    static template = "im_livechat.LivechatDiscuss";
    static components = {
        ...FormRenderer.components,
        Discuss,
    };

    channel = signal(undefined);

    setup() {
        super.setup();
        this.store = proxy(useService("mail.store"));
        useEffect(() => {
            const channel = this.channel();
            if (!channel) {
                return;
            }
            untrack(() => channel.shadowedBySelf++);
            return () => channel.shadowedBySelf--;
        });
        onWillStart(() => this.getChannel(this.props));
        onWillUpdateProps(async (nextProps) => {
            if (nextProps.record.resId === this.props.record.resId) {
                return;
            }
            await this.getChannel(nextProps);
        });
    }

    /**
     * Restore the discuss channel according to record id in the props if
     * necessary.
     *
     * @param {Props} props
     */
    async getChannel(props) {
        this.channel.set(await this.store["discuss.channel"].getOrFetch(props.record.resId));
    }

    redirectToSessions() {
        this.env.services.action.doAction("im_livechat.discuss_channel_action", {
            clearBreadcrumbs: true,
        });
    }
}
