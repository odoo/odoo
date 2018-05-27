odoo.define('mail.widget.Thread', function (require) {
"use strict";

var mailUtils = require('mail.utils');

var core = require('web.core');
var time = require('web.time');
var DocumentViewer = require('mail.DocumentViewer');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var ORDER = {
    ASC: 1,
    DESC: -1,
};

var READ_MORE = _t("read more");
var READ_LESS = _t("read less");

/**
 * This is a generic widget to render a chat thread
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
    },

    /**
     * @override
     * @param {widget} parent
     * @param {Object} options
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        // options when the thread is enabled (e.g. can send message, interact on messages, etc.)
        this._enabledOptions = _.defaults(options || {}, {
            displayOrder: ORDER.ASC,
            displayMarkAsRead: true,
            displayStar: true,
            displayDocumentLink: true,
            displayAvatar: true,
            squashCloseMessages: true,
            displayEmailIcon: true,
            displayReplyIcon: false,
            loadMoreOnScroll: false,
        });
        // options when the thread is disabled
        this._disabledOptions = {
            displayOrder: this._enabledOptions.displayOrder,
            displayMarkAsRead: false,
            displayStar: false,
            displayDocumentLink: false,
            displayAvatar: this._enabledOptions.displayAvatar,
            squashCloseMessages: false,
            displayEmailIcon: false,
            displayReplyIcon: false,
            loadMoreOnScroll: this._enabledOptions.loadMoreOnScroll,
        };
        this._selectedMessageID = null;
    },

    /**
     * @override
     */
    destroy: function () {
        clearInterval(this._updateTimestampsInterval);
    },

    /**
     * @param {mail.model.Message[]} messages
     * @param {Object} [options]
     * @param {integer} [options.displayOrder=ORDER.ASC]
     * @param {boolean} [options.displayLoadMore]
     * @param {boolean} [options.isCreateMode]
     * @param {boolean} [options.squashCloseMessages]
     */
    render: function (messages, options) {
        var self = this;

        messages = _.clone(messages); // copy so that reverse do not alter order in the conversation object

        var modeOptions = options.isCreateMode ? this._disabledOptions : this._enabledOptions;
        if (modeOptions.displayOrder === ORDER.DESC) {
            messages.reverse();
        }
        options = _.extend({}, modeOptions, options, {
            selectedMessageID: this._selectedMessageID,
        });

        // Hide avatar and info of a message if that message and the previous
        // one are both comments wrote by the same author at the same minute
        // and in the same document (users can now post message in documents
        // directly from a channel that follows it)
        var prevMessage;
        _.each(messages, function (message) {
            if (
                !prevMessage || // is first message of thread
                (Math.abs(message.getDate().diff(prevMessage.getDate())) > 60000) || // is more than 1 min. after previous message
                prevMessage.getType() !== 'comment' ||
                message.getType() !== 'comment' ||
                (prevMessage.getAuthorID() !== message.getAuthorID()) || // is from a different author
                prevMessage.getDocumentModel() !== message.getDocumentModel() || // is from a different record
                prevMessage.getDocumentResID() !== message.getDocumentResID()
            ) {
                message.displayAuthor(true);
            } else {
                message.displayAuthor(!options.squashCloseMessages);
            }
            prevMessage = message;
        });

        this.$el.html(QWeb.render('mail.ChatThread', {
            messages: messages,
            options: options,
            ORDER: ORDER,
            dateFormat: time.getLangDatetimeFormat(),
        }));

        this.attachments = _.uniq(_.flatten(_.map(messages, function (message) {
            return message.getAttachments();
        })));

        _.each(messages, function (message) {
            var $message = self.$('.o_thread_message[data-message-id="'+ message.getID() +'"]');
            $message.find('.o_mail_timestamp').data('date', message.getDate());

            self._insertReadMore($message);
        });

        if (!this._updateTimestampsInterval) {
            this.updateTimestampsInterval = setInterval(function () {
                self._updateTimestamps();
            }, 1000*60);
        }
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
     * @param {int} [message_id] the id of the removed message
     * @param {array} [messages] the list of messages to display, without the removed one
     * @param {object} [options] options for the thread rendering
     */
    removeMessageAndRender: function (messageID, messages, options) {
        var self = this;
        var done = $.Deferred();
        this.$('.o_thread_message[data-message-id="' + messageID + '"]').fadeOut({
            done: function () { self.render(messages, options); done.resolve();},
            duration: 200,
        });
        return done;
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
     * @param {integer} options.msgID the id of the message to scroll to
     * @param {boolean} [options.onlyIfNecessary]
     * @param {integer} [options.duration]
     */
    scrollToMessage: function (options) {
        var $target = this.$('.o_thread_message[data-message-id="' + options.msgID + '"]');
        if (options.onlyIfNecessary) {
            var delta = $target.parent().height() - $target.height();
            var offset = delta < 0 ? 0 : delta - ($target.offset().top - $target.offsetParent().offset().top);
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
                return this.nodeType === 1 || this.nodeType === 3 && this.nodeValue.trim();
            });

        _.each($children, function (child) {
            var $child = $(child);

            // Hide Text nodes if "stopSpelling"
            if (child.nodeType === 3 && $child.prevAll('[id*="stopSpelling"]').length > 0) {
                // Convert Text nodes to Element nodes
                $child = $('<span>', {
                    text: child.textContent,
                    'data-o-mail-quote': '1',
                });
                child.parentNode.replaceChild($child[0], child);
            }

            // Create array for each 'read more' with nodes to toggle
            if ($child.attr('data-o-mail-quote') || ($child.get(0).nodeName === 'BR' && $child.prev('[data-o-mail-quote="1"]').length > 0)) {
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
        var activeAttachmentID = $(event.currentTarget).data('id');
        if (activeAttachmentID) {
            var attachmentViewer = new DocumentViewer(this, this.attachments, activeAttachmentID);
            attachmentViewer.appendTo($('body'));
        }
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
     * AKU: useless now?
     *
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
    _onClickRedirect: function (ev) {
        // ignore inherited branding
        if ($(ev.target).data('oe-field') !== undefined) {
            return;
        }
        var id = $(ev.target).data('oe-id');
        if (id) {
            ev.preventDefault();
            var model = $(ev.target).data('oe-model');
            var options = model && (model !== 'mail.channel') ? {model: model, id: id} : {channelID: id};
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
