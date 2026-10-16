import {
    Component,
    computed,
    proxy,
    signal,
    types,
    untrack,
    useEffect,
    useOnChange,
    usePlugin,
} from "@odoo/owl";

import { useThreadActions } from "@mail/core/common/thread_actions";
import { AutoresizeInput } from "@mail/core/common/autoresize_input";
import { ActionList, CircleInlineAction } from "@mail/core/common/action_list";
import { useAncestors } from "@mail/core/common/ancestor_plugin";
import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { Thread } from "@mail/core/common/thread";
import { Composer } from "@mail/core/common/composer";
import { attClassObjectToString } from "@mail/utils/common/format";

import { UIPlugin } from "@web/core/ui/ui_plugin";
import { FileUploader } from "@web/views/fields/file_handler";
import { useService } from "@web/core/utils/hooks";
import { useTransition } from "@web/core/transition";
import { propSignal } from "@mail/utils/common/hooks";
import { computedShallowEqual } from "@mail/utils/common/signal";
import { ACTION_GROUP_TAGS, PANEL_CONTAINER_TYPE } from "@mail/core/common/action";

/** The duration of `--mail-Discuss-transition` in `discuss_app.css`. */
const PANEL_TRANSITION_DURATION = 150;

class DiscussContentCircleAction extends CircleInlineAction {
    get classObj() {
        return { ...super.classObj, "o-mail-DiscussContentCircleAction": true };
    }
}

export class DiscussContent extends Component {
    static components = {
        ActionList,
        AutoresizeInput,
        DiscussAvatar,
        Thread,
        Composer,
        FileUploader,
    };
    static template = "mail.DiscussContent";

    setup() {
        super.setup();
        this.ancestors = useAncestors({
            inDiscussContent: {
                panelWidth: () => untrack(() => this.store.discuss.panelWidth),
                /** @param {number} width */
                setPanelWidth: (width) => (this.store.discuss.panelWidth = width),
            },
        });
        this.store = useService("mail.store");
        this.channel = propSignal("channel", types.instanceOf(this.store["discuss.channel"]), {
            optional: true,
        });
        this.ui = usePlugin(UIPlugin);
        this.rootRef = signal.ref(HTMLDivElement);
        this.panelActionsRef = signal.ref(HTMLDivElement);
        this.threadAvatarRef = signal.ref(HTMLDivElement);
        this.threadActions = useThreadActions({ rootRef: this.rootRef, thread: () => this.thread });
        this.headerQuickActions = computedShallowEqual(() => this.threadActions.partition.quick);
        /** Whether the action opens a side panel and is in the group of panels. */
        const isPanelSwitcherAction = (action) =>
            action.hasPanel &&
            !action.definition.panel.component.menu &&
            !this.getPanelContainer({ action }) &&
            Boolean(
                this.threadActions.actionGroupDescriptions
                    .get(action.sequenceGroup)
                    ?.tags.includes(ACTION_GROUP_TAGS.ACTION_PANELS)
            );
        const groupedActions = computed(() =>
            this.threadActions.partition.group.toReversed().flat()
        );
        /** The non-quick actions outside the panel switcher. */
        this.headerActionsList = computedShallowEqual(() => [
            ...this.threadActions.partition.other,
            ...groupedActions().filter((action) => !isPanelSwitcherAction(action)),
        ]);
        /** The actions of the panel switcher. */
        this.headerPanelActions = computedShallowEqual(() =>
            groupedActions().filter(isPanelSwitcherAction)
        );
        this.state = proxy({ jumpThreadPresent: 0 });
        this.isDiscussContent = true;
        this.attClassObjectToString = attClassObjectToString;
        this.threadDisplayName = computed(() => this.thread?.displayName);
        this.threadDescription = computed(() => this.thread?.description);
        useOnChange(
            () => [this.thread],
            () => this.autoOpenPanel()
        );
        /** The panel on the side, kept while it narrows once closed. */
        this.sidePanel = signal(undefined);
        this.sidePanelTransition = useTransition({
            name: "o-mail-DiscussContent-panelTransition",
            initialVisibility: false,
            leaveDuration: PANEL_TRANSITION_DURATION,
        });
        useOnChange(
            () => [this.threadActions.activePanel],
            (panel) => {
                if (panel) {
                    this.sidePanel.set(panel);
                }
                this.sidePanelTransition.shouldMount = Boolean(panel);
            }
        );
        this.correspondentLocalDateTimeFormatted = computed(() =>
            this.store.localTimeIn(this.thread?.channel?.correspondent?.persona?.tz)
        );
        // The header and the panel on the side make room for the panel actions over them.
        useEffect(() => {
            const actionsEl = this.panelActionsRef();
            const rootEl = this.rootRef();
            if (!actionsEl || !rootEl) {
                return;
            }
            const observer = new ResizeObserver(() =>
                rootEl.style.setProperty(
                    "--o-mail-DiscussContent-panelActionsWidth",
                    `${actionsEl.offsetWidth}px`
                )
            );
            observer.observe(actionsEl);
            return () => {
                observer.disconnect();
                rootEl.style.removeProperty("--o-mail-DiscussContent-panelActionsWidth");
            };
        });
    }

