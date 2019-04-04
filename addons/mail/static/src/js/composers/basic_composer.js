odoo.define('mail.composer.Basic', function (require) {
"use strict";

var emojis = require('mail.emojis');
var MentionManager = require('mail.composer.MentionManager');
var DocumentViewer = require('mail.DocumentViewer');
var utils = require('web.utils');

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
        'mousedown .o_mail_emoji_container .o_mail_emoji': '_onEmojiImageClick',
        'focus .o_mail_emoji_container .o_mail_emoji': '_onEmojiImageFocus',
        'dragover .o_file_drop_zone_container': '_onFileDragover',
        'drop .o_file_drop_zone_container': '_onFileDrop',
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
        this.set('attachment_ids', options.attachmentIds || []);

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
        this._renderAttachments();
        $(window).on(this.fileuploadID, this._onAttachmentLoaded.bind(this));
        this.on('change:attachment_ids', this, this._renderAttachments);

        this.call('mail_service', 'getMailBus')
            .on('update_typing_partners', this, this._onUpdateTypingPartners);

        // Mention
        var prependPromise = this._mentionManager.prependTo(this.$('.o_composer'));

        // Drag-Drop files
        // Allowing body to detect dragenter and dragleave for display
        var $body = $('body');
        this._dropZoneNS = _.uniqueId('o_dz_');  // For event namespace used when multiple chat window is open
        $body.on('dragleave.' + this._dropZoneNS, this._onBodyFileDragLeave.bind(this));
        $body.on("dragover." + this._dropZoneNS, this._onBodyFileDragover.bind(this));
        $body.on("drop." + this._dropZoneNS, this._onBodyFileDrop.bind(this));
        return Promise.all([this._super(), prependPromise]);
    },
    destroy: function () {
        $("body").off('dragleave.' + this._dropZoneNS);
        $("body").off('dragover.' + this._dropZoneNS);
        $("body").off('drop.' + this._dropZoneNS);
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
     * Get cursor position and selection
     *
     * @returns {Object} a current cursor position as { start: {integer}, end: {integer} }
    */
   getSelectionPositions: function () {
        var InputElement = this.$input.get(0);
        return InputElement ? dom.getSelectionRange(InputElement) : { start: 0, end: 0 };
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
     * @param {Promise<Object[]>} prefetchedPartners list of list of
     *   prefetched partners.
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
     * Making sure that dragging content is external files.
     * Ignoring other content draging like text.
     *
     * @private
     * @param {DataTransfer} dataTransfer
     * @returns {boolean}
     */
    _isDragSourceExternalFile: function (dataTransfer) {
        var DragDataType = dataTransfer.types;
        if (DragDataType.constructor === DOMStringList) {
            return DragDataType.contains('Files');
        }
        if (DragDataType.constructor === Array) {
            return DragDataType.indexOf('Files') !== -1;
        }
        return false;
    },
    /**
     * @private
     * @param {string} search
     * @returns {Promise<Object[]>}
     */
    _mentionGetCannedResponses: function (search) {
        var self = this;
        var def = new Promise(function (resolve, reject) {
            clearTimeout(self._cannedTimeout);
            self._cannedTimeout = setTimeout(function () {
                var cannedResponses = self.call('mail_service', 'getCannedResponses');
                var matches = fuzzy.filter(utils.unaccent(search), _.pluck(cannedResponses, 'source'));
                var indexes = _.pluck(matches.slice(0, self.options.mentionFetchLimit), 'index');
                resolve(_.map(indexes, function (index) {
                    return cannedResponses[index];
                }));
            }, 500);
        });
        return def;
    },
    /**
     * @private
     * @param {string} search
     * @returns {Array}
     */
    _mentionGetCommands: function (search) {
        var searchRegexp = new RegExp(_.str.escapeRegExp(utils.unaccent(search)), 'i');
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
        return Promise.resolve(this._mentionPrefetchedPartners).then(function (prefetchedPartners) {
            // filter prefetched partners with the given search string
            var suggestions = [];
            var limit = self.options.mentionFetchLimit;
            var searchRegexp = new RegExp(_.str.escapeRegExp(utils.unaccent(search)), 'i');
            _.each(prefetchedPartners, function (partners) {
                if (limit > 0) {
                    var filteredPartners = _.filter(partners, function (partner) {
                        return partner.email && searchRegexp.test(partner.email) ||
                            partner.name && searchRegexp.test(utils.unaccent(partner.name));
                    });
                    if (filteredPartners.length) {
                        suggestions.push(filteredPartners.slice(0, limit));
                        limit -= filteredPartners.length;
                    }
                }
            });
            if (!suggestions.length && !self.options.mentionPartnersRestricted) {
                // no result found among prefetched partners, fetch other suggestions
                suggestions = self._mentionFetchThrottled(
                    'res.partner',
                    'get_mention_suggestions',
                    { limit: limit, search: search }
                );
            }
            return Promise.resolve(suggestions).then(function (suggestions) {
                //add im_status on suggestions
                _.each(suggestions, function (suggestionsSet) {
                    _.each(suggestionsSet, function (suggestion) {
                        suggestion.im_status = self.call('mail_service', 'getImStatus', { partnerID: suggestion.id });
                    });
                });
                return suggestions;
            });
        });
    },
    /**
     * @private
     * @param {string} model
     * @param {string} method
     * @param {Object} kwargs
     * @return {Promise}
     */
    _mentionFetchThrottled: function (model, method, kwargs) {
        var self = this;
        // Delays the execution of the RPC to prevent unnecessary RPCs when the user is still typing
        return new Promise(function (resolve, reject) {
            clearTimeout(self.mentionFetchTimer);
            self.mentionFetchTimer = setTimeout(function () {
                return self._rpc({model: model, method: method, kwargs: kwargs})
                .then(function (results) {
                    resolve(results);
                });
            }, self.MENTION_THROTTLE);
        });
    },
    /**
     * @private
     * @returns {Promise}
     */
    _preprocessMessage: function () {
        // Return a promise as this function is extended with asynchronous
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
        return Promise.resolve({
            content: this._mentionManager.generateLinks(value),
            attachment_ids: _.pluck(this.get('attachment_ids'), 'id'),
            partner_ids: _.uniq(_.pluck(this._mentionManager.getListenerSelection('@'), 'id')),
            canned_response_ids: _.uniq(_.pluck(this._mentionManager.getListenerSelections()[':'], 'id')),
            channel_ids: _.uniq(_.pluck(this._mentionManager.getListenerSelection('#'), 'id')),
            command: commands.length > 0 ? commands[0].name : undefined,
        });
    },
    /**
     * Allowing to upload attachment with file selector as well drag drop feature.
     *
     * @private
     * @param {Array<File>} params.files
     * @param {boolean} params.submitForm [optional]
     */
    _processAttachmentChange: function (params) {
        var self = this,
        attachments = this.get('attachment_ids'),
        files = params.files,
        submitForm = params.submitForm;
        _.each(files, function (file) {
            var attachment = _.findWhere(attachments, {
                name: file.name,
                size: file.size
            });
            // if the files already exits, delete the file before upload
            if (attachment) {
                self._attachmentDataSet.unlink([attachment.id]);
                attachments = _.without(attachments, attachment);
            }
        });
        var $form = this.$('form.o_form_binary_form');
        if (submitForm) {
            $form.submit();
            this._$attachmentButton.prop('disabled', true);
        } else {
            var data = new FormData($form[0]);
            _.each(files, function (file) {
                // removing existing key with blank data and appending again with file info
                // In safari, existing key will not be updated when append with new file.
                data.delete("ufile");
                data.append("ufile", file, file.name);
                $.ajax({
                    url: $form.attr("action"),
                    type: "POST",
                    enctype: 'multipart/form-data',
                    processData: false,
                    contentType: false,
                    data: data,
                    success: function (result) {
                        var $el = $(result);
                        $.globalEval($el.contents().text());
                    }
                });
            });
        }
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

        clearTimeout(this._cannedTimeout);
        var self = this;
        this._preprocessMessage().then(function (message) {
            self.trigger('post_message', message, function() {
                self._clearComposerOnSend();
                self.$input.focus();
            });
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
        this._processAttachmentChange({
            files: ev.currentTarget.files,
            submitForm: true
        });
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
                        size: file.size,
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
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onBodyFileDragLeave: function (ev) {
        // On every dragenter chain created with parent child element
        // That's why dragleave is fired every time when a child elemnt is hovered
        // so here we hide dropzone based on mouse position
        if (ev.originalEvent.clientX <= 0
            || ev.originalEvent.clientY <= 0
            || ev.originalEvent.clientX >= window.innerWidth
            || ev.originalEvent.clientY >= window.innerHeight
        ) {
            this.$(".o_file_drop_zone_container").addClass("d-none");
        }
    },
    /**
     * When user start dragging on element drop area will be visible to drop selected files.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onBodyFileDragover: function (ev) {
        ev.preventDefault();
        if (this._isDragSourceExternalFile(ev.originalEvent.dataTransfer)) {
            this.$(".o_file_drop_zone_container").removeClass("d-none");
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onBodyFileDrop: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.$(".o_file_drop_zone_container").addClass("d-none");
    },
    /**
     * @private
     */
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
     * Called when an emoji is clicked from the emoji panel.
     * Emoji is inserted in the composer based on the position of the cursor,
     * and it automatically focuses the composer and set the cursor position
     * just after the newly inserted emoji.
     *
     * @private
     * @param {Event} ev
     */
    _onEmojiImageClick: function (ev) {
        ev.preventDefault();
        var cursorPosition = this.getSelectionPositions();
        var inputVal = this.$input.val();
        var leftSubstring = inputVal.substring(0, cursorPosition.start);
        var rightSubstring = inputVal.substring(cursorPosition.end);
        var newInputVal  = [leftSubstring , $(ev.currentTarget).data('emoji'), rightSubstring].join(" ");
        var newCursorPosition = newInputVal.length - rightSubstring.length;
        this.$input.val(newInputVal);
        this.$input.focus();
        this.$input[0].setSelectionRange(newCursorPosition, newCursorPosition);
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
     * Setting drop Effect to copy so when mouse pointer on dropzone
     * cursor icon changed to copy ('+')
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onFileDragover: function (ev) {
        ev.originalEvent.dataTransfer.dropEffect = "copy";
    },
    /**
     * Called when user drop selected files on drop area
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onFileDrop: function (ev) {
        ev.preventDefault();
        // FIX: In case multiple chat windows are opened, and file droped in one of them
        // at that time, other chat windows are still displaing drop areas so here hide them all with $ selector
        $(".o_file_drop_zone_container").addClass("d-none");
        if (this._isDragSourceExternalFile(ev.originalEvent.dataTransfer)) {
            var files = ev.originalEvent.dataTransfer.files;
            this._processAttachmentChange({ files: files });
        }
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
    /**
     * @private
     * @param {integer|string} threadID
     */
    _onUpdateTypingPartners: function (threadID) {
        if (!this.options.showTyping) {
            return;
        }
        if (!this.options.thread) {
            return;
        }
        if (this.options.thread.getID() !== threadID) {
            return;
        }
        this.$('.o_composer_thread_typing').html(QWeb.render('mail.Composer.ThreadTyping', {
            thread: this.options.thread,
        }));
    },
});

return BasicComposer;

});
