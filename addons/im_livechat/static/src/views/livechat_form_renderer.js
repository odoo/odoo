import { Discuss } from "@mail/core/public_web/discuss";

import { onWillStart, onWillUpdateProps, useState } from "@odoo/owl";

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
        });
        onWillUpdateProps(async (nextProps) => {
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
