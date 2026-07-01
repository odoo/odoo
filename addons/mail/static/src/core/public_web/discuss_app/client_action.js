import { Discuss } from "@mail/core/public_web/discuss_app/discuss_app";

import { Component, onMounted, onWillUnmount, t } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { router } from "@web/core/browser/router";
import { propComputed, useOnChange } from "@mail/utils/common/hooks";

export class DiscussClientAction extends Component {
    static components = { Discuss };
    static template = "mail.DiscussClientAction";

    setup() {
        super.setup();
        this.action = propComputed(
            "action",
            t
                .object({
                    context: t.object({
                        active_id: t.or([t.string(), t.number()]).optional(),
                    }),
                    params: t
                        .object({
                            active_id: t.or([t.string(), t.number()]).optional(),
                            default_active_id: t.or([t.string(), t.number()]).optional(),
                            highlight_message_id: t.number().optional(),
                        })
                        .optional(),
                })
                // The public page doesn't use the action service, but overrides
                // `getActiveId` to provide the id from the URL instead of the action.
                .optional()
        );
        this.store = useService("mail.store");
        useOnChange(
            () => [this.action()],
            (action) => this.restoreDiscussThread(action())
        );
        onMounted(() => (this.store.discuss.isActive = true));
        onWillUnmount(() => (this.store.discuss.isActive = false));
    }

    getActiveId(action) {
        return (
            action.context.active_id ??
            action.params?.active_id ??
            this.store["mail.thread"].localIdToActiveId(this.store.discuss.thread?.localId) ??
            (this.env.services.ui.isSmall ? undefined : this.store.discuss.lastActiveId)
        );
    }

    /** @param {string} [rawActiveId] */
    parseActiveId(rawActiveId) {
        if (!rawActiveId) {
            return undefined;
        }
        const [model, id] = rawActiveId.split("_");
        if (model === "mail.box") {
            if (id === "starred") {
                // legacy value to be kept forever to avoid breaking links
                return ["mail.box", "bookmark"];
            }
            return ["mail.box", id];
        }
        return [model, parseInt(id)];
    }

    /**
     * Restore the discuss thread according to the active_id in the action if
     * necessary.
     *
     * @param {Object} action
     */
    async restoreDiscussThread(action) {
        const rawActiveId = this.getActiveId(action);
        const parsedActiveId = this.parseActiveId(rawActiveId);
        if (!parsedActiveId) {
            this.store.discuss.thread = undefined;
            this.store.discuss.hasRestoredThread = true;
            const odoobotChat = this.store.odoobot?.searchChat();
            const selfMember = odoobotChat?.self_member_id;
            if (odoobotChat && selfMember?.is_pinned && !selfMember.seen_message_id) {
                odoobotChat.setAsDiscussThread(false);
            }
            return;
        }
        const [model, id] = parsedActiveId;
        const activeThread = await this.store["mail.thread"].getOrFetch({ model, id });
        if (activeThread && !activeThread.discussAppAsThread) {
            const highlight_message_id =
                action?.params?.highlight_message_id || router.current.highlight_message_id;
            if (highlight_message_id) {
                activeThread.highlightMessage = highlight_message_id;
                delete action?.params?.highlight_message_id;
                delete router.current?.highlight_message_id;
            }
            activeThread.setAsDiscussThread(false);
        }
        this.store.discuss.hasRestoredThread = true;
    }
}

registry.category("actions").add("mail.action_discuss", DiscussClientAction);
