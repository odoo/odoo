import { useChildSubEnv, useSubEnv } from "@web/owl2/utils";
import { Composer } from "@mail/core/common/composer";
import { Thread } from "@mail/core/common/thread";
import { useMessageScrolling, useOnChange } from "@mail/utils/common/hooks";

import { Component, onMounted, props, proxy, signal, t } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { router } from "@web/core/browser/router";
import { useBus, useService } from "@web/core/utils/hooks";
import { useThrottleForAnimation } from "@web/core/utils/timing";

export class Chatter extends Component {
    static template = "mail.Chatter";
    static components = { Thread, Composer };

    setup() {
        this.store = useService("mail.store");
        this.props = props({
            composer: t.boolean().optional(true),
            threadId: t.or([t.number(), t.literal(false)]).optional(false),
            threadModel: t.string(),
            twoColumns: t.boolean().optional(false),
        });
        this.state = proxy({
            jumpThreadPresent: 0,
            /** @type {import("models").Thread} */
            thread: undefined,
        });
        this.messageHighlight = useMessageScrolling({
            thread: () => this.state.thread,
            messageFetchRouteParams: () => this.messageFetchRouteParams,
        });
        this.highlightMessage = router.current.highlight_message_id;
        this.rootRef = signal.ref(HTMLDivElement);
        this.onScrollDebounced = useThrottleForAnimation(this.onScroll);
        useChildSubEnv(this.childSubEnv);
        useSubEnv(this.subEnv);

        onMounted(this._onMounted);

        useOnChange(
            () => [this.props.threadId, this.props.threadModel],
            (threadId, threadModel) => this.changeThread(threadModel, threadId),
            { initialRun: false }
        );
        useOnChange(
            () => [this.state.thread],
            (thread) => {
                if (!this.env.chatter || this.env.chatter?.fetchThreadData) {
                    if (this.env.chatter) {
                        this.env.chatter.fetchThreadData = false;
                    }
                    this.load(thread, this.requestList);
                }
            },
            { initialRun: false }
        );
        // The useOnChange above only refetches when the thread identity changes.
        // A same-record form reload keeps the same thread, so we also refetch on
        // MAIL:RELOAD-THREAD to catch data that changed without a message_post
        // (e.g. an attachment created server-side). Mirrors the message refetch
        // in Thread.
        useBus(this.env.bus, "MAIL:RELOAD-THREAD", ({ detail }) => {
            const thread = this.state.thread;
            if (thread?.model === detail.model && thread?.id === detail.id) {
                this.load(thread, this.requestList);
            }
        });
    }

    get afterPostRequestList() {
        return ["messages"];
    }

    get childSubEnv() {
        return {
            inChatter: this.state,
            messageHighlight: this.messageHighlight,
        };
    }

    get extraMessageFetchRouteParams() {
        return {};
    }

    get messageFetchRouteParams() {
        return this.env.messageFetchRouteParams;
    }

    get onCloseFullComposerRequestList() {
        return this.state.thread.fullComposerCloseRequestList;
    }

    get requestList() {
        return [];
    }

    get subEnv() {
        return { messageFetchRouteParams: this.extraMessageFetchRouteParams };
    }

    changeThread(threadModel, threadId) {
        const data = {
            model: threadModel,
            id: threadId,
        };
        if (this.highlightMessage) {
            data.highlightMessage = this.highlightMessage;
        }
        this.state.thread = this.store["mail.thread"].insert(data);
        if (threadId === false) {
            if (this.state.thread.messages.length === 0) {
                const { effectiveSelf } = this.state.thread;
                const authorModelName = effectiveSelf.Model.getName();
                this.state.thread.messages.push({
                    id: this.store.getNextTemporaryId(),
                    is_transient: true,
                    author_id: authorModelName === "res.partner" ? effectiveSelf : undefined,
                    author_guest_id: authorModelName === "mail.guest" ? effectiveSelf : undefined,
                    body: _t("Creating a new record..."),
                    message_type: "notification",
                    thread: this.state.thread,
                    res_id: threadId,
                    model: threadModel,
                });
            }
        }
    }

    /**
     * Fetch data for the thread according to the request list.
     * @param {import("models").Thread} thread
     * @param {string[]} requestList
     */
    async load(thread, requestList) {
        if (!thread?.id || !this.state.thread?.eq(thread)) {
            return;
        }
        await thread.fetchThreadData(requestList, {
            messageFetchRouteParams: this.messageFetchRouteParams,
        });
    }

    onCloseFullComposerCallback() {
        this.load(this.state.thread, this.onCloseFullComposerRequestList);
    }

    _onMounted() {
        this.changeThread(this.props.threadModel, this.props.threadId);
        if (!this.env.chatter || this.env.chatter?.fetchThreadData) {
            if (this.env.chatter) {
                this.env.chatter.fetchThreadData = false;
            }
            this.load(this.state.thread, this.requestList);
        }
    }

    onPostCallback() {
        this.state.jumpThreadPresent++;
        // Load new messages to fetch potential new messages from other users (useful due to lack of auto-sync in chatter).
        this.load(this.state.thread, this.afterPostRequestList);
    }

    onScroll() {
        this.state.isTopStickyPinned = this.rootRef().scrollTop !== 0;
    }
}
