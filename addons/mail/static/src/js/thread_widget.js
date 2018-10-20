odoo.define('mail.widget.Thread', function (require) {
"use strict";

var DocumentViewer = require('mail.DocumentViewer');
var mailUtils = require('mail.utils');

var core = require('web.core');
var time = require('web.time');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var ORDER = {
    ASC: 1, // visually, ascending order of message IDs (from top to bottom)
    DESC: -1, // visually, descending order of message IDs (from top to bottom)
};

var READ_MORE = _t("read more");
var READ_LESS = _t("read less");

/**
 * This is a generic widget to render a thread.
 * Any thread that extends mail.model.AbstractThread can be used with this
 * widget.
 */
var ThreadWidget = Widget.extend({
    className: 'o_mail_thread',

    events: {
        'click a': '_onClickRedirect',
        'click img': '_onClickRedirect',
        'click strong': '_onClickRedirect',
        'click .o_thread_show_more': '_onClickShowMore',
        'click .o_attachment_download': '_onAttachmentDownload',
        'click .o_attachment_view': '_onAttachmentView',
        'click .o_thread_message_needaction': '_onClickMessageNeedaction',
        'click .o_thread_message_star': '_onClickMessageStar',
        'click .o_thread_message_reply': '_onClickMessageReply',
        'click .oe_mail_expand': '_onClickMailExpand',
        'click .o_thread_message': '_onClickMessage',
        'click': '_onClick',
        'click .o_thread_message_email_exception': '_onClickEmailException',
        'click .o_thread_message_email_bounce': '_onClickEmailException',
        'click .o_thread_message_moderation': '_onClickMessageModeration',
        'change .moderation_checkbox': '_onChangeModerationCheckbox',
    },

    /**
     * @override
     * @param {widget} parent
     * @param {Object} options
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        // options when the thread is enabled (e.g. can send message,
        // interact on messages, etc.)
        this._enabledOptions = _.defaults(options || {}, {
            displayOrder: ORDER.ASC,
            displayMarkAsRead: true,
            displayModerationCommands: false,
            displayStars: true,
            displayDocumentLinks: true,
            displayAvatars: true,
            squashCloseMessages: true,
            displayEmailIcons: true,
            displayReplyIcons: false,
            loadMoreOnScroll: false,
        });
        // options when the thread is disabled
        this._disabledOptions = {
            displayOrder: this._enabledOptions.displayOrder,
            displayMarkAsRead: false,
            displayModerationCommands: false,
            displayStars: false,
            displayDocumentLinks: false,
            displayAvatars: this._enabledOptions.displayAvatars,
            squashCloseMessages: false,
            displayEmailIcons: false,
            displayReplyIcons: false,
            loadMoreOnScroll: this._enabledOptions.loadMoreOnScroll,
        };
        this._selectedMessageID = null;
        this._currentThreadID = null;
        this._messageMailPopover = null;
    },
    /**
     * The message mail popover may still be shown at this moment. If we do not
     * remove it, it stays visible on the page until a page reload.
     *
     * @override
     */
    destroy: function () {
        clearInterval(this._updateTimestampsInterval);
        if (this._messageMailPopover) {
            this._messageMailPopover.popover('hide');
        }
    },
    /**
     * @param {mail.model.AbstractThread} thread the thread to render.
     * @param {Object} [options]
     * @param {integer} [options.displayOrder=ORDER.ASC] order of displaying
     *    messages in the thread:
     *      - ORDER.ASC: last message is at the bottom of the thread
     *      - ORDER.DESC: last message is at the top of the thread
     * @param {boolean} [options.displayLoadMore]
     * @param {Array} [options.domain=[]] the domain for the messages in the
     *    thread.
     * @param {boolean} [options.isCreateMode]
     * @param {boolean} [options.scrollToBottom=false]
     * @param {boolean} [options.squashCloseMessages]
     */
    render: function (thread, options) {
        var self = this;

        var shouldScrollToBottomAfterRendering = false;
        if (this._currentThreadID === thread.getID() && this.isAtBottom()) {
            shouldScrollToBottomAfterRendering = true;
        }
        this._currentThreadID = thread.getID();

        // copy so that reverse do not alter order in the thread object
        var messages = _.clone(thread.getMessages({ domain: options.domain || [] }));

        var modeOptions = options.isCreateMode ? this._disabledOptions :
                                                 this._enabledOptions;

        // attachments ordered by messages order (increasing ID)
        this.attachments = _.uniq(_.flatten(_.map(messages, function (message) {
            return message.getAttachments();
        })));

        options = _.extend({}, modeOptions, options, {
            selectedMessageID: this._selectedMessageID,
        });

        // dict where key is message ID, and value is whether it should display
        // the author of message or not visually
        var displayAuthorMessages = {};

        // Hide avatar and info of a message if that message and the previous
        // one are both comments wrote by the same author at the same minute
        // and in the same document (users can now post message in documents
        // directly from a channel that follows it)
        var prevMessage;
        _.each(messages, function (message) {
            if (
                // is first message of thread
                !prevMessage ||
                // more than 1 min. elasped
                (Math.abs(message.getDate().diff(prevMessage.getDate())) > 60000) ||
                prevMessage.getType() !== 'comment' ||
                message.getType() !== 'comment' ||
                // from a different author
                (prevMessage.getAuthorID() !== message.getAuthorID()) ||
                (
                    // messages are linked to a document thread
                    (
                        prevMessage.isLinkedToDocumentThread() &&
                        message.isLinkedToDocumentThread()
                    ) &&
                    (
                        // are from different documents
                        prevMessage.getDocumentModel() !== message.getDocumentModel() ||
                        prevMessage.getDocumentID() !== message.getDocumentID()
                    )
                )
            ) {
                displayAuthorMessages[message.getID()] = true;
            } else {
                displayAuthorMessages[message.getID()] = !options.squashCloseMessages;
            }
            prevMessage = message;
        });

        if (modeOptions.displayOrder === ORDER.DESC) {
            messages.reverse();
        }

        this.$el.html(QWeb.render('mail.widget.Thread', {
            thread: thread,
            displayAuthorMessages: displayAuthorMessages,
            options: options,
            ORDER: ORDER,
            dateFormat: time.getLangDatetimeFormat(),
        }));

        // must be after mail.widget.Thread rendering, so that there is the
        // DOM element for the 'is typing' notification bar
        if (thread.hasTypingNotification()) {
            this.renderTypingNotificationBar(thread);
        }

        _.each(messages, function (message) {
            var $message = self.$('.o_thread_message[data-message-id="'+ message.getID() +'"]');
            $message.find('.o_mail_timestamp').data('date', message.getDate());

            self._insertReadMore($message);
        });

        if (shouldScrollToBottomAfterRendering) {
            this.scrollToBottom();
        }

        if (!this._updateTimestampsInterval) {
            this.updateTimestampsInterval = setInterval(function () {
                self._updateTimestamps();
            }, 1000*60);
        }

        this._renderMessageMailPopover(messages);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    getScrolltop: function () {
        return this.$el.scrollTop();
    },
    /**
     * State whether the bottom of the thread is visible or not,
     * with a tolerance of 5 pixels
     *
     * @return {boolean}
     */
    isAtBottom: function () {
        var fullHeight         = this.el.scrollHeight;
        var topHiddenHeight    = this.$el.scrollTop();
        var visibleHeight      = this.$el.outerHeight();
        var bottomHiddenHeight = fullHeight - topHiddenHeight - visibleHeight;
        return bottomHiddenHeight < 5;
    },
    /**
     * Removes a message and re-renders the thread
     *
     * @param {integer} [messageID] the id of the removed message
     * @param {mail.model.AbstractThread} thread the thread which contains
     *   updated list of messages (so it does not contain any message with ID
     *   `messageID`).
     * @param {Object} [options] options for the thread rendering
     */
    removeMessageAndRender: function (messageID, thread, options) {
        var self = this;
        var done = $.Deferred();
        this.$('.o_thread_message[data-message-id="' + messageID + '"]')
            .fadeOut({
                done: function () {
                    self.render(thread, options);
                    done.resolve();
                },
                duration: 200,
            });
        return done;
    },
    /**
     * Render the 'is typing...' text on the typing notification bar of the
     * thread. This is called when there is a change in the list of users
     * typing something on this thread.
     *
     * @param {mail.model.AbstractThread} thread with ThreadTypingMixin
     */
    renderTypingNotificationBar: function (thread) {
        if (this._currentThreadID === thread.getID()) {
            var shouldScrollToBottomAfterRendering = this.isAtBottom();

            // typing notification bar rendering
            var $typingBar = this.$('.o_thread_typing_notification_bar');
            var text = thread.getTypingMembersToText();
            $typingBar.toggleClass('o_hidden', !text); // hide if no text, because of padding
            $typingBar.text(text);

            if (shouldScrollToBottomAfterRendering) {
                this.scrollToBottom();
            }
        }
    },
    /**
     * Scroll to the bottom of the thread
     */
    scrollToBottom: function () {
        this.$el.scrollTop(this.el.scrollHeight);
    },
    /**
     * Scrolls the thread to a given message
     *
     * @param {integer} options.messageID the ID of the message to scroll to
     * @param {integer} [options.duration]
     * @param {boolean} [options.onlyIfNecessary]
     */
    scrollToMessage: function (options) {
        var $target = this.$('.o_thread_message[data-message-id="' + options.messageID + '"]');
        if (options.onlyIfNecessary) {
            var delta = $target.parent().height() - $target.height();
            var offset = delta < 0 ?
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
    scrollToPosition: function (position) {
        if (position) {
            this.$el.scrollTop(position);
        } else {
            this.scrollToBottom();
        }
    },
    /**
     * Toggle all the moderation checkboxes in the thread
     *
     * @param {boolean} checked if true, check the boxes,
     *      otherwise uncheck them.
     */
    toggleModerationCheckboxes: function (checked) {
        this.$('.moderation_checkbox').prop('checked', checked);
    },
    /**
     * Unselect the selected message
     */
    unselectMessage: function () {
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
    _insertReadMore: function ($element) {
        var self = this;

        var groups = [];
        var readMoreNodes;

        // nodeType 1: element_node
        // nodeType 3: text_node
        var $children = $element.contents()
            .filter(function () {
                return this.nodeType === 1 ||
                        this.nodeType === 3 &&
                        this.nodeValue.trim();
            });

        _.each($children, function (child) {
            var $child = $(child);

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
                self._insertReadMore($child);
            }
        });

        _.each(groups, function (group) {
            // Insert link just before the first node
            var $readMore = $('<a>', {
                class: 'o_mail_read_more',
                href: '#',
                text: READ_MORE,
            }).insertBefore(group[0]);

            // Toggle All next nodes
            var isReadMore = true;
            $readMore.click(function (e) {
                e.preventDefault();
                isReadMore = !isReadMore;
                _.each(group, function ($child) {
                    $child.hide();
                    $child.toggle(!isReadMore);
                });
                $readMore.text(isReadMore ? READ_MORE : READ_LESS);
            });
        });
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
     * Render the popover when mouse-hovering on the mail icon of a message
     * in the thread. There is at most one such popover at any given time.
     *
     * @private
     * @param {mail.model.AbstractMessage[]} messages list of messages in the
     *   rendered thread, for which popover on mouseover interaction is
     *   permitted.
     */
    _renderMessageMailPopover: function (messages) {
        if (this._messageMailPopover) {
            this._messageMailPopover.popover('hide');
        }
        if (!this.$('.o_thread_tooltip').length) {
            return;
        }
        this._messageMailPopover = this.$('.o_thread_tooltip').popover({
            html: true,
            boundary: 'viewport',
            placement: 'auto',
            trigger: 'hover',
            offset: '0, 1',
            content: function () {
                var messageID = $(this).data('message-id');
                var message = _.find(messages, function (message) {
                    return message.getID() === messageID;
                });
                return QWeb.render('mail.widget.Thread.Message.MailTooltip', {
                    data: message.getCustomerEmailData()
                });
            },
        });
    },
    /**
     * @private
     */
    _updateTimestamps: function () {
        var isAtBottom = this.isAtBottom();
        this.$('.o_mail_timestamp').each(function () {
            var date = $(this).data('date');
            $(this).html(mailUtils.timeFromNow(date));
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
     * @param {MouseEvent} event
     */
    _onAttachmentDownload: function (event) {
        event.stopPropagation();
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onAttachmentView: function (event) {
        event.stopPropagation();
        var activeAttachmentID = $(event.currentTarget).data('id');
        if (activeAttachmentID) {
            var attachmentViewer = new DocumentViewer(this, this.attachments, activeAttachmentID);
            attachmentViewer.appendTo($('body'));
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onChangeModerationCheckbox: function (ev) {
        this.trigger_up('update_moderation_buttons');
    },
    /**
     * @private
     */
    _onClick: function () {
        if (this._selectedMessageID) {
            this.unselectMessage();
            this.trigger('unselect_message');
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickEmailException: function (ev) {
        var messageID = $(ev.currentTarget).data('message-id');
        this.do_action('mail.mail_resend_message_action', {
            additional_context: {
                mail_message_to_resend: messageID
            }
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMailExpand: function (ev) {
        ev.preventDefault();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMessage: function (ev) {
        $(ev.currentTarget).toggleClass('o_thread_selected_message');
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMessageNeedaction: function (ev) {
        var messageID = $(ev.currentTarget).data('message-id');
        this.trigger('mark_as_read', messageID);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMessageReply: function (ev) {
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
    _onClickMessageStar: function (ev) {
        var messageID = $(ev.currentTarget).data('message-id');
        this.trigger('toggle_star_status', messageID);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMessageModeration: function (ev) {
        var $button = $(ev.currentTarget);
        var messageID = $button.data('message-id');
        var decision = $button.data('decision');
        this.trigger_up('message_moderation', {
            messageID: messageID,
            decision: decision,
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRedirect: function (ev) {
        // ignore inherited branding
        if ($(ev.target).data('oe-field') !== undefined) {
            return;
        }
        var id = $(ev.target).data('oe-id');
        if (id) {
            ev.preventDefault();
            var model = $(ev.target).data('oe-model');
            var options;
            if (model && (model !== 'mail.channel')) {
                options = {
                    model: model,
                    id: id
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
    _onClickShowMore: function () {
        this.trigger('load_more_messages');
    },
});

ThreadWidget.ORDER = ORDER;

return ThreadWidget;

});
