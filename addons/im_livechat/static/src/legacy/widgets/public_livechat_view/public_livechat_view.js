/** @odoo-module **/

import * as mailUtils from '@mail/js/utils';

import core from 'web.core';
import time from 'web.time';
import Widget from 'web.Widget';

const QWeb = core.qweb;
const _lt = core._lt;

const ORDER = {
    ASC: 1, // visually, ascending order of message IDs (from top to bottom)
    DESC: -1, // visually, descending order of message IDs (from top to bottom)
};

const READ_MORE = _lt("read more");
const READ_LESS = _lt("read less");

/**
 * This is a generic widget to render a thread.
 * Any thread that extends mail.model.AbstractThread can be used with this
 * widget.
 */
const PublicLivechatView = Widget.extend({
    className: 'o_mail_thread',

    events: {
        'click a': '_onClickRedirect',
        'click img': '_onClickRedirect',
        'click strong': '_onClickRedirect',
        'click .o_thread_show_more': '_onClickShowMore',
        'click .o_thread_message_needaction': '_onClickMessageNeedaction',
        'click .o_thread_message_star': '_onClickMessageStar',
        'click .o_thread_message_reply': '_onClickMessageReply',
        'click .oe_mail_expand': '_onClickMailExpand',
        'click .o_thread_message': '_onClickMessage',
        'click': '_onClick',
        'click .o_thread_message_notification_error': '_onClickMessageNotificationError',
    },

    /**
     * @override
     * @param {widget} parent
     * @param {Messaging} messaging
     * @param {Object} options
     */
    init(parent, messaging, options) {
        this._super(...arguments);
        this.messaging = messaging;
        // options when the thread is enabled (e.g. can send message,
        // interact on messages, etc.)
        this._enabledOptions = _.defaults(options || {}, {
            displayOrder: ORDER.ASC,
            displayMarkAsRead: true,
            displayDocumentLinks: true,
            displayAvatars: true,
            squashCloseMessages: true,
            loadMoreOnScroll: false,
        });
        this._selectedMessageID = null;
        this._currentThreadID = null;
    },
    /**
     * The message mail popover may still be shown at this moment. If we do not
     * remove it, it stays visible on the page until a page reload.
     *
     * @override
     */
    destroy() {
        clearInterval(this._updateTimestampsInterval);
        this._super();
    },
    /**
     * @param {Object} [options]
     * @param {integer} [options.displayOrder=ORDER.ASC] order of displaying
     *    messages in the thread:
     *      - ORDER.ASC: last message is at the bottom of the thread
     *      - ORDER.DESC: last message is at the top of the thread
     * @param {boolean} [options.displayLoadMore]
     * @param {Array} [options.domain=[]] the domain for the messages in the
     *    thread.
     * @param {boolean} [options.scrollToBottom=false]
     * @param {boolean} [options.squashCloseMessages]
     */
    render(options) {
        let shouldScrollToBottomAfterRendering = false;
        if (this._currentThreadID === this.messaging.publicLivechatGlobal.publicLivechat.id && this.isAtBottom()) {
            shouldScrollToBottomAfterRendering = true;
        }
        this._currentThreadID = this.messaging.publicLivechatGlobal.publicLivechat.id;

        // copy so that reverse do not alter order in the thread object
        const messages = _.clone(this.messaging.publicLivechatGlobal.publicLivechat.widget.getMessages());

        const modeOptions = this._enabledOptions;

        options = Object.assign({}, modeOptions, options, {
            selectedMessageID: this._selectedMessageID,
        });

        // dict where key is message ID, and value is whether it should display
        // the author of message or not visually
        const displayAuthorMessages = {};

        // Hide avatar and info of a message if that message and the previous
        // one are both comments wrote by the same author at the same minute
        // and in the same document (users can now post message in documents
        // directly from a channel that follows it)
        let prevMessage;
        for (let message of messages) {
            if (
                // is first message of thread
                !prevMessage ||
                // more than 1 min. elasped
                (Math.abs(message.getDate().diff(prevMessage.getDate())) > 60000) ||
                prevMessage.getType() !== 'comment' ||
                message.getType() !== 'comment' ||
                // from a different author
                prevMessage.getAuthorID() !== message.getAuthorID()
            ) {
                displayAuthorMessages[message.getID()] = true;
            } else {
                displayAuthorMessages[message.getID()] = !options.squashCloseMessages;
            }
            prevMessage = message;
        }

        if (modeOptions.displayOrder === ORDER.DESC) {
            messages.reverse();
        }

        this.$el.html(QWeb.render('im_livechat.legacy.mail.widget.Thread', {
            displayAuthorMessages,
            options,
            ORDER,
            dateFormat: time.getLangDatetimeFormat(),
            widget: this,
        }));

        for (let message of messages) {
            const $message = this.$('.o_thread_message[data-message-id="' + message.getID() + '"]');
            $message.find('.o_mail_timestamp').data('date', message.getDate());

            this._insertReadMore($message);
        }

        if (shouldScrollToBottomAfterRendering) {
            this.scrollToBottom();
        }

        if (!this._updateTimestampsInterval) {
            this.updateTimestampsInterval = setInterval(() => {
                this._updateTimestamps();
            }, 1000 * 60);
        }
    },

    /**
     * Render thread widget when loading, i.e. when messaging is not yet ready.
     * @see /mail/init_messaging
     */
    renderLoading() {
        this.$el.html(QWeb.render('im_livechat.legacy.mail.widget.ThreadLoading'));
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    getScrolltop() {
        return this.$el.scrollTop();
    },
    /**
     * State whether the bottom of the thread is visible or not,
     * with a tolerance of 5 pixels
     *
     * @return {boolean}
     */
     isAtBottom() {
        const fullHeight = this.el.scrollHeight;
        const topHiddenHeight = this.$el.scrollTop();
        const visibleHeight = this.$el.outerHeight();
        const bottomHiddenHeight = fullHeight - topHiddenHeight - visibleHeight;
        return bottomHiddenHeight < 5;
    },
    /**
     * Scroll to the bottom of the thread
     */
    scrollToBottom() {
        this.$el.scrollTop(this.el.scrollHeight);
    },
    /**
     * Scrolls the thread to a given message
     *
     * @param {integer} options.msgID the ID of the message to scroll to
     * @param {integer} [options.duration]
     * @param {boolean} [options.onlyIfNecessary]
     */
     scrollToMessage(options) {
        const $target = this.$('.o_thread_message[data-message-id="' + options.messageID + '"]');
        if (options.onlyIfNecessary) {
            const delta = $target.parent().height() - $target.height();
            let offset = delta < 0 ?
                            0 :
                            delta - ($target.offset().top - $target.offsetParent().offset().top);
            offset = - Math.min(offset, 0);
            this.$el.scrollTo("+=" + offset + "px", options.duration);
        } else if ($target.length) {
            this.$el.scrollTo($target);
        }
    },
    /**
     * Scroll to the specific position in pixel
     *
     * If no position is provided, scroll to the bottom of the thread
     *
     * @param {integer} [position] distance from top to position in pixels.
     *    If not provided, scroll to the bottom.
     */
    scrollToPosition(position) {
        if (position) {
            this.$el.scrollTop(position);
        } else {
            this.scrollToBottom();
        }
    },
    /**
     * Unselect the selected message
     */
    unselectMessage() {
        this.$('.o_thread_message').removeClass('o_thread_selected_message');
        this._selectedMessageID = null;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Modifies $element to add the 'read more/read less' functionality
     * All element nodes with 'data-o-mail-quote' attribute are concerned.
     * All text nodes after a ``#stopSpelling`` element are concerned.
     * Those text nodes need to be wrapped in a span (toggle functionality).
     * All consecutive elements are joined in one 'read more/read less'.
     *
     * @private
     * @param {jQuery} $element
     */
     _insertReadMore($element) {

        const groups = [];
        let readMoreNodes;

        // nodeType 1: element_node
        // nodeType 3: text_node
        const $children = $element.contents()
            .filter(function () {
                return this.nodeType === 1 ||
                        this.nodeType === 3 &&
                        this.nodeValue.trim();
            });

            for (let child of $children) {
            let $child = $(child);

            // Hide Text nodes if "stopSpelling"
            if (
                child.nodeType === 3 &&
                $child.prevAll('[id*="stopSpelling"]').length > 0
            ) {
                // Convert Text nodes to Element nodes
                $child = $('<span>', {
                    text: child.textContent,
                    'data-o-mail-quote': '1',
                });
                child.parentNode.replaceChild($child[0], child);
            }

            // Create array for each 'read more' with nodes to toggle
            if (
                $child.attr('data-o-mail-quote') ||
                (
                    $child.get(0).nodeName === 'BR' &&
                    $child.prev('[data-o-mail-quote="1"]').length > 0
                )
            ) {
                if (!readMoreNodes) {
                    readMoreNodes = [];
                    groups.push(readMoreNodes);
                }
                $child.hide();
                readMoreNodes.push($child);
            } else {
                readMoreNodes = undefined;
                this._insertReadMore($child);
            }
        }

        for (let group of groups) {
            // Insert link just before the first node
            const $readMore = $('<a>', {
                class: 'o_mail_read_more',
                href: '#',
                text: READ_MORE,
            }).insertBefore(group[0]);

            // Toggle All next nodes
            let isReadMore = true;
            $readMore.click(function (e) {
                e.preventDefault();
                isReadMore = !isReadMore;
                for (let $child of group) {
                    $child.hide();
                    $child.toggle(!isReadMore);
                }
                $readMore.text(isReadMore ? READ_MORE : READ_LESS);
            });
        }
    },
    /**
     * @private
     * @param {Object} options
     * @param {integer} [options.channelID]
     * @param {string} options.model
     * @param {integer} options.id
     */
    _redirect: _.debounce(function (options) {
        if ('channelID' in options) {
            this.trigger('redirect_to_channel', options.channelID);
        } else {
            this.trigger('redirect', options.model, options.id);
        }
    }, 500, true),
    /**
     * @private
     */
     _updateTimestamps() {
        const isAtBottom = this.isAtBottom();
        this.$('.o_mail_timestamp').each(function () {
            const date = $(this).data('date');
            $(this).text(mailUtils.timeFromNow(date));
        });
        if (isAtBottom && !this.isAtBottom()) {
            this.scrollToBottom();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClick() {
        if (this._selectedMessageID) {
            this.unselectMessage();
            this.trigger('unselect_message');
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMailExpand(ev) {
        ev.preventDefault();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMessage(ev) {
        $(ev.currentTarget).toggleClass('o_thread_selected_message');
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
     _onClickMessageNeedaction(ev) {
        const messageID = $(ev.currentTarget).data('message-id');
        this.trigger('mark_as_read', messageID);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMessageNotificationError(ev) {
        const messageID = $(ev.currentTarget).data('message-id');
        this.do_action('mail.mail_resend_message_action', {
            additional_context: {
                mail_message_to_resend: messageID,
            }
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMessageReply(ev) {
        this._selectedMessageID = $(ev.currentTarget).data('message-id');
        this.$('.o_thread_message').removeClass('o_thread_selected_message');
        this.$('.o_thread_message[data-message-id="' + this._selectedMessageID + '"]')
            .addClass('o_thread_selected_message');
        this.trigger('select_message', this._selectedMessageID);
        ev.stopPropagation();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
     _onClickMessageStar(ev) {
        const messageID = $(ev.currentTarget).data('message-id');
        this.trigger('toggle_star_status', messageID);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRedirect(ev) {
        // ignore inherited branding
        if ($(ev.target).data('oe-field') !== undefined) {
            return;
        }
        const id = $(ev.target).data('oe-id');
        if (id) {
            ev.preventDefault();
            const model = $(ev.target).data('oe-model');
            let options;
            if (model && (model !== 'mail.channel')) {
                options = {
                    model,
                    id
                };
            } else {
                options = { channelID: id };
            }
            this._redirect(options);
        }
    },
    /**
     * @private
     */
    _onClickShowMore() {
        this.trigger('load_more_messages');
    },
});

PublicLivechatView.ORDER = ORDER;

export default PublicLivechatView;
