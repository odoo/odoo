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

/**
 * @param {HTMLElement} clone a clone of `this.headerContentRef`'s element
 */
function sanitizeGhostClone(clone) {
    // Excludes the ghost from tests scoping selectors under this class to target the real content.
    clone.classList.remove("o-mail-DiscussContent-headerContent");
    // Avoids duplicate `id`s stealing `url(#id)` references (e.g. the avatar's SVG mask) from the real content.
    for (const el of [clone, ...clone.querySelectorAll("[id]")]) {
        el.removeAttribute("id");
    }
}

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
        this.headerContentRef = signal.ref(HTMLDivElement);
        this.headerGhostOuterRef = signal.ref(HTMLDivElement);
        this.headerGhostRef = signal.ref(HTMLDivElement);
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
     * Computes the width of the header's decorative box so it hugs its content
     * (channel name/description, subtitle).
     *
     * `this.headerContentRef` can't be measured directly: it's `flex-grow-1`, which
     * `AutoresizeInput` itself relies on to measure its own width. So instead
     * it's cloned into an off-screen ghost, free to size itself with
     * `width: fit-content`, and the box is sized to match that.
     *
     * @returns {import("@odoo/owl").Signal<number|undefined>} the width (in
     *  px), or `undefined` while there's nothing to measure yet.
     */
    useHeaderBoxWidth() {
        const width = signal();
        useOnChange(
            () => [this.headerInfoRef(), this.headerGhostOuterRef()],
            (infoEl, outerEl) => {
                if (!infoEl || !outerEl) {
                    return;
                }
                const sync = () => {
                    outerEl.style.width = `${infoEl.getBoundingClientRect().width}px`;
                };
                sync();
                const resizeObserver = new ResizeObserver(sync);
                resizeObserver.observe(infoEl);
                return () => resizeObserver.disconnect();
            }
        );
        useOnChange(
            () => [this.headerContentRef(), this.headerGhostRef()],
            (contentEl, ghostEl) => {
                if (!contentEl || !ghostEl) {
                    width.set(undefined);
                    return;
                }
                const render = () => {
                    const clone = contentEl.cloneNode(true);
                    sanitizeGhostClone(clone);
                    ghostEl.replaceChildren(clone);
                };
                render();
                const measure = () => width.set(Math.ceil(ghostEl.getBoundingClientRect().width));
                measure();
                const mutationObserver = new MutationObserver(render);
                mutationObserver.observe(contentEl, {
                    childList: true,
                    subtree: true,
                    attributes: true,
                    characterData: true,
                });
                contentEl.addEventListener("input", render);
                const resizeObserver = new ResizeObserver(measure);
                resizeObserver.observe(ghostEl);
                return () => {
                    mutationObserver.disconnect();
                    contentEl.removeEventListener("input", render);
                    resizeObserver.disconnect();
                };
            }
        );
        /**
         * Nudges the inputs to re-measure after a thread change: Owl reuses the same
         * `<input>`, so their first measurement can be stale and never self-corrects.
         * @see {@link import("@mail/../tests/discuss_app/discuss.test").NudgeRegressionTest}
         */
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
