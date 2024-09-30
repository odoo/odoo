import { Chatter } from "@mail/chatter/web_portal/chatter";
import { patch } from "@web/core/utils/patch";

const chatterPatch = {
    get requestList() {
        return this.state.thread.inPortal && this.props.threadModel === "slide.channel"
            ? [...super.requestList, "rating_stats"]
            : super.requestList;
    },
};
patch(Chatter.prototype, chatterPatch);