    autoOpenPanel() {
        const memberListAction = this.threadActions.get("member-list");
        if (memberListAction && this.store.discuss.isMemberPanelOpenByDefault) {
            memberListAction.openPanel();
        }
    }

    /** @type {import("@mail/core/common/action_list").GetActionComponent} */
    getActionComponent() {}

    /**
     * The actions outside the panel switcher are circles without a background.
     *
     * @type {import("@mail/core/common/action_list").GetActionComponent}
     */
    getHeaderActionComponent(params) {
        return this.getActionComponent(params) ?? DiscussContentCircleAction;
    }

    /**
     * The compact panels open in a popover on their button, the others beside the conversation.
     *
     * @type {import("@mail/core/common/action_list").GetPanelContainer}
     */
    getPanelContainer({ action }) {
        switch (action.id) {
            case "notification-settings":
                return { ...this.panelPopover, fixedPosition: true, position: "bottom-end" };
        }
        if (action.definition.panel?.component.compact) {
            return this.panelPopover;
        }
    }

    /**
     * A popover on the button of the action, which looks like the dropdowns of Discuss.
     *
     * @returns {import("@mail/core/common/action").PanelContainer}
     */
    get panelPopover() {
        return {
            type: PANEL_CONTAINER_TYPE.POPOVER,
            popoverClass: this.store.discussDropdownMenuClass(this.ancestors),
        };
    }

    get thread() {
        return this.channel?.()?.thread || this.store.discuss.thread;
    }

    get isNotificationTabActive() {
        return Boolean(
            this.store.messagingMenu.notificationTab?.eq(this.store.discuss.sidebarState.activeTab)
        );
    }

    get showsChatLocalDateTime() {
        return (
            this.thread.channel?.channel_type === "chat" &&
            Boolean(this.correspondentLocalDateTimeFormatted())
        );
    }

    get isThreadAvatarEditable() {
        return (
            !this.thread.channel?.parent_channel_id &&
            this.thread.is_editable &&
            !this.thread.channel?.isReadonlyForSelf &&
            ["channel", "group"].includes(this.thread.channel?.channel_type)
        );
    }

    /** Whether an extra line is shown below the thread name in the header. */
    get hasHeaderSubline() {
        return this.showsChatLocalDateTime;
    }

    get threadNameAttClass() {
        return {
            "fw-bold flex-shrink-0 py-0": true,
            "fs-5": this.hasHeaderSubline,
            "fs-4": !this.hasHeaderSubline,
        };
    }

    get threadAvatarAttClass() {
        return {};
    }

    async onFileUploaded(file) {
        await this.thread.channel?.notifyAvatarToServer(file.data);
    }

    async renameThread(name) {
        await this.thread.channel.rename(name);
    }

    async updateThreadDescription(description) {
        const newDescription = description.trim();
        if (!newDescription && !this.thread.channel.description) {
            return;
        }
        if (newDescription !== this.thread.channel.description) {
            await this.thread.channel.notifyDescriptionToServer(newDescription);
        }
    }
}
