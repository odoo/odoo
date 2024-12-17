import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { sprintf } from "@web/core/utils/strings";
import { scrollTo } from "@web_editor/js/common/scrolling";
import { Interaction } from "@web/public/interaction";

export class BlogContentShare extends Interaction {
    static selector = ".js_comment, .js_tweet";

    dynamicContent = {
        "_root": { "t-on-mouseup": this.showPopover },
        "_window": { "t-on-mousedown": this.hidePopover },
    };

    setup() {
        this.isCommentActive = this.el.matches(".js_comment");
        this.isTweetActive = this.el.matches(".js_tweet");

        this.options = {
            minLength: 5,
            maxLength: 140,
        };
        this.bsPopover = null;
        this.shareCommentEl = null;
        this.shareTweetEl = null;
        this.removeCommentListener = null;
        this.removeTweetListener = null;
        this.popoverContentEl = null;
    }

    showPopover() {
        if (this.getSelectionRange("string").length < this.options.minLength) {
            return;
        }
        const popoverEl = document.createElement("span");
        popoverEl.classList.add("share");
        this.popoverContentEl ||= this.makeContent();
        this.updatePopoverSelection();

        const range = this.getSelectionRange();
        range.insertNode(popoverEl);

        this.bsPopover = Popover.getOrCreateInstance(popoverEl, {
            trigger: "manual",
            placement: "top",
            html: true,
            content: () => this.popoverContentEl,
        });

        this.bsPopover.show();
        this.registerCleanup(() => {
            this.bsPopover.hide();
            this.bsPopover.dispose();
            popoverEl.remove();
        });
    }

    hidePopover() {
        if (this.bsPopover) {
            this.bsPopover.hide();
        }
    }

    /**
     * @param {"string" | null} type - whether to return a string or a Range
     * @returns {"string" | Range}
     */
    getSelectionRange(type) {
        const selection = window.getSelection();
        if (!selection || selection.rangeCount === 0) {
            return "";
        }
        if (type === "string") {
            return String(selection.getRangeAt(0)).replace(/\s{2,}/g, " ");
        } else {
            return selection.getRangeAt(0);
        }
    }

    makeContent() {
        const popoverContentEl = document.createElement("div");
        popoverContentEl.className = "h4 m-0";

        if (this.isCommentActive) {
            this.shareCommentEl = this.makeButton(
                "o_share_comment btn btn-link px-2",
                "fa fa-lg fa-comment",
                "Comment with the quoted selection"
            );
            this.insert(this.shareCommentEl, popoverContentEl, "beforeend");
        }
        if (this.isTweetActive) {
            this.shareTweetEl = this.makeButton(
                "btn", "ml4 mr4 fa fa-twitter fa-lg", "Tweet the selection"
            );
            this.insert(this.shareTweetEl, popoverContentEl, "beforeend");
        }
        return popoverContentEl;
    }

    updatePopoverSelection() {
        if (this.isCommentActive) {
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
        if (this.isTweetActive) {
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

    /**
     * @param {string} btnClasses
     * @param {string} iconClasses
     * @param {string} iconTitle
     */
    makeButton(btnClasses, iconClasses, iconTitle) {
        const btnEl = document.createElement("button");
        btnEl.className = btnClasses;
        const iconEl = document.createElement("span");
        iconEl.className = iconClasses;
        iconEl.title = iconEl.ariaLabel = _t(iconTitle);
        iconEl.role = "img";
        btnEl.appendChild(iconEl);
        return btnEl;
    }
}

registry
    .category("public.interactions")
    .add("website_blog.blog_content_share", BlogContentShare);
