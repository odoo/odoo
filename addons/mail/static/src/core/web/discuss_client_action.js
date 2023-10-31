/* @odoo-module */

import { Discuss } from "@mail/core/common/discuss";

import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

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
        this.store = useState(useService("mail.store"));
        this.messaging = useState(useService("mail.messaging"));
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
            this.store.Thread.localIdToActiveId(this.store.discuss.thread?.localId) ??
            "mail.box_inbox";
        const activeId =
            typeof rawActiveId === "number" ? `discuss.channel_${rawActiveId}` : rawActiveId;
        let [model, id] = activeId.split("_");
        if (model === "mail.channel") {
            // legacy format (sent in old emails, shared links, ...)
            model = "discuss.channel";
        }
        const activeThread = this.store.Thread.get({ model, id });
        if (!activeThread || activeThread.notEq(this.store.discuss.thread)) {
            const thread =
                this.store.Thread.get({ model, id }) ??
                (await this.threadService.fetchChannel(parseInt(id)));
            if (!thread) {
                return;
            }
            if (!thread.is_pinned) {
                await this.threadService.pin(thread);
            }
            this.threadService.setDiscussThread(thread);
        }
    }
}

registry.category("actions").add("mail.action_discuss", DiscussClientAction);
