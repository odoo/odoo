import { Discuss } from "@mail/core/public_web/discuss_app/discuss_app";

import { asyncComputed, proxy } from "@odoo/owl";

import { useOnChange } from "@mail/utils/common/hooks";
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
        this.store = proxy(useService("mail.store"));
        this.channel = asyncComputed(() =>
            this.store["discuss.channel"].getOrFetch(this.props.record.resId)
        );
        useOnChange(
            () => [this.channel()],
            (channel) => {
                if (!channel) {
                    return;
                }
                channel.shadowedBySelf++;
                return () => channel.shadowedBySelf--;
            }
        );
    }

    redirectToSessions() {
        this.env.services.action.doAction("im_livechat.discuss_channel_action", {
            clearBreadcrumbs: true,
        });
    }
}
