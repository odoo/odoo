/** @odoo-module **/

import { sprintf } from "@web/core/utils/strings";
import dom from "@web/legacy/js/core/dom";

Element.prototype.share = function (options) {
    const option = Object.assign(Element.prototype.share.defaults, options);
    var selected_text = "";
    Object.assign(Element.prototype.share, {
        init: function (shareable) {
            var self = this;
            Element.prototype.share.defaults.shareable = shareable;
            Element.prototype.share.defaults.shareable.addEventListener("mouseup", function () {
                if (!this.closest("body.editor_enable")) {
                    self.popOver();
                }
            });
            Element.prototype.share.defaults.shareable.addEventListener("mousedown", function () {
                self.destroy();
            });
        },
        getContent: function () {
            const popoverContentEl = document.createElement("div");
            popoverContentEl.className = "h4 m-0";
            if (
                document.querySelector(
                    ".o_wblog_title.js_comment, .o_wblog_post_content_field.js_comment"
                )
            ) {
                selected_text = this.getSelection("string");
                const btnEl = document.createElement("a");
                btnEl.className = "o_share_comment btn btn-link px-2";
                btnEl.href = "#";
                const iEl = document.createElement("i");
                iEl.className = "fa fa-lg fa-comment";
                btnEl.appendChild(iEl);
                popoverContentEl.appendChild(btnEl);
            }
            if (
                document.querySelector(
                    ".o_wblog_title.js_tweet, .o_wblog_post_content_field.js_tweet"
                )
            ) {
                var tweet = '"%s" - %s';
                var baseLength = tweet.replace(/%s/g, '').length;
                // Shorten the selected text to match the tweet max length
                // Note: all (non-localhost) urls in a tweet have 23 characters https://support.twitter.com/articles/78124
                var selectedText = this.getSelection('string').substring(0, option.maxLength - baseLength - 23);

                var text = window.btoa(encodeURIComponent(sprintf(tweet, selectedText, window.location.href)));
                popoverContentEl.innerHTML += sprintf(
                    "<a onclick=\"window.open('%s' + atob('%s'), '_%s','location=yes,height=570,width=520,scrollbars=yes,status=yes')\"><i class=\"ml4 mr4 fa fa-twitter fa-lg\"/></a>",
                    option.shareLink,
                    text,
                    option.target
                );
            }
            return popoverContentEl;
        },
        commentEdition: function () {
            const textareaEl = document.querySelector(".o_portal_chatter_composer_body textarea");
            if (textareaEl) {
                textareaEl.value = '"' + selected_text + '" ';
                textareaEl.focus();
            }
            const commentsEl = document.getElementById("o_wblog_post_comments");
            if (commentsEl) {
                dom.scrollTo(commentsEl).then(() => {
                    window.location.hash = 'blog_post_comment_quote';
                });
            }
        },
        getSelection: function (share) {
            if (window.getSelection) {
                var selection = window.getSelection();
                if (!selection || selection.rangeCount === 0) {
                    return "";
                }
                if (share === 'string') {
                    return String(selection.getRangeAt(0)).replace(/\s{2,}/g, ' ');
                } else {
                    return selection.getRangeAt(0);
                }
            } else if (document.selection) {
                if (share === 'string') {
                    return document.selection.createRange().text.replace(/\s{2,}/g, ' ');
                } else {
                    return document.selection.createRange();
                }
            }
        },
        popOver: function () {
            this.destroy();
            if (this.getSelection('string').length < option.minLength) {
                return;
            }
            var data = this.getContent();
            var range = this.getSelection();

            var newNode = document.createElement("span");
            range.insertNode(newNode);
            newNode.className = option.className;
            const popover = Popover.getOrCreateInstance(newNode, {
                trigger: 'manual',
                placement: option.placement,
                html: true,
                content: function () {
                    return data;
                }
            });
            popover.show();
            const shareCommentEl = document.querySelector(".o_share_comment");
            shareCommentEl?.addEventListener("click", this.commentEdition);
        },
        destroy: function () {
            const spanEl = document.querySelector("span." + option.className);
            if (spanEl) {
                const popover = Popover.getInstance(spanEl);
                if (popover) {
                    popover.hide();
                }
                spanEl.remove();
            }
        }
    });
    Element.prototype.share.init(this);
};

Element.prototype.share.defaults = {
    shareLink: "http://twitter.com/intent/tweet?text=",
    minLength: 5,
    maxLength: 140,
    target: "blank",
    className: "share",
    placement: "top",
};
