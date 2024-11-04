import { sprintf, escape } from "@web/core/utils/strings";
import { scrollTo } from "@web_editor/js/common/scrolling";

export function share(el, options) {
    const option = {
        shareLink: "http://twitter.com/intent/tweet?text=",
        minLength: 5,
        maxLength: 140,
        target: "blank",
        className: "share",
        placement: "top",
        ...options
    };
    let selectedText = "";

    function init(shareable) {
        shareable.addEventListener("mouseup", () => {
            if (!shareable.closest("body.editor_enable")) {
                popOver();
            }
        });
        shareable.addEventListener("mousedown", destroy);
    }

    function getContent() {
        const popoverContentEl = document.createElement("div");
        popoverContentEl.className = "h4 m-0";

        if (
            document.querySelector(
                ".o_wblog_title.js_comment, .o_wblog_post_content_field.js_comment"
            )
        ) {
            selectedText = getSelection("string");
            const btnEl = document.createElement("a");
            btnEl.className = "o_share_comment btn btn-link px-2";
            btnEl.href = "#";
            const iEl = document.createElement("i");
            iEl.className = "fa fa-lg fa-comment";
            btnEl.appendChild(iEl);
            popoverContentEl.appendChild(btnEl);
        }

        if (
            document.querySelector(".o_wblog_title.js_tweet, .o_wblog_post_content_field.js_tweet")
        ) {
            const tweet = '"%s" - %s';
            const baseLength = tweet.replace(/%s/g, "").length;
            const selectedTextShort = getSelection("string").substring(
                0,
                option.maxLength - baseLength - 23
            );

            const text = window.btoa(
                encodeURIComponent(sprintf(tweet, selectedTextShort, window.location.href))
            );

            const anchorEL = document.createElement("a");
            anchorEL.href = "#";
            anchorEL.classList.add("btn");
            anchorEL.addEventListener("click", () => {
                const decodedText = atob(text);
                window.open(
                    escape(option.shareLink) + decodedText,
                    `_${escape(option.target)}`,
                    "location=yes,height=570,width=520,scrollbars=yes,status=yes"
                );
            });
            const iconEl = document.createElement("i");
            iconEl.className = "ml4 mr4 fa fa-twitter fa-lg";
            anchorEL.appendChild(iconEl);
            popoverContentEl.appendChild(anchorEL);
        }

        return popoverContentEl;
    }

    function commentEdition() {
        const textareaEl = document.querySelector(".o_portal_chatter_composer_body textarea");
        if (textareaEl) {
            textareaEl.value = `"${selectedText}" `;
            textareaEl.focus();
        }
        const commentsEl = document.getElementById("o_wblog_post_comments");
        if (commentsEl) {
            scrollTo(commentsEl).then(() => {
                window.location.hash = "blog_post_comment_quote";
            });
        }
    }

    function getSelection(type) {
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

    function popOver() {
        destroy();
        if (getSelection("string").length < option.minLength) {
            return;
        }
        const data = getContent();
        const range = getSelection();

        const newNode = document.createElement("span");
        range.insertNode(newNode);
        newNode.className = option.className;

        const popover = Popover.getOrCreateInstance(newNode, {
            trigger: "manual",
            placement: option.placement,
            html: true,
            content: () => data,
        });

        popover.show();

        const shareCommentEl = document.querySelector(".o_share_comment");
        shareCommentEl?.addEventListener("click", commentEdition);
    }

    function destroy() {
        const spanEl = document.querySelector(`span.${option.className}`);
        if (spanEl) {
            const popover = Popover.getInstance(spanEl);
            if (popover) {
                popover.hide();
            }
            spanEl.remove();
        }
    }

    init(el);
}
