import { useOnChange } from "@odoo/owl";

import { ACTION_TAGS } from "@mail/core/common/action";
import { DiscussContent } from "@mail/core/public_web/discuss_content";
import { Call } from "@mail/discuss/call/common/call";
import { getCallActionComponent } from "@mail/discuss/call/common/call_action_list";
import { PipBanner } from "@mail/discuss/call/common/pip_banner";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

Object.assign(DiscussContent.components, { Call, PipBanner });

patch(DiscussContent.prototype, {
    setup() {
        super.setup(...arguments);
        this.rtc = useService("discuss.rtc");
        // close action panel when opening a side channel
        useOnChange(
            () => [this.store.discuss.sideChannel],
            (sideChannel) => {
                if (sideChannel && this.threadActions.activeAction) {
                    this.threadActions.activeAction.actionPanelClose({ closeAll: true });
                }
            }
        );
        // close side channel when opening an action panel
        useOnChange(
            () => [this.threadActions.activeAction],
            (activeAction) => {
                if (activeAction && !activeAction.popover) {
                    this.store.discuss.sideChannel = undefined;
                }
            }
        );
    },
    // contracted action list when the side channel is open
    computeHeaderActionsList() {
        const groups = super.computeHeaderActionsList();
        if (!this.store.discuss.sideChannel) {
            return groups;
        }
        const isInline = (action) =>
            ["notification-settings", "show-threads"].includes(action.id) ||
            action.tags.includes(ACTION_TAGS.JOIN_LEAVE_CALL);
        const { quick, other, group } = this.threadActions.partition;
        const moreGroups = [quick, other, ...group]
            .map((actions) => actions.filter((action) => !isInline(action)))
            .filter((actions) => actions.length);
        const inlineGroups = groups.map((actions) => actions.filter(isInline));
        if (!moreGroups.length) {
            return inlineGroups;
        }
        const moreAction = this.threadActions.more(
            { thread: () => this.thread },
            { actions: moreGroups, dropdownPosition: "bottom-end", name: _t("More Actions") }
        );
        return [...inlineGroups, [moreAction]];
    },
    /** @type {import("@mail/core/common/action_list").GetActionComponent} */
    getActionComponent(params) {
        return getCallActionComponent(params) ?? super.getActionComponent(params);
    },
});
