import { Thread } from "@mail/core/common/thread";
import { patch } from "@web/core/utils/patch";

const threadPatch = {
    get orderedMessages() {
        if (this.props.thread.model === "slide.channel" && this.env.inFrontendPortalChatter) {
            const messagesToDisplay = this.props.thread.messages.filter(
                (message) => !message.isEmpty
            );
            return this.props.order === "asc"
                ? [...messagesToDisplay]
                : [...messagesToDisplay].reverse();
        }
        return super.orderedMessages;
    },
};
patch(Thread.prototype, threadPatch);
