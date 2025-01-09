import { BlogShare } from "./blog_share";
import { registry } from "@web/core/registry";

import { sprintf } from "@web/core/utils/strings";

export class BlogShareTweet extends BlogShare {
    static selector = ".js_tweet";

    makeContent() {
        const popoverContentEl = super.makeContent();
        this.shareTweetEl = this.makeButton(
            "btn", "ml4 mr4 fa fa-twitter fa-lg", "Tweet the selection"
        );
        this.insert(this.shareTweetEl, popoverContentEl);
        return popoverContentEl;
    }

    updatePopoverSelection() {
        const tweet = '"%s" - %s';
        const baseLength = tweet.replace(/%s/g, "").length;
        const selectedTextShort = this.getSelectionRange("string").substring(
            0,
            this.options.maxLength - baseLength - 23
        );
        const text = window.btoa(
            encodeURIComponent(sprintf(tweet, selectedTextShort, window.location.href))
        );
        this.removeTweetListener?.();
        this.removeTweetListener = this.addListener(this.shareTweetEl, "click", () => {
            const decodedText = atob(text);
            window.open(
                "http://twitter.com/intent/tweet?text=" + decodedText,
                "_blank",
                "location=yes,height=570,width=520,scrollbars=yes,status=yes"
            );
        });
    }
}

registry
    .category("public.interactions")
    .add("website_blog.blog_tweet_share", BlogShareTweet);
