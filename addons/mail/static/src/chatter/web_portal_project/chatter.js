import { useChildSubEnv, useRef, useState } from "@web/owl2/utils";
import { Composer } from "@mail/core/common/composer";
import { Thread } from "@mail/core/common/thread";
import { useMessageScrolling } from "@mail/utils/common/hooks";

import { Component, onMounted, onWillUpdateProps } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { router } from "@web/core/browser/router";
import { useService } from "@web/core/utils/hooks";
import { useThrottleForAnimation } from "@web/core/utils/timing";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class Chatter extends Component {
    static template = "mail.Chatter";
    static components = { Thread, Composer };
    static props = ["composer?", "threadId?", "threadModel", "twoColumns?"];
    static defaultProps = { composer: true, threadId: false, twoColumns: false };

    setup() {
        this.store = useService("mail.store");
        this.state = useState({
            jumpThreadPresent: 0,
            /** @type {import("models").Thread} */
            thread: undefined,
            aside: false,
            disabled: !this.props.threadId,
        });
        this.messageHighlight = useMessageScrolling();
        this.highlightMessage = router.current.highlight_message_id;
        this.rootRef = useRef("root");
        this.onScrollDebounced = useThrottleForAnimation(this.onScroll);
        useChildSubEnv(this.childSubEnv);

        onMounted(this._onMounted);
        onWillUpdateProps((nextProps) => {
            this.state.disabled = !nextProps.threadId;
            if (
                this.props.threadId !== nextProps.threadId ||
                this.props.threadModel !== nextProps.threadModel
            ) {
                this.changeThread(nextProps.threadModel, nextProps.threadId);
            }
            if (!this.env.chatter || this.env.chatter?.fetchThreadData) {
                if (this.env.chatter) {
                    this.env.chatter.fetchThreadData = false;
                }
                this.load(this.state.thread, this.requestList);
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

    get onCloseFullComposerRequestList() {
        return ["messages"];
    }

    get requestList() {
        return [];
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
                this.state.thread.messages.push({
                    id: this.store.getNextTemporaryId(),
                    author_id: this.state.thread.effectiveSelf,
                    body: _t("Creating a new record..."),
                    message_type: "notification",
                    thread: this.state.thread,
                    trackingValues: [],
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
        if (!thread.id || !this.state.thread?.eq(thread)) {
            return;
        }
        await thread.fetchThreadData(requestList);
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
        this.state.isTopStickyPinned = this.rootRef.el.scrollTop !== 0;
    }
}
