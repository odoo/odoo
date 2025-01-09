import { BlogShare } from "./blog_share";
import { registry } from "@web/core/registry";

import { scrollTo } from "@web_editor/js/common/scrolling";

export class BlogShareComment extends BlogShare {
    static selector = ".js_comment";

    makeContent() {
        const popoverContentEl = super.makeContent();
        this.shareCommentEl = this.makeButton(
            "o_share_comment btn btn-link px-2",
            "fa fa-lg fa-comment",
            "Comment with the quoted selection"
        );
        this.insert(this.shareCommentEl, popoverContentEl);
        return popoverContentEl;
    }

    updatePopoverSelection() {
        const selectedText = this.getSelectionRange("string");
        this.removeCommentListener?.();
        this.removeCommentListener = this.addListener(this.shareCommentEl, "click", () => {
            const textareaEl = document.querySelector("#chatterRoot")?.shadowRoot
                .querySelector(".o-mail-Composer-coreMain textarea");
            if (textareaEl) {
                textareaEl.value = `"${selectedText}"\n`;
                textareaEl.focus();
            }
            const commentsEl = document.getElementById("o_wblog_post_comments");
            if (commentsEl) {
                scrollTo(commentsEl);
            }
        });
    }
}

registry
    .category("public.interactions")
    .add("website_blog.blog_comment_share", BlogShareComment);
