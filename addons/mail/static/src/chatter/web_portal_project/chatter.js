import { useSubEnv } from "@web/owl2/utils";
import { ChatterStatePlugin } from "@mail/core/common/chatter_state_plugin";
import { Composer } from "@mail/core/common/composer";
import { Thread } from "@mail/core/common/thread";
import { propComputed, useMessageScrolling } from "@mail/utils/common/hooks";

import { Component, onMounted, providePlugins, signal, t, useOnChange, usePlugin } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { router } from "@web/core/browser/router";
import { useBus, useService } from "@web/core/utils/hooks";
import { useThrottleForAnimation } from "@web/core/utils/timing";

export class Chatter extends Component {
    static template = "mail.Chatter";
    static components = { Thread, Composer };

    setup() {
        this.store = useService("mail.store");
        this.composer = propComputed("composer", t.boolean().optional(true));
        this.threadId = propComputed(
            "threadId",
            t.or([t.number(), t.literal(false)]).optional(false)
        );
        this.threadModel = propComputed("threadModel", t.string());
        this.twoColumns = propComputed("twoColumns", t.boolean().optional(false));
        providePlugins([ChatterStatePlugin]);
        this.state = usePlugin(ChatterStatePlugin);
        this.messageHighlight = useMessageScrolling({
            thread: () => this.state.thread(),
            messageFetchRouteParams: () => this.messageFetchRouteParams,
        });
        this.highlightMessage = router.current.highlight_message_id;
        this.rootRef = signal.ref(HTMLDivElement);
        this.topRef = signal.ref(HTMLDivElement);
        this.onScrollDebounced = useThrottleForAnimation(this.onScroll.bind(this));
        useSubEnv(this.subEnv);

        onMounted(this._onMounted);

        useOnChange(
            () => [this.threadId(), this.threadModel()],
            (threadId, threadModel) => this.changeThread(threadModel, threadId),
            { initialRun: false }
        );
        useOnChange(
            () => [this.state.thread()],
            (thread) => {
                if (!this.env.chatter || this.env.chatter?.fetchThreadData) {
                    if (this.env.chatter) {
                        this.env.chatter.fetchThreadData = false;
                    }
                    this.load(thread, this.initialRequestList);
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
            const thread = this.state.thread();
            if (thread?.model === detail.model && thread?.id === detail.id) {
                this.load(thread, this.requestList);
            }
        });
    }

    get afterPostRequestList() {
        return ["messages"];
    }

    get extraMessageFetchRouteParams() {
        return {};
    }

    get messageFetchRouteParams() {
        return this.env.messageFetchRouteParams;
    }

    get onCloseFullComposerRequestList() {
        return this.state.thread().fullComposerCloseRequestList;
    }

    get initialRequestList() {
        return [...this.requestList, "messages"];
    }

    get requestList() {
        return [];
    }

    get subEnv() {
        return {
            inChatter: true,
            messageFetchRouteParams: this.extraMessageFetchRouteParams,
            messageHighlight: this.messageHighlight,
        };
    }

    changeThread(threadModel, threadId) {
        const data = {
            model: threadModel,
            id: threadId,
        };
        if (this.highlightMessage) {
            data.highlightMessage = this.highlightMessage;
        }
        this.state.thread.set(this.store["mail.thread"].insert(data));
        if (threadId === false) {
            this.state.thread().isLoaded = true;
            this.state.thread().status = "ready";
            if (this.state.thread().messages.length === 0) {
                const { effectiveSelf } = this.state.thread();
                const authorModelName = effectiveSelf.Model.getName();
                this.state.thread().messages.push({
                    id: this.store.getNextTemporaryId(),
                    is_transient: true,
                    author_id: authorModelName === "res.partner" ? effectiveSelf : undefined,
                    author_guest_id: authorModelName === "mail.guest" ? effectiveSelf : undefined,
                    body: _t("Creating a new record..."),
                    message_type: "notification",
                    thread: this.state.thread(),
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
        if (!thread?.id || !this.state.thread()?.eq(thread)) {
            return;
        }
        await thread.fetchThreadData(requestList, {
            messageFetchRouteParams: this.messageFetchRouteParams,
        });
    }

    onCloseFullComposerCallback() {
        this.load(this.state.thread(), this.onCloseFullComposerRequestList);
    }

    _onMounted() {
        this.changeThread(this.threadModel(), this.threadId());
        if (!this.env.chatter || this.env.chatter?.fetchThreadData) {
            if (this.env.chatter) {
                this.env.chatter.fetchThreadData = false;
            }
            this.load(this.state.thread(), this.initialRequestList);
        }
    }

    onPostCallback() {
        this.state.incrementJumpThreadPresent();
        // Load new messages to fetch potential new messages from other users (useful due to lack of auto-sync in chatter).
        this.load(this.state.thread(), this.afterPostRequestList);
    }

    onScroll() {
        this.state.isTopStickyPinned.set(this.rootRef().scrollTop !== 0);
    }
}
