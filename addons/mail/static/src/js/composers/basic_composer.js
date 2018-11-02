odoo.define('mail.composer.Basic', function (require) {
"use strict";

var emojis = require('mail.emojis');
var MentionManager = require('mail.composer.MentionManager');
var DocumentViewer = require('mail.DocumentViewer');
var mailUtils = require('mail.utils');

var config = require('web.config');
var core = require('web.core');
var data = require('web.data');
var dom = require('web.dom');
var session = require('web.session');
var Widget = require('web.Widget');

var QWeb = core.qweb;
var _t = core._t;

var BasicComposer = Widget.extend({
    template: "mail.Composer",
    events: {
        'change input.o_input_file': '_onAttachmentChange',
        'click .o_attachment_delete': '_onAttachmentDelete',
        'click .o_attachment_download': '_onAttachmentDownload',
        'click .o_attachment_view': '_onAttachmentView',
        'click .o_composer_button_add_attachment': '_onClickAddAttachment',
        'click .o_composer_button_emoji': '_onEmojiButtonClick',
        'focusout .o_composer_button_emoji': '_onEmojiButtonFocusout',
        'click .o_mail_emoji_container .o_mail_emoji': '_onEmojiImageClick',
        'focus .o_mail_emoji_container .o_mail_emoji': '_onEmojiImageFocus',
        'input .o_input': '_onInput',
        'keydown .o_composer_input textarea': '_onKeydown',
        'keyup .o_composer_input': '_onKeyup',
        'click .o_composer_button_send': '_sendMessage',
    },
    // RPCs done to fetch the mention suggestions are throttled with the
    // following value
    MENTION_THROTTLE: 200,

    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.options = _.defaults(options || {}, {
            commandsEnabled: true,
            context: {},
            inputMinHeight: 28,
            mentionFetchLimit: 8,
            // set to true to only suggest prefetched partners
            mentionPartnersRestricted: false,
            sendText: _t("Send"),
            defaultBody: '',
            defaultMentionSelections: {},
            isMobile: config.device.isMobile
        });
        this.context = this.options.context;

        // Attachments
        this._attachmentDataSet = new data.DataSetSearch(this, 'ir.attachment', this.context);
        this.fileuploadID = _.uniqueId('o_chat_fileupload');
        this.set('attachment_ids', []);

        // Mention
        this._mentionManager = new MentionManager(this);
        this._mentionManager.register({
            delimiter: '@',
            fetchCallback: this._mentionFetchPartners.bind(this),
            generateLinks: true,
            model: 'res.partner',
            redirectClassname: 'o_mail_redirect',
            selection: this.options.defaultMentionSelections['@'],
            suggestionTemplate: 'mail.MentionSuggestions.Partner',
        });
        this._mentionManager.register({
            delimiter: '#',
            fetchCallback: this._mentionFetchChannels.bind(this),
            generateLinks: true,
            model: 'mail.channel',
            redirectClassname: 'o_channel_redirect',
            selection: this.options.defaultMentionSelections['#'],
            suggestionTemplate: 'mail.MentionSuggestions.Channel',
        });
        this._mentionManager.register({
            delimiter: ':',
            fetchCallback: this._mentionGetCannedResponses.bind(this),
            selection: this.options.defaultMentionSelections[':'],
            suggestionTemplate: 'mail.MentionSuggestions.CannedResponse',
        });
        if (this.options.commandsEnabled) {
            this._mentionManager.register({
                beginningOnly: true,
                delimiter: '/',
                fetchCallback: this._mentionGetCommands.bind(this),
                selection: this.options.defaultMentionSelections['/'],
                suggestionTemplate: 'mail.MentionSuggestions.Command',
            });
        }

        this.isMini = options.isMini;

        this.avatarURL = session.uid > 0 ? session.url('/web/image', {
            model: 'res.users',
            field: 'image_small',
            id: session.uid,
        }) : '/web/static/src/img/user_menu_avatar.png';
    },
    start: function () {
        var self = this;

        this._$attachmentButton = this.$('.o_composer_button_add_attachment');
        this._$attachmentsList = this.$('.o_composer_attachments_list');
        this.$input = this.$('.o_composer_input textarea');
        this.$input.focus(function () {
            self.trigger('input_focused');
        });
        this.$input.val(this.options.defaultBody);
        dom.autoresize(this.$input, {
            parent: this,
            min_height: this.options.inputMinHeight
        });

        // Attachments
        $(window).on(this.fileuploadID, this._onAttachmentLoaded.bind(this));
        this.on('change:attachment_ids', this, this._renderAttachments);

        // Mention
        this._mentionManager.prependTo(this.$('.o_composer'));

        return this._super();
    },
    destroy: function () {
        $(window).off(this.fileuploadID);
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Empty input, selected partners and attachments
     */
    clearComposer: function () {
        this.$input.val('');
        this._mentionManager.resetSelections();
        this.set('attachment_ids', []);
    },
    /**
     * Set the focus on the input
     */
    focus: function () {
        this.$input.focus();
    },
    /**
     * Get the state of the composer.
     *
     * This is useful in order to (re)store its state when switchng to another
     * thread with a composer, and coming back to the thread with this composer.
     *
     * @returns {Object}
     */
    getState: function () {
        return {
            attachments: this.get('attachment_ids'),
            text: this.$input.val(),
        };
    },
    /**
     * @returns {integer} it returns length of attachment and trim content of
     *   input box to check for empty.
     */
    isEmpty: function () {
        return !this.$input.val().trim() &&
                !this.$('.o_attachments').children().length;
    },
    /**
     * Set the state of the composer.
     *
     * This is useful in order to (re)store its state when switching to another
     * thread with a composer, and coming back to the thread with this composer.
     *
     * @param {Object} state
     * @param {Array} state.attachments
     * @param {string} state.text
     */
    setState: function (state) {
        this.set('attachment_ids', state.attachments);
        this.$input.val(state.text);
    },
    /**
     * Set the thread that this composer refers to.
     *
     * @param {mail.model.Thread} thread
     */
    setThread: function (thread) {
        this.options.thread = thread;
    },
    /**
     * Set the list of command suggestions on the thread.
     *
     * When the user partially types a command, matching commands are displayed
     * to the user (@see _mentionGetCommands).
     *
     * @param {Object[]} commands
     */
    mentionSetCommands: function (commands) {
        this._mentionCommands = commands;
    },
    /**
     * Set the list of partner mentions suggestions that has been prefetched.
     *
     * When the user partially types a mention, matching prefetched partners are
     * displayed to the user. If none of them match, then it will fetch for more
     * partner suggestions (@see _mentionFetchPartners).
     *
     * @param {$.Deferred<Object[]>} prefetchedPartners
     */
    mentionSetPrefetchedPartners: function (prefetchedPartners) {
        this._mentionPrefetchedPartners = prefetchedPartners;
    },
    /**
     * @returns {Object} containing listener selections, grouped by delimiter
     *   as key of the object.
     */
    getMentionListenerSelections: function () {
        return this._mentionManager.getListenerSelections();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _clearComposerOnSend: function () {
        this.clearComposer();
    },
    /**
     * @private
     */
    _doCheckAttachmentUpload: function () {
        if (_.find(this.get('attachment_ids'), function (file) { return file.upload; })) {
            this.do_warn(_t("Uploading error"), _t("Please, wait while the file is uploading."));
            return false;
        }
        return true;
    },
    /**
     * Hides the emojis container.
     *
     * @private
     */
    _hideEmojis: function () {
        this._$emojisContainer.remove();
    },
    /**
     * @private
     * @param {string} search
     * @returns {$.Deferred<Object[]>}
     */
    _mentionGetCannedResponses: function (search) {
        var self = this;
        var def = $.Deferred();
        clearTimeout(this._cannedTimeout);
        this._cannedTimeout = setTimeout(function () {
            var cannedResponses = self.call('mail_service', 'getCannedResponses');
            var matches = fuzzy.filter(mailUtils.unaccent(search), _.pluck(cannedResponses, 'source'));
            var indexes = _.pluck(matches.slice(0, self.options.mentionFetchLimit), 'index');
            def.resolve(_.map(indexes, function (index) {
                return cannedResponses[index];
            }));
        }, 500);
        return def;
    },
    /**
     * @private
     * @param {string} search
     * @returns {Array}
     */
    _mentionGetCommands: function (search) {
        var searchRegexp = new RegExp(_.str.escapeRegExp(mailUtils.unaccent(search)), 'i');
        return _.filter(this._mentionCommands, function (command) {
            return searchRegexp.test(command.name);
        }).slice(0, this.options.mentionFetchLimit);
    },
    /**
     * @private
     * @param {string} search
     */
    _mentionFetchChannels: function (search) {
        return this._mentionFetchThrottled('mail.channel', 'get_mention_suggestions', {
            limit: this.options.mentionFetchLimit,
            search: search,
        }).then(function (suggestions) {
            return _.partition(suggestions, function (suggestion) {
                return _.contains(['public', 'groups'], suggestion.public);
            });
        });
    },
    /**
     * @private
     * @param {string} search
     */
    _mentionFetchPartners: function (search) {
        var self = this;
        return $.when(this._mentionPrefetchedPartners).then(function (partners) {
            // filter prefetched partners with the given search string
            var suggestions = [];
            var limit = self.options.mentionFetchLimit;
            var searchRegexp = new RegExp(_.str.escapeRegExp(mailUtils.unaccent(search)), 'i');
            if (limit > 0) {
                var filteredPartners = _.filter(partners, function (partner) {
                    return partner.email && searchRegexp.test(partner.email) ||
                           partner.name && searchRegexp.test(mailUtils.unaccent(partner.name));
                });
                if (filteredPartners.length) {
                    suggestions.push(filteredPartners.slice(0, limit));
                    limit -= filteredPartners.length;
                }
            }
            if (!suggestions.length && !self.options.mentionPartnersRestricted) {
                // no result found among prefetched partners, fetch other suggestions
                suggestions = self._mentionFetchThrottled(
                    'res.partner',
                    'get_mention_suggestions',
                    { limit: limit, search: search }
                );
            }
            return suggestions;
        });
    },
    /**
     * @private
     * @param {string} model
     * @param {string} method
     * @param {Object} kwargs
     * @return {$.Deferred}
     */
    _mentionFetchThrottled: function (model, method, kwargs) {
        var self = this;
        // Delays the execution of the RPC to prevent unnecessary RPCs when the user is still typing
        var def = $.Deferred();
        clearTimeout(this.mentionFetchTimer);
        this.mentionFetchTimer = setTimeout(function () {
            return self._rpc({model: model, method: method, kwargs: kwargs})
                .then(function (results) {
                    def.resolve(results);
                });
        }, this.MENTION_THROTTLE);
        return def;
    },
    /**
     * @private
     * @returns {$.Deferred}
     */
    _preprocessMessage: function () {
        // Return a deferred as this function is extended with asynchronous
        // behavior for the chatter composer

        //Removing unwanted extra spaces from message
        var value = _.escape(this.$input.val()).trim();
        value = value.replace(/(\r|\n){2,}/g, '<br/><br/>');
        value = value.replace(/(\r|\n)/g, '<br/>');

        // prevent html space collapsing
        value = value.replace(/ /g, '&nbsp;').replace(/([^>])&nbsp;([^<])/g, '$1 $2');
        var commands = this.options.commandsEnabled ?
                        this._mentionManager.getListenerSelection('/') :
                        [];
        return $.when({
            content: this._mentionManager.generateLinks(value),
            attachment_ids: _.pluck(this.get('attachment_ids'), 'id'),
            partner_ids: _.uniq(_.pluck(this._mentionManager.getListenerSelection('@'), 'id')),
            canned_response_ids: _.uniq(_.pluck(this._mentionManager.getListenerSelections()[':'], 'id')),
            command: commands.length > 0 ? commands[0].name : undefined,
        });
    },
    /**
     * @private
     */
    _renderAttachments: function () {
        this._$attachmentsList.html(QWeb.render('mail.composer.Attachments', {
            attachments: this.get('attachment_ids'),
        }));
    },
    /**
     * @private
     */
    _sendMessage: function () {
        if (this.isEmpty() || !this._doCheckAttachmentUpload()) {
            return;
        }

        this.$(".o_composer_button_send").prop("disabled", true);
        clearTimeout(this._cannedTimeout);
        var self = this;
        this._preprocessMessage().then(function (message) {
            self.trigger('post_message', message);
            self._clearComposerOnSend();
            self.$input.focus();
        });
    },
    /**
     * Send the message on ENTER, but go to new line on SHIFT+ENTER
     *
     * @private
     */
    _shouldSend: function (ev) {
        return !ev.shiftKey;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {jQuery.Event} ev
     */
    _onAttachmentChange: function (ev) {
        var self = this;
        var files = ev.target.files;
        var attachments = this.get('attachment_ids');

        _.each(files, function (file){
            var attachment = _.findWhere(attachments, {name: file.name});
            // if the files already exits, delete the file before upload
            if (attachment){
                self._attachmentDataSet.unlink([attachment.id]);
                attachments = _.without(attachments, attachment);
            }
        });

        this.$('form.o_form_binary_form').submit();
        this._$attachmentButton.prop('disabled', true);
        var uploadAttachments = _.map(files, function (file){
            return {
                id: 0,
                name: file.name,
                filename: file.name,
                url: '',
                upload: true,
                mimetype: '',
            };
        });
        attachments = attachments.concat(uploadAttachments);
        this.set('attachment_ids', attachments);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onAttachmentDelete: function (ev){
        ev.stopPropagation();
        var self = this;
        var attachmentID = $(ev.currentTarget).data('id');
        if (attachmentID) {
            var attachments = [];
            _.each(this.get('attachment_ids'), function (attachment){
                if (attachmentID !== attachment.id) {
                    attachments.push(attachment);
                } else {
                    self._attachmentDataSet.unlink([attachmentID]);
                }
            });
            this.set('attachment_ids', attachments);
            this.$('input.o_input_file').val('');
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onAttachmentDownload: function (ev) {
        ev.stopPropagation();
    },
    /**
     * @private
     */
    _onAttachmentLoaded: function () {
        var attachments = this.get('attachment_ids');
        var files = Array.prototype.slice.call(arguments, 1);

        _.each(files, function (file) {
            if (file.error || !file.id){
                this.do_warn(file.error);
                attachments = _.filter(attachments, function (attachment) {
                    return !attachment.upload;
                });
            } else {
                var attachment = _.findWhere(attachments, { filename: file.filename, upload: true });
                if (attachment) {
                    attachments = _.without(attachments, attachment);
                    attachments.push({
                        id: file.id,
                        name: file.name || file.filename,
                        filename: file.filename,
                        mimetype: file.mimetype,
                        url: session.url('/web/content', { id: file.id, download: true }),
                    });
                }
            }
        }.bind(this));
        this.set('attachment_ids', attachments);
        this._$attachmentButton.prop('disabled', false);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onAttachmentView: function (ev) {
        var activeAttachmentID = $(ev.currentTarget).data('id');
        var attachments = this.get('attachment_ids');
        if (activeAttachmentID) {
            var attachmentViewer = new DocumentViewer(this, attachments, activeAttachmentID);
            attachmentViewer.appendTo($('body'));
        }
    },
    _onClickAddAttachment: function () {
        this.$('input.o_input_file').click();
        this.$input.focus();
    },
    /**
     * Called when the emoji button is clicked -> opens/hides the emoji panel.
     * Also, this method is in charge of the rendering of this panel the first
     * time it is opened.
     *
     * @private
     */
    _onEmojiButtonClick: function () {
        if (!this._$emojisContainer) { // lazy rendering
            this._$emojisContainer = $(QWeb.render('mail.Composer.emojis', {
                emojis: emojis,
            }));
        }
        if (this._$emojisContainer.parent().length) {
            this._hideEmojis();
        } else {
            this._$emojisContainer.appendTo(this.$('.o_composer'));
        }
    },
    /**
     * Called when the emoji button is blurred -> closes the emoji panel. The
     * closing is scheduled to be done at the end of the current execution
     * stack to allow stoping this closing if the button was focusout to select
     * an emoji (for example).
     *
     * @private
     */
    _onEmojiButtonFocusout: function () {
        if (this._$emojisContainer) {
            this._hideEmojisTimeout = setTimeout(this._hideEmojis.bind(this), 0);
        }
    },
    /**
     * Called when an emoji is clicked -> adds it in the <input/>, focuses the
     * <input/> and closes the emoji panel.
     *
     * @private
     * @param {Event} ev
     */
    _onEmojiImageClick: function (ev) {
        this.$input.val(this.$input.val() + " " + $(ev.currentTarget).data('emoji') + " ");
        this.$input.focus();
        this._hideEmojis();
    },
    /**
     * Called when an emoji is focused -> @see _onEmojiButtonFocusout
     *
     * @private
     */
    _onEmojiImageFocus: function () {
        clearTimeout(this._hideEmojisTimeout);
    },
    /**
     * Called when the input in the composer changes
     *
     * @private
     */
    _onInput: function () {
        if (this.options.thread && this.options.thread.hasTypingNotification()) {
            var isTyping = this.$input.val().length > 0;
            this.options.thread.setMyselfTyping({ typing: isTyping });
        }
    },
    /**
     * _onKeydown event is triggered when is key is pressed
     *      - on UP and DOWN arrow is pressed then event prevents it's default
     *              behaviour if mention manager is open else it break it.
     *      - on ENTER key is pressed and mention manager is open then event
     *              prevents it's default behaviour else check if ControlKey is
     *              pressed or not if yes then it send a message
     *
     * @private
     * @param {KeyboardEvent} ev
    */
    _onKeydown: function (ev) {
        switch (ev.which) {
            // UP, DOWN, TAB: prevent moving cursor if navigation in mention propositions
            case $.ui.keyCode.UP:
            case $.ui.keyCode.DOWN:
            case $.ui.keyCode.TAB:
                if (this._mentionManager.isOpen()) {
                    ev.preventDefault();
                }
                break;
            // ENTER: submit the message only if the dropdown mention proposition is not displayed
            case $.ui.keyCode.ENTER:
                if (this._mentionManager.isOpen()) {
                    ev.preventDefault();
                } else {
                    var sendMessage = ev.ctrlKey || this._shouldSend(ev);
                    if (sendMessage) {
                        ev.preventDefault();
                        this._sendMessage();
                    }
                }
                break;
        }
    },
    /**
     * _onKeyup event is triggered when key is released.
     * on ESCAP key it close the mention suggestion dropdown menu.
     * on ENTER key it selects that mention and add to a content editable div.
     * on UP or DOWN key it highlights previous or next mention respectively.
     *
     * @private
     * @param {KeyboardEvent} ev
    */
    _onKeyup: function (ev) {
        switch (ev.which) {
            // ESCAPED KEYS: do nothing
            case $.ui.keyCode.END:
            case $.ui.keyCode.PAGE_UP:
            case $.ui.keyCode.PAGE_DOWN:
                break;
            // ESCAPE: close mention propositions
            case $.ui.keyCode.ESCAPE:
                if (this._mentionManager.isOpen()) {
                    ev.stopPropagation();
                    this._mentionManager.resetSuggestions();
                } else {
                    this.trigger_up('escape_pressed');
                }
                break;
            // ENTER, UP, DOWN, TAB: check if navigation in mention propositions
            case $.ui.keyCode.ENTER:
            case $.ui.keyCode.UP:
            case $.ui.keyCode.DOWN:
            case $.ui.keyCode.TAB:
                if (this._mentionManager.isOpen()) {
                    this._mentionManager.propositionNavigation(ev.which);
                }
                break;
            // Otherwise, check if a mention is typed
            default:
                this._mentionManager.detectDelimiter();
        }
    },
});

return BasicComposer;

});
