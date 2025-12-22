import { Discuss } from "@mail/core/public_web/discuss";

import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { router } from "@web/core/browser/router";

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
        super.setup();
        this.store = useState(useService("mail.store"));
        onWillStart(() => {
            // bracket to avoid blocking rendering with restore promise
            this.restoreDiscussThread(this.props);
        });
        onWillUpdateProps((nextProps) => {
            // bracket to avoid blocking rendering with restore promise
            this.restoreDiscussThread(nextProps);
        });
    }

    getActiveId(props) {
        return (
            props.action.context.active_id ??
            props.action.params?.active_id ??
            this.store.Thread.localIdToActiveId(this.store.discuss.thread?.localId) ??
            "mail.box_inbox"
        );
    }

    /**
     * @param {string} rawActiveId
     */
    parseActiveId(rawActiveId) {
        const [model, id] = rawActiveId.split("_");
        if (model === "mail.box") {
            return ["mail.box", id];
        }
        return [model, parseInt(id)];
    }

    /**
     * Restore the discuss thread according to the active_id in the action if
     * necessary.
     *
     * @param {Props} props
     */
    async restoreDiscussThread(props) {
        const rawActiveId = this.getActiveId(props);
        const [model, id] = this.parseActiveId(rawActiveId);
        const activeThread = await this.store.Thread.getOrFetch({ model, id });
        if (activeThread && activeThread.notEq(this.store.discuss.thread)) {
            const highlight_message_id =
                props.action?.params?.highlight_message_id || router.current.highlight_message_id;
            if (highlight_message_id) {
                activeThread.highlightMessage = highlight_message_id;
                delete props.action?.params?.highlight_message_id;
                delete router.current?.highlight_message_id;
            }
            activeThread.setAsDiscussThread(false);
        }
        this.store.discuss.hasRestoredThread = true;
    }
}

registry.category("actions").add("mail.action_discuss", DiscussClientAction);
