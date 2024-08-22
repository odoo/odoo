import { Composer } from "@mail/core/common/composer";
import { Thread } from "@mail/core/common/thread";
import { useThreadActions } from "@mail/core/common/thread_actions";
import { onWillStart, onWillUpdateProps, useChildSubEnv, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { FormRenderer } from "@web/views/form/form_renderer";
import { useMessageHighlight } from "@mail/utils/common/hooks";
import { DiscussHeader } from "@mail/core/common/discuss_header";

export class LivechatSessionFormRenderer extends FormRenderer {
    static template = "im_livechat.LivechatDiscuss";
    static components = {
        ...FormRenderer.components,
        Thread,
        Composer,
        DiscussHeader,
    };

    setup() {
        super.setup();
        this.state = useState({ activeAction: null });
        this.contentRef = useRef("content");
        this.root = useRef("root");
        this.store = useState(useService("mail.store"));
        this.ui = useState(useService("ui"));
        this.threadActions = useThreadActions();
        this.messageHighlight = useMessageHighlight();
        useChildSubEnv({
            inDiscussApp: false,
            messageHighlight: this.messageHighlight,
        });
        onWillStart(async () => {
            await this.restoreDiscussThread(this.props);
        });
        onWillUpdateProps(async (nextProps) => {
            await this.restoreDiscussThread(nextProps);
        });
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
            id: props.record.evalContext.id,
        });
        if (activeThread && activeThread.notEq(this.store.discuss.thread)) {
            activeThread.setAsDiscussThread(false);
        }
        this.store.discuss.hasRestoredThread = true;
    }

    get thread() {
        return this.store.discuss.thread;
    }
}
