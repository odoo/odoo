import { useChildSubEnv, useSubEnv } from "@web/owl2/utils";
import { Composer } from "@mail/core/common/composer";
import { Thread } from "@mail/core/common/thread";
import { useMessageScrolling, useOnChange } from "@mail/utils/common/hooks";

import { Component, onMounted, props, proxy, signal, t } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { router } from "@web/core/browser/router";
import { useService } from "@web/core/utils/hooks";
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
        this.thread = signal();
        useOnChange(
            () => [this.props.threadId, this.props.threadModel],
            (threadId, threadModel) => this.onChangeThread(threadId, threadModel),
            { initialRun: false }
        );
        onMounted(() => this.onChangeThread(this.props.threadId, this.props.threadModel));

        this.state = proxy({
            jumpThreadPresent: 0,
        });
        this.messageHighlight = useMessageScrolling({
            thread: this.thread,
            messageFetchRouteParams: () => this.messageFetchRouteParams,
        });
        this.highlightMessage = router.current.highlight_message_id;
        this.rootRef = signal.ref(HTMLDivElement);
        this.onScrollDebounced = useThrottleForAnimation(this.onScroll);
        useChildSubEnv(this.childSubEnv);
        useSubEnv(this.subEnv);
    }

    onChangeThread(threadId, threadModel) {
        this.thread.set(
            this.store["mail.thread"].insert({
                model: threadModel,
                id: threadId,
                highlightMessage: this.highlightMessage,
            })
        );
        if (threadId === false) {
            if (this.thread().messages.length === 0) {
                const { effectiveSelf } = this.thread();
                const authorModelName = effectiveSelf.Model.getName();
                this.thread().messages.push({
                    id: this.store.getNextTemporaryId(),
                    is_transient: true,
                    author_id: authorModelName === "res.partner" ? effectiveSelf : undefined,
                    author_guest_id: authorModelName === "mail.guest" ? effectiveSelf : undefined,
                    body: _t("Creating a new record..."),
                    message_type: "notification",
                    thread: this.thread(),
                    res_id: threadId,
                    model: threadModel,
                });
            }
        }
        if (!this.env.chatter || this.env.chatter?.fetchThreadData) {
            if (this.env.chatter) {
                this.env.chatter.fetchThreadData = false;
            }
            this.load(this.thread(), this.requestList);
        }
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
        return this.thread().fullComposerCloseRequestList;
    }

    get requestList() {
        return [];
    }

    get subEnv() {
        return { messageFetchRouteParams: this.extraMessageFetchRouteParams };
    }

    /**
     * Fetch data for the thread according to the request list.
     * @param {import("models").Thread} thread
     * @param {string[]} requestList
     */
    async load(thread, requestList) {
        if (!thread?.id || !this.thread()?.eq(thread)) {
            return;
        }
        await thread.fetchThreadData(requestList, {
            messageFetchRouteParams: this.messageFetchRouteParams,
        });
    }

    onCloseFullComposerCallback() {
        this.load(this.thread(), this.onCloseFullComposerRequestList);
    }

    onPostCallback() {
        this.state.jumpThreadPresent++;
        // Load new messages to fetch potential new messages from other users (useful due to lack of auto-sync in chatter).
        this.load(this.thread(), this.afterPostRequestList);
    }

    onScroll() {
        this.state.isTopStickyPinned = this.rootRef().scrollTop !== 0;
    }
}
