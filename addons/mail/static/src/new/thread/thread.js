/** @odoo-module */

import { Component, onMounted, onPatched, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useMessaging } from "../messaging_hook";
import { useAutoScroll, useVisible } from "../utils";
import { Message } from "./message";

export class Thread extends Component {
    setup() {
        this.messaging = useMessaging();
        if (!this.env.inChatter) {
            useAutoScroll(
                "messages",
                () =>
                    !this.props.messageHighlight ||
                    !this.props.messageHighlight.highlightedMessageId
            );
        }
        this.loadMoreState = useVisible("load-more", () => this.loadMore());
        onMounted(() => this.loadMore());
        onPatched(() => this.loadMore());
        onWillStart(() => this.requestMessages(this.props.id));
        onWillUpdateProps((nextProps) => this.requestMessages(nextProps.id));
    }

    loadMore() {
        if (this.loadMoreState.isVisible) {
            this.messaging.fetchThreadMessagesMore(this.props.id);
        }
    }

    requestMessages(threadId) {
        // does not return the promise, so the thread is immediately rendered
        // then updated whenever messages get here
        this.messaging.fetchThreadMessagesNew(threadId);
    }

    isGrayedOut(msg) {
        const { messageToReplyTo } = this.messaging.discuss;
        return (
            messageToReplyTo &&
            messageToReplyTo.id !== msg.id &&
            messageToReplyTo.resId === msg.resId
        );
    }

    isSquashed(msg, prevMsg) {
        if (
            !prevMsg ||
            prevMsg.type === "notification" ||
            this.messaging.isMessageEmpty(prevMsg) ||
            this.env.inChatter
        ) {
            return false;
        }

        if (msg.author.id !== prevMsg.author.id) {
            return false;
        }
        if (msg.resModel !== prevMsg.resModel || msg.resId !== prevMsg.resId) {
            return false;
        }
        if (msg.parentMessage) {
            return false;
        }
        return msg.dateTime.ts - prevMsg.dateTime.ts < 60 * 1000;
    }
}

Object.assign(Thread, {
    components: { Message },
    props: ["id", "messageHighlight?", "order?"],
    defaultProps: {
        order: "asc", // 'asc' or 'desc'
    },
    template: "mail.thread",
});
