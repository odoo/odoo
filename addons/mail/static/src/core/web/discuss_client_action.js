/* @odoo-module */

import { Discuss } from "@mail/core/common/discuss";
import { useMessaging, useStore } from "@mail/core/common/messaging_hook";

import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { createLocalId } from "@mail/utils/common/misc";

/**
 * @typedef {Object} Props
 * @property {Object} action
 * @property {Object} action.context
 * @property {number} [action.context.active_id]
 * @property {Object} [action.params]
 * @property {number} [action.params.active_id]
 * @extends {Component<Props, Env>}
 */
export class DiscussClientAction extends Component {
    static components = { Discuss };
    static props = ["*"];
    static template = "mail.DiscussClientAction";

    setup() {
        this.store = useStore();
        this.messaging = useMessaging();
        this.threadService = useService("mail.thread");
        onWillStart(() => this.restoreDiscussThread(this.props));
        onWillUpdateProps((nextProps) => this.restoreDiscussThread(nextProps));
    }

    /**
     * Restore the discuss thread according to the active_id in the action
     * if necessary: thread is different than the one already displayed and
     * we are not in a public page. If the thread is not yet known, fetch it.
     *
     * @param {Props} props
     */
    async restoreDiscussThread(props) {
        await this.messaging.isReady;
        if (this.store.inPublicPage) {
            return;
        }
        const rawActiveId =
            props.action.context.active_id ??
            props.action.params?.active_id ??
            this.store.discuss.threadLocalId?.replace(",", "_") ??
            "mail.box_inbox";
        const activeId =
            typeof rawActiveId === "number" ? `discuss.channel_${rawActiveId}` : rawActiveId;
        let [model, id] = activeId.split("_");
        if (model === "mail.channel") {
            // legacy format (sent in old emails, shared links, ...)
            model = "discuss.channel";
        }
        const activeThreadLocalId = createLocalId(model, id);
        if (activeThreadLocalId !== this.store.discuss.threadLocalId) {
            const thread =
                this.store.threads[createLocalId(model, id)] ??
                (await this.threadService.fetchChannel(parseInt(id)));
            if (!thread.is_pinned) {
                await this.threadService.pin(thread);
            }
            this.threadService.setDiscussThread(thread);
        }
    }
}

registry.category("actions").add("mail.action_discuss", DiscussClientAction);
