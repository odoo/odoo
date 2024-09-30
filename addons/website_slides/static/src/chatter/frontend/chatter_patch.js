import { Chatter } from "@mail/chatter/web_portal/chatter";
import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {
    get requestList() {
        const requestList = super.requestList;
        if (this.props.threadModel === "slide.channel") {
            requestList.push("ratingStats");
        }
        return requestList;
    },
});
