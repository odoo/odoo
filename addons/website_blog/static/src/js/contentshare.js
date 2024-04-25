/** @odoo-module **/

import { sprintf } from "@web/core/utils/strings";
import dom from "@web/legacy/js/core/dom";

Element.prototype.share = function (options) {
    var option = Object.assign(Element.prototype.share.defaults, options);
    var selected_text = "";
    Object.assign(Element.prototype.share, {
        init: function (shareable) {
            var self = this;
            Element.prototype.share.defaults.shareable = shareable;
            Element.prototype.share.defaults.shareable.addEventListener('mouseup', function () {
                if (!this.closest('body.editor_enable')) {
                    self.popOver();
                }
            });
            Element.prototype.share.defaults.shareable.addEventListener('mousedown', function () {
                self.destroy();
            });
        },
        getContent: function () {
            var popover_content = document.createElement('div');
            popover_content.className = 'h4 m-0';
            if (document.querySelector('.o_wblog_title.js_comment, .o_wblog_post_content_field.js_comment')) {
                selected_text = this.getSelection('string');
                var btn_c = document.createElement('a');
                btn_c.className = 'o_share_comment btn btn-link px-2';
                btn_c.href = '#';
                var i = document.createElement('i');
                i.className = 'fa fa-lg fa-comment';
                btn_c.appendChild(i);
                popover_content.appendChild(btn_c);
            }
            if (document.querySelector('.o_wblog_title.js_tweet, .o_wblog_post_content_field.js_tweet')) {
                var tweet = '"%s" - %s';
                var baseLength = tweet.replace(/%s/g, '').length;
                var selectedText = this.getSelection('string').substring(0, option.maxLength - baseLength - 23);

                var text = window.btoa(encodeURIComponent(sprintf(tweet, selectedText, window.location.href)));
                popover_content.innerHTML += sprintf(
                    "<a onclick=\"window.open('%s' + atob('%s'), '_%s','location=yes,height=570,width=520,scrollbars=yes,status=yes')\"><i class=\"ml4 mr4 fa fa-twitter fa-lg\"/></a>",
                    option.shareLink, text, option.target);
            }
            return popover_content;
        },
        commentEdition: function () {
            document.querySelector(".o_portal_chatter_composer_form textarea").value = '"' + selected_text + '" ';
            document.querySelector(".o_portal_chatter_composer_form textarea").focus();
            const commentsEl = document.getElementById('o_wblog_post_comments');
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
            const popover = new Popover(newNode, {
                trigger: 'manual',
                placement: option.placement,
                html: true,
                content: function () {
                    return data;
                }
            });
            popover.show();
            document.querySelector('.o_share_comment').addEventListener('click', this.commentEdition);
        },
        destroy: function () {
            var span = document.querySelector('span.' + option.className);
            span.hide();
            span.parentNode.removeChild(span);
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
