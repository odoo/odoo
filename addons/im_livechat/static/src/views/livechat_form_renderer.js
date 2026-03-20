import { Discuss } from "@mail/core/public_web/discuss_app/discuss_app";

import { onWillStart, onWillUpdateProps, useEffect, useState } from "@odoo/owl";

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
        useEffect(
            (channel) => {
                if (channel) {
                    channel.shadowedBySelf++;
                    return () => channel.shadowedBySelf--;
                }
            },
            () => [this.thread?.channel]
        );
        onWillStart(() => this.getChannel(this.props));
        onWillUpdateProps(async (nextProps) => {
            if (nextProps.record.resId === this.props.record.resId) {
                return;
            }
            await this.getChannel(nextProps);
        });
    }

    /**
     * Restore the discuss thread according to record id in the props if
     * necessary.
     *
     * @param {Props} props
     */
    async getChannel(props) {
        this.thread = await this.store["mail.thread"].getOrFetch({
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
