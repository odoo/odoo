import { Discuss } from "@mail/core/common/discuss";

import { Component, onWillStart, onWillUpdateProps, useState, onMounted, status } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { effect } from "@web/core/utils/reactive";

const boxIds = {
    1: "inbox",
    2: "starred",
    3: "history",
};

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
    static path = "discuss";

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

        let oldThread;
        onMounted(() => {
            effect(
                (store) => {
                    if (status(this) === "mounted") {
                        const thread = store.discuss.thread;
                        if (thread) {
                            if (thread.pushState) {
                                const key = Object.keys(boxIds).find(
                                    (key) => boxIds[key] === thread.id
                                );
                                this.props.updateActionState({
                                    resId: thread.model === "discuss.channel" ? thread.id : false,
                                    active_id: thread.model === "mail.box" ? parseInt(key) : false,
                                });
                            }
                        } else if (oldThread) {
                            // unpinned thread
                            this.props.updateActionState({
                                resId: false,
                                active_id: false,
                            });
                        }
                        oldThread = thread;
                    }
                },
                [this.store]
            );
        });
    }

    /**
     * Restore the discuss thread according to the active_id in the action if
     * necessary.
     *
     * @param {Props} props
     */
    async restoreDiscussThread(props) {
        const { context, params = {} } = props.action;
        let activeId = context.active_id || params.active_id;
        if (typeof activeId === "number") {
            activeId = boxIds[activeId];
        }
        const id = activeId ?? props.resId ?? this.store.discuss.thread?.id ?? "inbox";
        const model = activeId
            ? "mail.box"
            : props.resId
            ? "discuss.channel"
            : this.store.discuss.thread?.model ?? "mail.box";

        const activeThread = await this.store.Thread.getOrFetch({ model, id });
        if (activeThread && activeThread.notEq(this.store.discuss.thread)) {
            activeThread.setAsDiscussThread(false);
        }
        this.store.discuss.hasRestoredThread = true;
    }
}

registry.category("actions").add("mail.action_discuss", DiscussClientAction);
