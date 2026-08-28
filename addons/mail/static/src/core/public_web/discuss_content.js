import { Component, computed, proxy, signal, types, useOnChange, useProps } from "@odoo/owl";

import { useThreadActions } from "@mail/core/common/thread_actions";
import { AutoresizeInput } from "@mail/core/common/autoresize_input";
import { ActionList } from "@mail/core/common/action_list";
import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { Thread } from "@mail/core/common/thread";
import { ThreadIcon } from "@mail/core/common/thread_icon";
import { Composer } from "@mail/core/common/composer";
import { attClassObjectToString } from "@mail/utils/common/format";

import { FileUploader } from "@web/views/fields/file_handler";
import { useService } from "@web/core/utils/hooks";
import { AUTORESIZE_NUDGE_EVENT } from "@web/core/utils/autoresize";

export class DiscussContent extends Component {
    static components = {
        ActionList,
        AutoresizeInput,
        DiscussAvatar,
        Thread,
        ThreadIcon,
        Composer,
        FileUploader,
    };
    static template = "mail.DiscussContent";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({
            thread: types.instanceOf(this.store["mail.thread"]).optional(),
        });
        this.ui = useService("ui");
        this.notification = useService("notification");
        this.rootRef = signal.ref(HTMLDivElement);
        this.threadAvatarRef = signal.ref(HTMLDivElement);
        this.headerInfoRef = signal.ref(HTMLDivElement);
        this.threadNameInputRef = signal.ref(HTMLInputElement);
        this.threadDescriptionInputRef = signal.ref(HTMLInputElement);
        this.headerBoxWidth = this.useHeaderBoxWidth();
        this.threadActions = useThreadActions({ rootRef: this.rootRef, thread: () => this.thread });
        this.headerActionsList = computed(() => {
            const partition = this.threadActions.partition;
            return [partition.quick, partition.other, ...partition.group.slice().reverse()];
        });
        this.state = proxy({ jumpThreadPresent: 0 });
        this.isDiscussContent = true;
        this.attClassObjectToString = attClassObjectToString;
        this.selfGuestName = computed(() => this.store.self_guest?.name);
        this.threadDisplayName = computed(() => this.thread?.displayName);
        this.threadDescription = computed(() => this.thread?.description);
        useOnChange(
            () => [this.thread],
            () => this.actionPanelAutoOpenFn()
        );
        this.correspondentLocalDateTimeFormatted = computed(() =>
            this.store.localTimeIn(this.thread?.channel?.correspondent?.persona?.tz)
        );
    }

    /**
     * Computes the width of the header's decorative box so it hugs the
     * channel name/description `AutoresizeInput`s.
     *
     * This can't just be `width: fit-content` on the box's own container:
     * `AutoresizeInput`s measure themselves by momentarily going
     * `width: 100%` and reading back the available space, which requires a
     * genuinely full-width ancestor (`this.headerInfoRef`) - so the box is
     * instead drawn separately (absolutely positioned) and sized from here.
     *
     * Same reason the inputs need a nudge: their first measurement (on mount
     * or thread change) can be inaccurate and never self-corrects, so
     * dispatch `AUTORESIZE_NUDGE_EVENT` next frame to force a re-measure, keyed
     * off `this.thread` rather than the input refs, since Owl reuses the
     * same `<input>` element across a thread change.
     *
     * @returns {import("@odoo/owl").ReactiveValue<number|undefined>} the
     *  width (in px), or `undefined` while there's nothing to measure yet.
     */
    useHeaderBoxWidth() {
        const width = signal();
        useOnChange(
            () => [
                this.headerInfoRef(),
                this.threadNameInputRef(),
                this.threadDescriptionInputRef(),
            ],
            (headerInfoEl, ...inputEls) => {
                inputEls = inputEls.filter(Boolean);
                if (!headerInfoEl || !inputEls.length) {
                    width.set(undefined);
                    return;
                }
                const measure = () => {
                    const siblings = inputEls[0].parentElement?.children;
                    if (!siblings) {
                        // probably detached, so ignored.
                        return;
                    }
                    const headerInfoRect = headerInfoEl.getBoundingClientRect();
                    const right = Math.max(
                        ...[...siblings].map((el) => el.getBoundingClientRect().right)
                    );
                    const contentEl = [...headerInfoEl.children].find(
                        (el) => getComputedStyle(el).position !== "absolute"
                    );
                    const trailingPadding = contentEl
                        ? parseFloat(getComputedStyle(contentEl).paddingInlineEnd) || 0
                        : 0;
                    width.set(Math.ceil(right - headerInfoRect.left) + trailingPadding);
                };
                measure();
                const resizeObserver = new ResizeObserver(measure);
                resizeObserver.observe(headerInfoEl);
                for (const el of inputEls) {
                    resizeObserver.observe(el);
                }
                return () => resizeObserver.disconnect();
            }
        );
        /** @see {@link import("@mail/../tests/discuss_app/discuss.test").NudgeRegressionTest} */
        useOnChange(
            () => [this.threadNameInputRef(), this.threadDescriptionInputRef(), this.thread],
            (nameEl, descEl) => {
                const inputEls = [nameEl, descEl].filter(Boolean);
                if (!inputEls.length) {
                    return;
                }
                const handle = requestAnimationFrame(() => {
                    for (const el of inputEls) {
                        el.dispatchEvent(new Event(AUTORESIZE_NUDGE_EVENT));
                    }
                });
                return () => cancelAnimationFrame(handle);
            }
        );
        return width;
    }

    headerBoxStyle() {
        const width = this.headerBoxWidth();
        return width ? `width: ${width}px` : "right: 0";
    }

    actionPanelAutoOpenFn() {
        const memberListAction = this.threadActions.actions.find((a) => a.id === "member-list");
        if (memberListAction && this.store.discuss.isMemberPanelOpenByDefault) {
            memberListAction.actionPanelOpen();
        }
    }

    get thread() {
        return this.props.thread || this.store.discuss.thread;
    }

    get isNotificationTabActive() {
        return Boolean(
            this.store.messagingMenu.notificationTab?.eq(this.store.discuss.sidebarState.activeTab)
        );
    }

    get showsChatLocalDateTime() {
        return (
            this.thread.channel?.channel_type === "chat" &&
            this.correspondentLocalDateTimeFormatted()
        );
    }

    get showThreadAvatar() {
        return (
            ["channel", "group"].includes(this.thread.channel?.channel_type) ||
            this.thread.channel?.hasCorrespondentAvatar
        );
    }

    get isThreadAvatarEditable() {
        return (
            !this.thread.channel?.parent_channel_id &&
            this.thread.is_editable &&
            ["channel", "group"].includes(this.thread.channel?.channel_type)
        );
    }

    get threadAvatarAttClass() {
        return {};
    }

    async onFileUploaded(file) {
        await this.thread.channel?.notifyAvatarToServer(file.data);
    }

    async renameGuest(name) {
        const newName = name.trim();
        if (this.store.self_guest.name !== newName) {
            await this.store.self_guest.updateGuestName(newName);
        }
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
