import { computed, useOnChange } from "@odoo/owl";

import { ACTION_TAGS, PANEL_CONTAINER_TYPE } from "@mail/core/common/action";
import { ThreadAction } from "@mail/core/common/thread_actions";
import { DiscussContent } from "@mail/core/public_web/discuss_content";
import { Call } from "@mail/discuss/call/common/call";
import { getCallActionComponent } from "@mail/discuss/call/common/call_action_list";
import { PipBanner } from "@mail/discuss/call/common/pip_banner";
import { DiscussSideChannel } from "@mail/discuss/core/public_web/discuss_side_channel";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

Object.assign(DiscussContent.components, { Call, DiscussSideChannel, PipBanner });

patch(DiscussContent.prototype, {
    setup() {
        super.setup(...arguments);
        this.rtc = useService("discuss.rtc");
        // not registered, not listed: only for using the panel stack
        this.sideChannelAction = new ThreadAction({
            actions: this.threadActions,
            definition: {
                condition: ({ store }) => Boolean(store.discuss.sideChannel),
                panel: {
                    component: DiscussSideChannel,
                    onClose: ({ store }) => (store.discuss.sideChannel = undefined),
                    props: ({ store }) => ({
                        channel: store.discuss.sideChannel,
                        openInFullView: (panelAction) =>
                            this.openSideChannelInFullView(panelAction),
                    }),
                },
            },
            id: "side-channel",
            owner: this,
            thread: () => this.thread,
        });
        /** @type {() => import("@mail/core/common/action").Panel|undefined} */
        this.sideChannelPanel = computed(() => {
            const panel = this.threadActions.activePanel;
            return panel?.action.id === this.sideChannelAction.id ? panel : undefined;
        });
        useOnChange(
            () => [this.store.discuss.sideChannel],
            (sideChannel) => {
                if (sideChannel) {
                    this.sideChannelAction.openPanel({ keepPrevious: true });
                } else if (this.sideChannelAction.isActive) {
                    this.sideChannelAction.closePanel();
                }
            }
        );
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
    // contracted action list when the side channel is open
    computeHeaderActionsList() {
        const groups = super.computeHeaderActionsList();
        if (!this.sideChannelPanel()) {
            return groups;
        }
        const isInline = (action) =>
            ["notification-settings", "show-threads"].includes(action.id) ||
            action.tags.includes(ACTION_TAGS.JOIN_LEAVE_CALL);
        const moreGroups = groups
            .map((actions) => actions.filter((action) => !isInline(action)))
            .filter((actions) => actions.length);
        const inlineGroups = groups.map((actions) => actions.filter(isInline));
        if (!moreGroups.length) {
            return inlineGroups;
        }
        const moreAction = this.threadActions.more(
            { thread: () => this.thread },
            { actions: moreGroups, id: "contracted-header", name: _t("More Actions") },
            "contracted-header"
        );
        return [...inlineGroups, [moreAction]];
    },
    get showsPanelContainer() {
        return !this.sideChannelPanel() && super.showsPanelContainer;
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
});
