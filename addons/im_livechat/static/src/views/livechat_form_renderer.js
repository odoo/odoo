import { Discuss } from "@mail/core/public_web/discuss";

import { onMounted, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";

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
            this.thread = await this.restoreDiscussThread(this.props);
        });
        onWillUpdateProps(async (nextProps) => {
            this.thread = await this.restoreDiscussThread(nextProps);
        });
        onMounted(() => (this.store.discuss.isActive = false));
    }

    /**
     * Restore the discuss thread according to record id in the props if
     * necessary.
     *
     * @param {Props} props
     */
    async restoreDiscussThread(props) {
        const activeThread = await this.store.Thread.getOrFetch({
            model: "discuss.channel",
            id: props.record.resId,
        });
        if (activeThread && activeThread.notEq(this.store.discuss.thread)) {
            return activeThread;
        }
    }
}
