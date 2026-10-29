import { useEffect } from "@odoo/owl";

import { PANEL_CONTAINER_TYPE } from "@mail/core/common/action";
import { DiscussContent } from "@mail/core/public_web/discuss_content";
import { Call } from "@mail/discuss/call/common/call";
import { getCallActionComponent } from "@mail/discuss/call/common/call_action_list";
import { PipBanner } from "@mail/discuss/call/common/pip_banner";
import { computedShallowEqual } from "@mail/utils/common/signal";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

Object.assign(DiscussContent.components, { Call, PipBanner });

patch(DiscussContent.prototype, {
    setup() {
        super.setup(...arguments);
        this.rtc = useService("discuss.rtc");
        const headerActionsList = this.headerActionsList;
        this.headerActionsList = computedShallowEqual(() => {
            const actions = headerActionsList();
            if (!this.hasSideChannel) {
                return actions;
            }
            return [
                ...actions,
                this.threadActions.more(
                    { thread: () => this.thread },
                    {
                        actions: this.headerPanelActions(),
                        id: "contracted-header",
                        name: _t("More Actions"),
                    },
                    "contracted-header"
                ),
            ];
        });
        // The panel actions in the closed "More Actions" dropdown have no button for their hotkey.
        const hotkeyService = useService("hotkey");
        useEffect(() => {
            if (!this.hasSideChannel) {
                return;
            }
            const hotkeyCleanups = this.headerPanelActions()
                .filter((action) => action.hotkey)
                .map((action) =>
                    hotkeyService.add(
                        `${hotkeyService.overlayModifier}+${action.hotkey}`,
                        () => action.onSelected(),
                        { bypassEditableProtection: true }
                    )
                );
            return () => hotkeyCleanups.forEach((cleanup) => cleanup());
        });
    },
    autoOpenPanel() {
        const panelAction =
            this.panelActionIdFromSideChannel &&
            this.threadActions.get(this.panelActionIdFromSideChannel);
        this.panelActionIdFromSideChannel = undefined;
        if (panelAction) {
            panelAction.openPanel();
            return;
        }
        super.autoOpenPanel(...arguments);
    },
    /**
     * Opens side channel in full view with action panel already open, @see autoOpenPanel.
     *
     * @param {import("@mail/core/common/thread_actions").ThreadAction} panelAction
     */
    openSideChannelInFullView(panelAction) {
        this.panelActionIdFromSideChannel = panelAction.id;
        this.store.discuss.sideChannel.setAsDiscussThread();
    },
    /** @type {import("@mail/core/common/action_list").GetActionComponent} */
    getActionComponent(params) {
        return getCallActionComponent(params) ?? super.getActionComponent(params);
    },
    /** @type {import("@mail/core/common/action_list").GetPanelContainer} */
    getPanelContainer({ action }) {
        if (action.id === "more-action:contracted-header") {
            return { type: PANEL_CONTAINER_TYPE.DROPDOWN, position: "bottom-end" };
        }
        return super.getPanelContainer(...arguments);
    },
    get showActionPanelSwitcher() {
        return super.showActionPanelSwitcher && !this.hasSideChannel;
    },
    get hasSideChannel() {
        return Boolean(this.threadActions.get("side-channel"));
    },
});
