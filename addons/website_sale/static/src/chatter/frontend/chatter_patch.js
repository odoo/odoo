import { Chatter } from "@mail/chatter/web_portal/chatter";
import { patch } from "@web/core/utils/patch";

const chatterPatch = {
    get requestList() {
        return this.props.threadModel === "product.template"
            ? [...super.requestList, "ratingStats"]
            : super.requestList;
    },
};
patch(Chatter.prototype, chatterPatch);
