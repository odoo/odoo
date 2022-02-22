odoo.define('wysiwyg.widgets.media', function (require) {
'use strict';

var concurrency = require('web.concurrency');
var core = require('web.core');
var Dialog = require('web.Dialog');
var dom = require('web.dom');
var fonts = require('wysiwyg.fonts');
var utils = require('web.utils');
var Widget = require('web.Widget');
var session = require('web.session');
const {removeOnImageChangeAttrs} = require('web_editor.image_processing');
const {getCSSVariableValue, DEFAULT_PALETTE} = require('web_editor.utils');
const { UploadProgressToast } = require('@web_editor/js/wysiwyg/widgets/upload_progress_toast');

var QWeb = core.qweb;
var _t = core._t;

var MediaWidget = Widget.extend({
    xmlDependencies: ['/web_editor/static/src/xml/wysiwyg.xml'],

    /**
     * @constructor
     * @param {Element} media: the target Element for which we select a media
     * @param {Object} options: useful parameters such as res_id, res_model,
     *  context, user_id, ...
     */
    init: function (parent, media, options) {
        this._super.apply(this, arguments);
        this.media = media;
        this.$media = $(media);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @todo comment
     */
    clear: function () {
        if (!this.media) {
            return;
        }
        this._clear();
    },
    /**
     * Saves the currently configured media on the target media.
     *
     * @abstract
     * @returns {Promise}
     */
    save: function () {},

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @abstract
     */
    _clear: function () {},
});

var SearchableMediaWidget = MediaWidget.extend({
    events: _.extend({}, MediaWidget.prototype.events || {}, {
        'keydown .o_we_search': '_onSearchKeydown',
        'input .o_we_search': '_onSearchInput',
    }),

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this._onSearchInput = _.debounce(this._onSearchInput, 500);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Finds and displays existing attachments related to the target media.
     *
     * @abstract
     * @param {string} needle: only return attachments matching this parameter
     * @returns {Promise}
     */
    search: function (needle) {},

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Renders thumbnails for the attachments.
     *
     * @abstract
     * @returns {Promise}
     */
    _renderThumbnails: function () {},

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onSearchKeydown: function (ev) {
        // If the template contains a form that has only one input, the enter
        // will reload the page as the html 2.0 specify this behavior.
        if (ev.originalEvent && (ev.originalEvent.code === "Enter" || ev.originalEvent.key === "Enter")) {
            ev.preventDefault();
        }
    },
    /**
     * @private
     */
    _onSearchInput: function (ev) {
        this.attachments = [];
        this.search($(ev.currentTarget).val() || '').then(() => this._renderThumbnails());
        this.hasSearched = true;
    },
});

/**
 * Let users choose a file, including uploading a new file in odoo.
 */
var FileWidget = SearchableMediaWidget.extend({
    events: _.extend({}, SearchableMediaWidget.prototype.events || {}, {
        'click .o_upload_media_button': '_onUploadButtonClick',
        'change .o_file_input': '_onFileInputChange',
        'click .o_upload_media_url_button': '_onUploadURLButtonClick',
        'input .o_we_url_input': '_onURLInputChange',
        'click .o_existing_attachment_cell': '_onAttachmentClick',
        'click .o_existing_attachment_remove': '_onRemoveClick',
        'click .o_load_more': '_onLoadMoreClick',
    }),
    existingAttachmentsTemplate: undefined,

    IMAGE_MIMETYPES: ['image/jpg', 'image/jpeg', 'image/jpe', 'image/png', 'image/svg+xml', 'image/gif'],
    VIDEO_MIMETYPES: ['video/mp4', 'video/url'],
    IMAGE_EXTENSIONS: ['.jpg', '.jpeg', '.jpe', '.png', '.svg', '.gif'],
    VIDEO_EXTENSIONS: ['.mp4'],
    NUMBER_OF_ATTACHMENTS_TO_DISPLAY: 30,
    MAX_DB_ATTACHMENTS: 5,

    /**
     * @constructor
     */
    init: function (parent, media, options) {
        this._super.apply(this, arguments);
        this._mutex = new concurrency.Mutex();

        this.numberOfAttachmentsToDisplay = this.NUMBER_OF_ATTACHMENTS_TO_DISPLAY;

        this.options = _.extend({
            mediaWidth: media && media.parentElement && $(media.parentElement).width(),
            useMediaLibrary: true,
        }, options || {});

        this.attachments = [];
        this.selectedAttachments = [];
        this.libraryMedia = [];
        this.selectedMedia = [];

        this._onUploadURLButtonClick = dom.makeAsyncHandler(this._onUploadURLButtonClick);
    },
    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        var self = this;
        this.$urlInput = this.$('.o_we_url_input');
        this.$form = this.$('form');
        this.$fileInput = this.$('.o_file_input');
        this.$uploadButton = this.$('.o_upload_media_button');
        this.$addUrlButton = this.$('.o_upload_media_url_button');
        this.$urlSuccess = this.$('.o_we_url_success');
        this.$urlWarning = this.$('.o_we_url_warning');
        this.$urlError = this.$('.o_we_url_error');
        this.$errorText = this.$('.o_we_error_text');

        // If there is already an attachment on the target, select by default
        // that attachment if it is among the loaded images.
        var o = {
            url: null,
            alt: null,
        };
        if (this.$media.is('img')) {
            o.url = this.$media.attr('src');
        } else if (this.$media.is('a.o_image')) {
            o.url = this.$media.attr('href').replace(/[?].*/, '');
            o.id = +o.url.match(/\/web\/content\/(\d+)/, '')[1];
        }

        return this.search('').then(async () => {
            await this._renderThumbnails();
            if (o.url) {
                self._selectAttachment(_.find(self.attachments, function (attachment) {
                    return o.url === attachment.media_src;
                }) || o);
            }
            return def;
        });
    },
    /**
     * @override
     */
    destroy() {
        if (this.uploader) {
            // Prevent uploader from being destroyed with call to super so it can linger
            this.uploader.setParent(null);
            this.uploader.close(2000);
        }
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Saves the currently selected image on the target media. If new files are
     * currently being added, delays the save until all files have been added.
     *
     * @override
     */
    save: function () {
        return this._mutex.exec(this._save.bind(this));
    },
    /**
     * @override
     */
    search: function (needle) {
        this.needle = needle;
        return this.fetchAttachments(this.NUMBER_OF_ATTACHMENTS_TO_DISPLAY, 0);
    },
    /**
     * @param {Number} number - the number of attachments to fetch
     * @param {Number} offset - from which result to start fetching
     */
    fetchAttachments: function (number, offset) {
        const fields = ['name', 'mimetype', 'description', 'checksum', 'url', 'type', 'res_id',
            'res_model', 'public', 'access_token', 'media_src', 'media_width', 'media_height', 'original_id'];
        if (this.widgetType === "video") {
            // Thumbnails are binary data, only fetch them if needed
            fields.push("thumbnail");
            // Accomodates for potential previous video selection which is
            // fetched in another RPC (hence +2 instead of +1)
            number += 1;
        }
        return this._rpc({
            model: 'ir.attachment',
            method: 'search_read',
            args: [],
            kwargs: {
                domain: this._getAttachmentsDomain(this.needle),
                fields: fields,
                order: [{name: 'id', asc: false}],
                context: this.options.context,
                // Try to fetch first one or two records of the next page just
                // to know whether there is a next page.
                limit: number + 1,
                offset: offset,
            },
        }).then(attachments => {
            this.attachments = this.attachments.slice();
            Array.prototype.splice.apply(this.attachments, [offset, attachments.length].concat(attachments));
        });
    },
    /**
     * Computes whether there is content to display in the template.
     */
    hasContent() {
        return this.attachments.length;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _clear: function () {
        this.media.className = this.media.className && this.media.className.replace(/(^|\s+)(o_image)(?=\s|$)/g, ' ');
    },
    /**
     * Returns the domain for attachments used in media dialog.
     * We look for attachments related to the current document. If there is a value for the model
     * field, it is used to search attachments, and the attachments from the current document are
     * filtered to display only user-created documents.
     * In the case of a wizard such as mail, we have the documents uploaded and those of the model
     *
     * @private
     * @params {string} needle
     * @returns {Array} "ir.attachment" odoo domain.
     */
    _getAttachmentsDomain: function (needle) {
        var domain = this.options.attachmentIDs && this.options.attachmentIDs.length ? ['|', ['id', 'in', this.options.attachmentIDs]] : [];

        var attachedDocumentDomain = [
            '&',
            ['res_model', '=', this.options.res_model],
            ['res_id', '=', this.options.res_id|0]
        ];
        // if the document is not yet created, do not see the documents of other users
        if (!this.options.res_id) {
            attachedDocumentDomain.unshift('&');
            attachedDocumentDomain.push(['create_uid', '=', this.options.user_id]);
        }
        if (this.options.data_res_model) {
            var relatedDomain = ['&',
                ['res_model', '=', this.options.data_res_model],
                ['res_id', '=', this.options.data_res_id|0]];
            if (!this.options.data_res_id) {
                relatedDomain.unshift('&');
                relatedDomain.push(['create_uid', '=', session.uid]);
            }
            domain = domain.concat(['|'], attachedDocumentDomain, relatedDomain);
        } else {
            domain = domain.concat(attachedDocumentDomain);
        }
        domain = ['|', ['public', '=', true]].concat(domain);
        domain = domain.concat(this.options.mimetypeDomain);
        if (needle && needle.length) {
            domain.push(['name', 'ilike', needle]);
        }
        if (!this.options.useMediaLibrary) {
            domain.push('|', ['url', '=', false], '!', ['url', '=ilike', '/web_editor/shape/%']);
        }
        domain.push('!', ['name', '=like', '%.crop']);
        domain.push('|', ['type', '=', 'binary'], '!', ['url', '=like', '/%/static/%']);
        return domain;
    },
    /**
     * @private
     */
    _highlightSelected: function () {
        var self = this;
        this.$('.o_existing_attachment_cell.o_we_attachment_selected').removeClass("o_we_attachment_selected");
        _.each(this.selectedAttachments, function (attachment) {
            self.$('.o_existing_attachment_cell[data-id=' + attachment.id + ']')
                .addClass("o_we_attachment_selected").css('display', '');
        });
    },
    /**
     * @private
     * @param {object} attachment
     */
    _handleNewAttachment: function (attachment) {
        this.attachments = this.attachments.filter(att => att.id !== attachment.id);
        this.attachments.unshift(attachment);
        this._renderThumbnails();
        this._selectAttachment(attachment);
    },
    /**
     * @private
     * @returns {Promise}
     */
    _loadMoreImages: function (forceSearch) {
        return this.fetchAttachments(10, this.numberOfAttachmentsToDisplay).then(() => {
            this.numberOfAttachmentsToDisplay += 10;
            if (!forceSearch) {
                this._renderThumbnails();
                return Promise.resolve();
            } else {
                return this.search(this.$('.o_we_search').val() || '');
            }
        });
    },
    /**
     * Renders the existing attachments and returns the result as a string.
     *
     * @param {Object[]} attachments
     * @returns {string}
     */
    _renderExisting: function (attachments) {
        return QWeb.render(this.existingAttachmentsTemplate, {
            attachments: attachments,
            widget: this,
        });
    },
    /**
     * @private
     */
    _renderThumbnails() {
        let attachments = this.attachments.slice(0, this.numberOfAttachmentsToDisplay);
        let leftoverAttachments = this.attachments.slice(this.numberOfAttachmentsToDisplay);
        if (this.selectedAttachments.length && leftoverAttachments.length && leftoverAttachments.indexOf(this.selectedAttachments[0]) !== -1) {
            // If the previously selected attachment is fetched in the two
            // extra attachments used to check if "Load more" should be
            // displayed. This ensures it's still shown even if it doesn't
            // need extra fetching from the DB.
            this.previousAttachment = this.selectedAttachments[0];
        }
        let previouslySelected = 0;
        if (this.previousAttachment) {
            previouslySelected = 1;
            attachments.splice(this.previousAttachment.length, 0, this.previousAttachment);
            attachments = attachments.reduce((acc, current) => {
            const x = acc.find(item => item.id === current.id);
            if (!x) {
                return acc.concat([current]);
            } else {
                return acc;
            }
        }, []);
        }
        // Render menu & content
        this.$('.o_we_existing_attachments').replaceWith(
            this._renderExisting(attachments)
        );

        this._highlightSelected();

        // adapt load more
        this.$('.o_we_load_more').toggleClass('d-none', !this.hasContent());
        const noLoadMoreButton = this.NUMBER_OF_ATTACHMENTS_TO_DISPLAY + previouslySelected >= this.attachments.length;
        const noMoreImgToLoad = this.numberOfAttachmentsToDisplay + previouslySelected >= this.attachments.length;
        this.$('.o_load_done_msg').toggleClass('d-none', noLoadMoreButton || !noMoreImgToLoad);
        this.$('.o_load_more').toggleClass('d-none', noMoreImgToLoad);
        this.$('.o_we_load_more').toggleClass('d-none', noMoreImgToLoad);
    },
    /**
     * @private
     * @returns {Promise}
     */
    _save: async function () {
        // Create all media-library attachments.
        const toSave = Object.fromEntries(this.selectedMedia.map(media => [
            media.id, {
                query: media.query || '',
                is_dynamic_svg: !!media.isDynamicSVG,
                dynamic_colors: media.dynamicColors,
                thumbnail: media.thumbnail,
            }
        ]));
        let mediaAttachments = [];
        if (Object.keys(toSave).length !== 0) {
            mediaAttachments = await this._rpc({
                route: '/web_editor/save_library_media',
                params: {
                    media: toSave,
                },
            });
        }
        const selected = this.selectedAttachments.concat(mediaAttachments).map(attachment => {
            // Color-customize dynamic SVGs with the theme colors
            if (attachment.media_src && attachment.media_src.startsWith('/web_editor/shape/')) {
                const colorCustomizedURL = new URL(attachment.media_src, window.location.origin);
                colorCustomizedURL.searchParams.forEach((value, key) => {
                    const match = key.match(/^c([1-5])$/);
                    if (match) {
                        colorCustomizedURL.searchParams.set(key, getCSSVariableValue(`o-color-${match[1]}`));
                    }
                });
                attachment.media_src = colorCustomizedURL.pathname + colorCustomizedURL.search;
            }
            return attachment;
        });
        if (this.options.multiImages) {
            return selected;
        }

        const img = selected[0];
        if (!img || !img.id || this.$media.attr('src') === img.media_src) {
            return this.media;
        }

        if (!img.public && !img.access_token) {
            await this._rpc({
                model: 'ir.attachment',
                method: 'generate_access_token',
                args: [[img.id]]
            }).then(function (access_token) {
                img.access_token = access_token[0];
            });
        }

        if (img.media_src) {
            var src = img.media_src;
            if (!img.public && img.access_token) {
                src += _.str.sprintf('?access_token=%s', img.access_token);
            }
            if (!this.$media.is('img')) {

                // Note: by default the images receive the bootstrap opt-in
                // img-fluid class. We cannot make them all responsive
                // by design because of libraries and client databases img.
                this.$media = $('<img/>', {class: 'img-fluid o_we_custom_image'});
                this.media = this.$media[0];
            }
            this.$media.attr('src', src);
        } else {
            if (!this.$media.is('a')) {
                $('.note-control-selection').hide();
                this.$media = $('<a/>');
                this.media = this.$media[0];
            }
            var href = '/web/content/' + img.id + '?';
            if (!img.public && img.access_token) {
                href += _.str.sprintf('access_token=%s&', img.access_token);
            }
            href += 'unique=' + img.checksum + '&download=true';
            this.$media.attr('href', href);
            this.$media.addClass('o_image').attr('title', img.name);
        }

        this.$media.attr('alt', img.alt || img.description || '');
        var style = this.style;
        if (style) {
            this.$media.css(style);
        }

        // Remove image modification attributes
        removeOnImageChangeAttrs.forEach(attr => {
            delete this.media.dataset[attr];
        });
        // Add mimetype for documents
        if (!img.media_src && this.media.dataset) {
            this.media.dataset.mimetype = img.mimetype;
        }
        this.media.classList.remove('o_modified_image_to_save');
        this.$media.trigger('image_changed');
        return this.media;
    },
    /**
     * @param {object} attachment
     * @param {boolean} [save=true] to save the given attachment in the DOM and
     *  and to close the media dialog
     * @private
     */
    _selectAttachment(attachment, save, {type = 'attachment'} = {}) {
        const possibleProps = {
            'attachment': 'selectedAttachments',
            'media': 'selectedMedia'
        };
        const prop = possibleProps[type];
        if (this.options.multiImages) {
            // if the clicked attachment is already selected then unselect it
            // unless it was a save request (then keep the current selection)
            const index = this[prop].indexOf(attachment);
            if (index !== -1) {
                if (!save) {
                    this[prop].splice(index, 1);
                }
            } else {
                // if the clicked attachment is not selected, add it to selected
                this[prop].push(attachment);
            }
        } else {
            Object.values(possibleProps).forEach(prop => {
                this[prop] = [];
            });
            // select the clicked attachment
            this[prop] = [attachment];
        }
        this._highlightSelected();
        if (save) {
            this.trigger_up('save_request');
        }
    },
    /**
     * Updates the add by URL UI.
     *
     * @private
     * @param {boolean} emptyValue
     * @param {boolean} isURL
     * @param {boolean} isImage
     */
    _updateAddUrlUi: function (emptyValue, isURL, isImage) {
        this.$addUrlButton.toggleClass('btn-secondary', emptyValue)
            .toggleClass('btn-primary', !emptyValue)
            .prop('disabled', !isURL);
        this.$urlSuccess.toggleClass('d-none', !isURL);
        this.$urlError.toggleClass('d-none', emptyValue || isURL);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAttachmentClick: function (ev) {
        const attachment = ev.currentTarget;
        const {id: attachmentID, mediaId} = attachment.dataset;
        if (attachmentID) {
            const attachment = this.attachments.find(attachment => attachment.id === parseInt(attachmentID));
            this._selectAttachment(attachment, !this.options.multiImages);
        } else if (mediaId) {
            const media = this.libraryMedia.find(media => media.id === parseInt(mediaId));
            this._selectAttachment(media, !this.options.multiImages, {type: 'media'});
        }
    },
    /**
     * Handles change of the file input: create attachments with the new files
     * and open the Preview dialog for each of them. Locks the save button until
     * all new files have been processed.
     *
     * @private
     * @returns {Promise}
     */
    _onFileInputChange: function () {
        return this._mutex.exec(this._addData.bind(this));
    },
    /**
     * Uploads the files that are currently selected on the file input, which
     * creates new attachments. Then inserts them on the media dialog and
     * selects them. If multiImages is not set, also triggers up the
     * save_request event to insert the attachment in the DOM.
     *
     * @private
     * @returns {Promise}
     */
    async _addData() {
        let files = this.$fileInput[0].files;
        if (!files.length) {
            // Case if the input is emptied, return resolved promise
            return;
        }

        const uploadMutex = new concurrency.Mutex();

        // Upload the smallest file first to block the user the least possible.
        files = _.sortBy(files, 'size');
        await this._setUpProgressToast(files);
        _.each(files, (file, index) => {
            // Upload one file at a time: no need to parallel as upload is
            // limited by bandwidth.
            uploadMutex.exec(async () => {
                const dataURL = await utils.getDataURLFromFile(file);
                const attachment = await this.uploader.rpcShowProgress({
                    route: '/web_editor/attachment/add_data',
                    params: {
                        'name': file.name,
                        'data': dataURL.split(',')[1],
                        'res_id': this.options.res_id,
                        'res_model': this.options.res_model,
                        'filetype': this.widgetType || "file",
                    }
                }, index);
                if (!attachment.error) {
                    this._handleNewAttachment(attachment);
                }
            });
        });

        return uploadMutex.getUnlockedDef().then(() => {
            if (this.widgetType === "video") {
                // When a user uploads a video, he still needs to configure it
                // So no save request / closing the widget yet.
                return;
            }
            if (!this.uploader.hasError) {
                this.uploader.close(3000);
            }
            if (!this.options.multiImages && !this.noSave) {
                this.trigger_up('save_request');
            }
            this.noSave = false;
        });
    },
    /**
     * @private
     */
    _onRemoveClick: function (ev) {
        var self = this;
        ev.stopPropagation();
        Dialog.confirm(this, _t("Are you sure you want to delete this file ?"), {
            confirm_callback: function () {
                var $a = $(ev.currentTarget).closest('.o_existing_attachment_cell');
                var id = parseInt($a.data('id'), 10);
                var attachment = _.findWhere(self.attachments, {id: id});
                 return self._rpc({
                    route: '/web_editor/attachment/remove',
                    params: {
                        ids: [id],
                    },
                }).then(function (prevented) {
                    if (_.isEmpty(prevented)) {
                        self.attachments = _.without(self.attachments, attachment);
                        self.attachments.filter(at => at.original_id[0] === attachment.id).forEach(at => delete at.original_id);
                        if (!self.attachments.length) {
                            self._renderThumbnails(); //render the message and image if empty
                        } else {
                            $a.closest('.o_existing_attachment_cell').remove();
                        }
                        if (self._resetVideo && attachment && _.findWhere(self.selectedAttachments, {id: id})) {
                            // Reset preview if deleting current attachment
                            self._resetVideo();
                        }
                        return;
                    }
                    self.$errorText.replaceWith(QWeb.render('wysiwyg.widgets.image.existing.error', {
                        views: prevented[id],
                        widget: self,
                    }));
                });
            }
        });
    },
    /**
     * @private
     */
    _onURLInputChange: function () {
        const inputValue = this.$urlInput.val().split('?')[0];
        var emptyValue = (inputValue === '');

        var isURL = /^.+\..+$/.test(inputValue); // TODO improve
        var isImage = _.any(this.IMAGE_EXTENSIONS, function (format) {
            return inputValue.endsWith(format);
        });

        this._updateAddUrlUi(emptyValue, isURL, isImage);
    },
    /**
     * @private
     */
    _onUploadButtonClick: function () {
        this.$fileInput.click();
    },
    /**
     * @private
     */
    _onUploadURLButtonClick: function () {
        if (this.$urlInput.is('.o_we_horizontal_collapse')) {
            this.$urlInput.removeClass('o_we_horizontal_collapse');
            this.$addUrlButton.attr('disabled', 'disabled');
            return;
        }
        return this._mutex.exec(this._addUrl.bind(this));
    },
    /**
     * @private
     * @returns {Promise}
     */
    _addUrl: function () {
        var self = this;
        return this._rpc({
            route: '/web_editor/attachment/add_url',
            params: {
                'url': this.$urlInput.val(),
                'res_id': this.options.res_id,
                'res_model': this.options.res_model,
            },
        }).then(function (attachment) {
            self.$urlInput.val('');
            self._onURLInputChange();
            self._handleNewAttachment(attachment);
            if (!self.options.multiImages) {
                self.trigger_up('save_request');
            }
        });
    },
    /**
     * @private
     */
    _onLoadMoreClick: function () {
        this._loadMoreImages();
    },
    /**
     * @override
     */
    _onSearchInput: function () {
        this.attachments = [];
        this.numberOfAttachmentsToDisplay = this.NUMBER_OF_ATTACHMENTS_TO_DISPLAY;
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Sets up a progress bar for every file being uploaded in a toast.
     *
     * @private
     * @param {Object[]} files
     */
    _setUpProgressToast: async function (files) {
        this.uploader = new UploadProgressToast(this, files);
        await this.uploader.appendTo(document.body);
    },
});

/**
 * Let users choose an image, including uploading a new image in odoo.
 */
var ImageWidget = FileWidget.extend({
    template: 'wysiwyg.widgets.image',
    existingAttachmentsTemplate: 'wysiwyg.widgets.image.existing.attachments',
    events: Object.assign({}, FileWidget.prototype.events, {
        'change input.o_we_show_optimized': '_onShowOptimizedChange',
        'change .o_we_search_select': '_onSearchSelect',
    }),
    MIN_ROW_HEIGHT: 128,

    /**
     * @constructor
     */
    init: function (parent, media, options) {
        this.searchService = 'all';
        this.widgetType = 'image';
        options = _.extend({
            accept: 'image/*',
            mimetypeDomain: [['mimetype', 'in', this.IMAGE_MIMETYPES]],
        }, options || {});
        // Binding so we can add/remove it as an addEventListener
        this._onAttachmentImageLoad = this._onAttachmentImageLoad.bind(this);
        this._super(parent, media, options);
    },
    /**
     * @override
     */
    start: async function () {
        await this._super(...arguments);
        this.el.addEventListener('load', this._onAttachmentImageLoad, true);
    },
    /**
     * @override
     */
    destroy: function () {
        this.el.removeEventListener('load', this._onAttachmentImageLoad, true);
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async fetchAttachments(number, offset) {
        if (this.needle && this.searchService !== 'database') {
            number = this.MAX_DB_ATTACHMENTS;
            offset = 0;
        }
        const result = await this._super(number, offset);
        // Color-substitution for dynamic SVG attachment
        const primaryColors = {};
        for (let color = 1; color <= 5; color++) {
            primaryColors[color] = getCSSVariableValue('o-color-' + color);
        }
        this.attachments.forEach(attachment => {
            if (attachment.media_src && attachment.media_src.startsWith('/')) {
                const newURL = new URL(attachment.media_src, window.location.origin);
                // Set the main colors of dynamic SVGs to o-color-1~5
                if (attachment.media_src.startsWith('/web_editor/shape/')) {
                    newURL.searchParams.forEach((value, key) => {
                        const match = key.match(/^c([1-5])$/);
                        if (match) {
                            newURL.searchParams.set(key, primaryColors[match[1]]);
                        }
                    });
                } else {
                    // Set height so that db images load faster
                    newURL.searchParams.set('height', 2 * this.MIN_ROW_HEIGHT);
                }
                attachment.thumbnail_src = newURL.pathname + newURL.search;
            }
        });
        if (this.needle && this.options.useMediaLibrary) {
            try {
                const response = await this._rpc({
                    route: '/web_editor/media_library_search',
                    params: {
                        'query': this.needle,
                        'offset': this.libraryMedia.length,
                    },
                });
                const newMedia = response.media;
                this.nbMediaResults = response.results;
                this.libraryMedia.push(...newMedia);
            } catch (_e) {
                // Either API endpoint doesn't exist or is misconfigured.
                console.error(`Couldn't reach API endpoint.`);
            }
        }
        return result;
    },
    /**
     * @override
     */
    hasContent() {
        if (this.searchService === 'all') {
            return this._super(...arguments) || this.libraryMedia.length;
        } else if (this.searchService === 'media-library') {
            return !!this.libraryMedia.length;
        }
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _updateAddUrlUi: function (emptyValue, isURL, isImage) {
        this._super.apply(this, arguments);
        const warning = isURL && !isImage;
        this.$urlWarning.toggleClass('d-none', !warning);
        this.$addUrlButton.prop('disabled', warning || !isURL);
        this.$urlSuccess.toggleClass('d-none', warning || !isURL);
    },
    /**
     * @override
     */
    _renderThumbnails: function () {
        const alreadyLoaded = this.$('.o_existing_attachment_cell[data-loaded="true"]');
        this._super(...arguments);
        // Hide images until they're loaded
        this.$('.o_existing_attachment_cell').addClass('d-none');
        // Replace images that had been previously loaded if any to prevent scroll resetting to top
        alreadyLoaded.each((index, el) => {
            const toReplace = this.$(`.o_existing_attachment_cell[data-id="${el.dataset.id}"], .o_existing_attachment_cell[data-media-id="${el.dataset.mediaId}"]`);
            if (toReplace.length) {
                toReplace.replaceWith(el);
            }
        });
        this._toggleOptimized(this.$('input.o_we_show_optimized')[0].checked);
        // Placeholders have a 3:2 aspect ratio like most photos.
        const placeholderWidth = 3 / 2 * this.MIN_ROW_HEIGHT;
        this.$('.o_we_attachment_placeholder').css({
            flexGrow: placeholderWidth,
            flexBasis: placeholderWidth,
        });
        if (this.needle && ['media-library', 'all'].includes(this.searchService)) {
            const noMoreImgToLoad = this.libraryMedia.length === this.nbMediaResults;
            const noLoadMoreButton = noMoreImgToLoad && this.libraryMedia.length <= 15;
            this.$('.o_load_done_msg').toggleClass('d-none', noLoadMoreButton || !noMoreImgToLoad);
            this.$('.o_load_more').toggleClass('d-none', noMoreImgToLoad);
            this.$('.o_we_load_more').toggleClass('d-none', noMoreImgToLoad); // TODO: check if this breaks load more
        }
    },
    /**
     * @override
     */
    _renderExisting: function (attachments) {
        if (this.needle && this.searchService !== 'database') {
            attachments = attachments.slice(0, this.MAX_DB_ATTACHMENTS);
        }
        return QWeb.render(this.existingAttachmentsTemplate, {
            attachments: attachments,
            libraryMedia: this.libraryMedia,
            widget: this,
        });
    },
    /**
     * @private
     *
     * @param {boolean} value whether to toggle optimized attachments on or off
     */
    _toggleOptimized: function (value) {
        this.$('.o_we_attachment_optimized').each((i, cell) => cell.style.setProperty('display', value ? null : 'none', 'important'));
    },
    /**
     * @override
     */
    _highlightSelected: function () {
        this._super(...arguments);
        this.selectedMedia.forEach(media => {
            this.$(`.o_existing_attachment_cell[data-media-id=${media.id}]`)
                .addClass("o_we_attachment_selected");
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onAttachmentImageLoad: async function (ev) {
        const img = ev.target;
        const cell = img.closest('.o_existing_attachment_cell');
        if (!cell) {
            return;
        }
        if (cell.dataset && cell.dataset.mediaId && !img.src.startsWith('blob')) {
            const mediaUrl = img.src;
            try {
                const response = await fetch(mediaUrl);
                if (response.headers.get('content-type') === 'image/svg+xml') {
                    let svg = await response.text();
                    const fileName = mediaUrl.split('/').pop();
                    const dynamicColors = {};
                    const combinedColorsRegex = new RegExp(Object.values(DEFAULT_PALETTE).join('|'), 'gi');
                    svg = svg.replace(combinedColorsRegex, match => {
                        const colorId = Object.keys(DEFAULT_PALETTE).find(key => DEFAULT_PALETTE[key] === match.toUpperCase());
                        const colorKey = 'c' + colorId
                        dynamicColors[colorKey] = getCSSVariableValue('o-color-' + colorId);
                        return dynamicColors[colorKey];
                    });
                    if (Object.keys(dynamicColors).length) {
                        const file = new File([svg], fileName, {
                            type: "image/svg+xml",
                        });
                        img.src = URL.createObjectURL(file);
                        const media = this.libraryMedia.find(media => media.id === parseInt(cell.dataset.mediaId));
                        if (media) {
                            media.isDynamicSVG = true;
                            media.dynamicColors = dynamicColors;
                        }
                        // We changed the src: wait for the next load event to do the styling
                        return;
                    }
                }
            } catch (_e) {
                console.error('CORS is misconfigured on the API server, image will be treated as non-dynamic.');
            }
        }
        let aspectRatio = img.naturalWidth / img.naturalHeight;
        // Special case for SVGs with no instrinsic sizes on firefox
        // See https://github.com/whatwg/html/issues/3510#issuecomment-369982529
        if (img.naturalHeight === 0) {
            img.width = 1000;
            // Position fixed so that the image doesn't affect layout while rendering
            img.style.position = 'fixed';
            // Make invisible so the image doesn't briefly appear on the screen
            img.style.opacity = '0';
            // Image needs to be in the DOM for dimensions to be correct after render
            const originalParent = img.parentElement;
            document.body.appendChild(img);

            aspectRatio = img.width / img.height;
            originalParent.appendChild(img);
            img.removeAttribute('width');
            img.style.removeProperty('position');
            img.style.removeProperty('opacity');
        }
        const width = aspectRatio * this.MIN_ROW_HEIGHT;
        cell.style.flexGrow = width;
        cell.style.flexBasis = `${width}px`;
        cell.classList.remove('d-none');
        cell.classList.add('d-flex');
        cell.dataset.loaded = 'true';
    },
    /**
     * @override
     */
    _onShowOptimizedChange: function (ev) {
        this._toggleOptimized(ev.target.checked);
    },
    /**
     * @override
     */
    _onSearchSelect: function (ev) {
        const {value} = ev.target;
        this.searchService = value;
        this.$('.o_we_search').trigger('input');
    },
    /**
     * @private
     */
    _onSearchInput: function (ev) {
        this.libraryMedia = [];
        this._super(...arguments);
        this.$('.o_we_search_select').removeClass('d-none');
    },
    /**
     * @override
     */
    _clear: function (type) {
        // Not calling _super: we don't want to call the document widget's _clear method on images
        var allImgClasses = /(^|\s+)(img|img-\S*|o_we_custom_image|rounded-circle|rounded|thumbnail|shadow)(?=\s|$)/g;
        this.media.className = this.media.className && this.media.className.replace(allImgClasses, ' ');
    },
});


/**
 * Let users choose a document, including uploading a new document in odoo.
 */
var DocumentWidget = FileWidget.extend({
    template: 'wysiwyg.widgets.document',
    existingAttachmentsTemplate: 'wysiwyg.widgets.document.existing.attachments',

    /**
     * @constructor
     */
    init: function (parent, media, options) {
        options = _.extend({
            accept: '*/*',
            mimetypeDomain: [['mimetype', 'not in', this.IMAGE_MIMETYPES]],
        }, options || {});
        this._super(parent, media, options);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getAttachmentsDomain: function (needle) {
        var domain = this._super.apply(this, arguments);
        // the assets should not be part of the documents
        return domain.concat('!', utils.assetsDomain());
    },
});

/**
 * Let users choose a font awesome icon, support all font awesome loaded in the
 * css files.
 */
var IconWidget = SearchableMediaWidget.extend({
    template: 'wysiwyg.widgets.font-icons',
    events: _.extend({}, SearchableMediaWidget.prototype.events || {}, {
        'click .font-icons-icon': '_onIconClick',
    }),

    /**
     * @constructor
     */
    init: function (parent, media) {
        this._super.apply(this, arguments);

        fonts.computeFonts();
        this.iconsParser = fonts.fontIcons;
        this.alias = _.flatten(_.map(this.iconsParser, function (data) {
            return data.alias;
        }));
    },
    /**
     * @override
     */
    start: function () {
        this.$icons = this.$('.font-icons-icon');
        var classes = (this.media && this.media.className || '').split(/\s+/);
        for (var i = 0; i < classes.length; i++) {
            var cls = classes[i];
            if (_.contains(this.alias, cls)) {
                this.selectedIcon = cls;
                this.initialIcon = cls;
                this._highlightSelectedIcon();
            }
        }

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    save: function () {
        var style = this.$media.attr('style') || '';
        var iconFont = this._getFont(this.selectedIcon) || {base: 'fa', font: ''};
        if (!this.$media.is('span, i')) {
            var $span = $('<span/>');
            $span.data(this.$media.data());
            this.$media = $span;
            this.media = this.$media[0];
            style = style.replace(/\s*width:[^;]+/, '');
        }
        this.$media.removeClass(this.initialIcon).addClass([iconFont.base, iconFont.font]);
        this.$media.attr('style', style || null);
        return Promise.resolve(this.media);
    },
    /**
     * @override
     */
    search: function (needle) {
        var iconsParser = this.iconsParser;
        if (needle && needle.length) {
            iconsParser = [];
            _.filter(this.iconsParser, function (data) {
                var cssData = _.filter(data.cssData, function (cssData) {
                    return _.find(cssData.names, function (alias) {
                        return alias.indexOf(needle) >= 0;
                    });
                });
                if (cssData.length) {
                    iconsParser.push({
                        base: data.base,
                        cssData: cssData,
                    });
                }
            });
        }
        this.$('div.font-icons-icons').html(
            QWeb.render('wysiwyg.widgets.font-icons.icons', {iconsParser: iconsParser, widget: this})
        );
        return Promise.resolve();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _clear: function () {
        var allFaClasses = /(^|\s)(fa|(text-|bg-|fa-)\S*|rounded-circle|rounded|thumbnail|shadow)(?=\s|$)/g;
        this.media.className = this.media.className && this.media.className.replace(allFaClasses, ' ');
    },
    /**
     * @private
     */
    _getFont: function (classNames) {
        if (!(classNames instanceof Array)) {
            classNames = (classNames || "").split(/\s+/);
        }
        var fontIcon, cssData;
        for (var k = 0; k < this.iconsParser.length; k++) {
            fontIcon = this.iconsParser[k];
            for (var s = 0; s < fontIcon.cssData.length; s++) {
                cssData = fontIcon.cssData[s];
                if (_.intersection(classNames, cssData.names).length) {
                    return {
                        base: fontIcon.base,
                        parser: fontIcon.parser,
                        font: cssData.names[0],
                    };
                }
            }
        }
        return null;
    },
    /**
     * @private
     */
    _highlightSelectedIcon: function () {
        var self = this;
        this.$icons.removeClass('o_we_attachment_selected');
        this.$icons.filter(function (i, el) {
            return _.contains($(el).data('alias').split(','), self.selectedIcon);
        }).addClass('o_we_attachment_selected');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onIconClick: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        this.selectedIcon = $(ev.currentTarget).data('id');
        this._highlightSelectedIcon();
        this.trigger_up('save_request');
    },
});

/**
 * Let users choose a video, support embed iframe.
 */
const VideoWidget = FileWidget.extend({
    template: 'wysiwyg.widgets.video',
    existingAttachmentsTemplate: 'wysiwyg.widgets.video.existing.attachments',
    events: Object.assign({}, FileWidget.prototype.events, {
        'change .o_video_dialog_options input': '_onUpdateVideoOption',
        'input input#o_video_text': '_onVideoCodeInput',
        'change input#o_video_text': '_onVideoCodeChange',
        'click .o_show_url_button': '_saveURL',
    }),
    NUMBER_OF_ATTACHMENTS_TO_DISPLAY: 8,

    /**
     * @constructor
     */
    init(parent, media, options) {
        this.widgetType = 'video';
        options = _.extend({
            accept: 'video/mp4',
            mimetypeDomain: [['mimetype', 'in', this.VIDEO_MIMETYPES]],
        }, options || {});
        this.isForBgVideo = !!options.isForBgVideo;
        this._onVideoCodeInput = _.debounce(this._onVideoCodeInput, 1000);
        // Video upload size limit check on client side before uploading - 128Mb
        this._sizeLimit = 128 * (1024 ** 2);
        this._super(parent, media, options);
    },
    /**
     * @override
     */
    async start() {
        const _super = this._super.bind(this);
        this.$content = this.$('.o_video_dialog_iframe');

        if (this.media) {
            var $media = $(this.media);
            var src = $media.data('oe-expression') || $media.data('src') || ($media.is('iframe') ? $media.attr('src') : '') || '';
            this.$('input#o_video_text').val(src);

            this.$('input#o_video_autoplay').prop('checked', src.indexOf('autoplay=1') >= 0);
            this.$('input#o_video_hide_controls').prop('checked', src.indexOf('controls=0') >= 0);
            this.$('input#o_video_loop').prop('checked', src.indexOf('loop=1') >= 0);
            this.$('input#o_video_hide_fullscreen').prop('checked', src.indexOf('fs=0') >= 0);
            this.$('input#o_video_hide_yt_logo').prop('checked', src.indexOf('modestbranding=1') >= 0);
            this.$('input#o_video_hide_dm_logo').prop('checked', src.indexOf('ui-logo=0') >= 0);
            this.$('input#o_video_hide_dm_share').prop('checked', src.indexOf('sharing-enable=0') >= 0);
        }

        return _super(...arguments).then(widget => {
            this._updateVideo();
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async save() {
        const videoSrc = this.$content.attr('src');
        if (this.isForBgVideo) {
            if (!this.selectedAttachments.length) {
                await this._saveURL(); // Saving bg video embedded from URL
            }
            return Promise.resolve({bgVideoSrc: videoSrc});
        }
        const videoFrame = this.$('.o_video_dialog_iframe');
        if (videoFrame.is('iframe')) {
            this.$media = videoFrame.hasClass('o_user_upload') ? this.getWrappedVideo(videoFrame) : this.getWrappedIframe(videoSrc);
            this.media = this.$media[0];
            if (!this.selectedAttachments.length) {
                await this._saveURL(); // Saving video embedded from URL
            }
        }
        return Promise.resolve(this.media);
    },

    /**
     * Get an iframe wrapped for the website builder. Used for embedding
     * external videos.
     *
     * @param {string} src The video url.
     * @return {string} The HTML code for displaying the iframe
     */
    getWrappedIframe(src) {
        return $(
            '<div class="media_iframe_video" data-oe-expression="' + src + '">' +
                '<div class="css_editable_mode_display">&nbsp;</div>' +
                '<div class="media_iframe_video_size" contenteditable="false">&nbsp;</div>' +
                '<iframe src="' + src + '" frameborder="0" contenteditable="false" allowfullscreen="allowfullscreen"></iframe>' +
            '</div>'
        );
    },
    /**
     * Get a video element wrapped for the website builder. Used for uploaded
     * videos.
     *
     * @param video The video element.
     * @return {string} The HTML code for displaying the iframe
     */
    getWrappedVideo(video) {
        return $(
            '<div class="media_iframe_video" data-oe-expression="' + video.attr('src') + '">' +
                '<div class="css_editable_mode_display">&nbsp;</div>' +
                '<div class="media_iframe_video_size" contenteditable="false">&nbsp;</div>' +
                video.get(0).outerHTML +
            '</div>'
        );
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _renderThumbnails() {
        for (const att of this.attachments) {
            if (att.url) {
                // Renders the video provider as a text bubble on the thumbnail
                const processedURL = att.url.startsWith("//") ? "https:" + att.url.replace("player.", "") : att.url.replace("player.", "");
                att.thumbnailText = new URL(processedURL).hostname.replace("www.", "").split(".")[0];
                if (att.thumbnailText === "youtu") {
                    att.thumbnailText += "be";
                } else if (att.thumbnailText === "dai") {
                    att.thumbnailText += "lymotion";
                }
            } else if (att.media_src) {
                att.thumbnailText = "Uploaded";
            } else {
                att.thumbnailText = "Unknown";
            }
        }
        this._super(...arguments);
    },
    /**
     * @override
     */
    async _addData() {
        const files = [...this.$fileInput[0].files];
        if (files.filter(file => file.size > this._sizeLimit).length) {
            this.displayNotification({
                title: _t("File size too big"),
                message: _t("Please select a smaller video for upload, the current size limit for a single file is") + ` ${this._sizeLimit / (1024 ** 2)}Mb.`,
                type: 'danger',
            });
            return;
        }
        this._super();
    },
    /**
     * @private
     */
    _showUpload() {
        this.$('#video-preview').show();
        this.$('.o_video_dialog_options').show();
        this.$('#o_video_text:not(.o_collapsed_video_text)').prop('disabled', true).css('opacity', '0.5').val('');
    },
    /**
     * @private
     */
    _showURL() {
        this.$('#video-preview').show();
        this.$('.o_video_dialog_options').show();
        this.$('#o_video_text:not(.o_collapsed_video_text)').prop('disabled', false).css('opacity', '1');
    },
    /**
     * @private
     */
    _resetVideo() {
        this.$('#video-preview').hide();
        this.$('.o_video_dialog_options').hide();
        this.$('.o_video_dialog_iframe').attr('src', '');
        this.$('#o_video_text:not(.o_collapsed_video_text)').prop('disabled', false).css('opacity', '1');
    },
    /**
     * @private
     */
    _displayURLField() {
        this.$('.o_show_url_button').removeClass('o_visible_url_button').hide();
        this.$('#o_video_text').removeClass('o_collapsed_video_text').css('opacity', '1').val('').css('width', '100%');
        this.$('.o_invisible_placeholder').css('width', '0');
    },
    /**
     * @private
     */
    _hideURLField() {
        this.$('.o_show_url_button').addClass('o_visible_url_button').show();
        this.$('#o_video_text').addClass('o_collapsed_video_text').css('opacity', '0').css('width', '0');
        this.$('.o_invisible_placeholder').css('width', '100%');
    },
    /**
     * @override
     */
    async _selectAttachment(attachment, save, {type = 'attachment'} = {}) {
        this._resetVideo();
        const clickedOnNewUpload = attachment ? !(this.selectedAttachments.length) || this.selectedAttachments[0].media_src !== attachment.media_src : false;
        const clickedOnNewURL = attachment ? !(this.selectedAttachments.length) || this.selectedAttachments[0].url !== attachment.url : false;
        if (clickedOnNewURL && attachment.mimetype === 'video/url') {
            // Clicked on a saved URL attachment different from the current one
            this._hideURLField();
            this._super(attachment, false, {type: type});
            this.$('#o_video_text').val(attachment.url);
            this._showURL();
            await this._updateVideo();
        } else if (clickedOnNewUpload && attachment.mimetype === 'video/mp4') {
            // Clicked on an uploaded video attachment different from the current one
            this._hideURLField();
            this._showUpload();
            this._super(attachment, false, {type: type});
            await this._updateVideo();
        } else {
            // Clicked on the same attachment as currently selected so it deselects it or function
            // was called without an attachment or with an error to reset selection state.
            this.selectedAttachments = [];
            this.$('.o_we_attachment_selected').each(function () {
                this.classList.remove('o_we_attachment_selected');
            });
            if (type !== 'error') {
                this.$('#o_video_text').val('');
            } else {
                this.$('#video-preview').show();
            }
        }
    },
    /**
     * Creates a video node according to the given URL and options. If not
     * possible, returns an error code.
     *
     * @param {string} url
     * @param {Object} options
     * @returns {Object}
     *          $video -> the created video jQuery node
     *          platform -> the type of the created video
     *          errorCode -> if defined, either '0' for invalid URL or '1' for
     *              unsupported video provider
     */
    async _createVideoNode(url, options) {
        options = options || {};
        if (options['uploaded']) {
            const video = document.createElement('video');
            video.muted = options['muted'];
            video.defaultMuted = options['muted'];
            video.autoplay = options['autoplay'];
            video.preload = 'metadata';
            video.controls = !(options['controls']);
            video.loop = options['loop'];
            video.style.width = '100%';
            video.style.height = '90vh';
            // Store selected options as part of the src URL
            const autoplay = video.autoplay ? '?autoplay=1&mute=1' : '?autoplay=0';
            const controls = video.controls ? '&controls=1' : '&controls=0';
            const loop = video.loop ? '&loop=1' : '&loop=0';
            const source = url + autoplay + controls + loop;
            video.src = source;
            // Set to 0.01 for canvas thumbnail generation, otherwise thumbnail is black
            video.currentTime = 0.01;
            let thumbnail = document.createElement('canvas');
            const frame = document.createElement('iframe');
            frame.src = source;
            frame.srcdoc = video.outerHTML;
            frame.style.border = '0';
            frame.allowFullscreen = true;
            frame.contentEditable = 'false';
            frame.classList.add('o_video_dialog_iframe');
            frame.classList.add('o_user_upload');
            video.onloadeddata = () => {
                if (!frame.hasAttribute('thumbnail') && this.selectedAttachments.length && !this.selectedAttachments[0].thumbnail) {
                    // Reduce storage used in DB for thumbnail data
                    thumbnail.height = 120;
                    thumbnail.width = video.videoWidth / video.videoHeight * thumbnail.height;
                    const thumbnailContext = thumbnail.getContext('2d');
                    thumbnailContext.drawImage(video, 0, 0, thumbnail.width, thumbnail.height);
                    thumbnail = thumbnail.toDataURL('image/png');
                    this.attachments[this.attachments.indexOf(this.selectedAttachments[0])].thumbnail = thumbnail;
                    this._rpc({
                        route: '/web_editor/attachment/add_thumbnail',
                        params: {
                            attachment_id: this.selectedAttachments[0].id,
                            thumbnail_data: thumbnail,
                        },
                    }).then(this._renderThumbnails());
                }
            };
            const $frameContainer = $('<div>').attr('src', source);
            $frameContainer.append($(frame));
            return {$video: $frameContainer, platform: 'user_upload'};
        } else {
            const videoData = await this._getVideoURLData(url, options, false);
            if (videoData.error) {
                return {errorCode: 0};
            }
            if (!videoData.platform) {
                return {errorCode: 1};
            }
            const $video = $('<iframe>').width(1280).height(720)
                .css('border', 0)
                .attr('src', videoData.embed_url)
                .addClass('o_video_dialog_iframe');

            return {$video: $video, platform: videoData.platform};
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _clear: function () {
        if (this.media.dataset.src) {
            try {
                delete this.media.dataset.src;
            } catch (_e) {
                this.media.dataset.src = undefined;
            }
        }
        var allVideoClasses = /(^|\s)media_iframe_video(\s|$)/g;
        var isVideo = this.media.className && this.media.className.match(allVideoClasses);
        if (isVideo) {
            this.media.className = this.media.className.replace(allVideoClasses, ' ');
            this.media.innerHTML = '';
        }
    },
    /**
     * Updates the video preview according to video code and enabled options.
     *
     * @private
     */
    async _updateVideo() {
        // Reset the feedback
        this.$content.empty();
        this.$('#o_video_form_group').removeClass('o_has_error o_has_success').find('.form-control, .custom-select').removeClass('is-invalid is-valid');
        this.$('.o_video_dialog_options div').addClass('d-none');
        this._resetVideo();
        // Check video code
        const $text = this.$('input#o_video_text');
        const code = $text.val().trim();
        const $uploadedVideo = this.$('.o_we_attachment_selected');
        let query;
        const autoplayChecked = this.$('input#o_video_autoplay').is(':checked');
        if ($uploadedVideo.length && this.selectedAttachments.length && this.selectedAttachments[0].media_src) {
            this._showUpload();
            query = await this._createVideoNode(this.selectedAttachments[0].media_src, {
                'uploaded': true,
                'autoplay': this.isForBgVideo || autoplayChecked,
                'muted': this.isForBgVideo || autoplayChecked,
                'controls': this.isForBgVideo || this.$('input#o_video_hide_controls').is(':checked'),
                'loop': this.isForBgVideo || this.$('input#o_video_loop').is(':checked')
            });
        } else if (code) {
            if (code.includes('/web/content/')) {
                for (const attachment of this.attachments) {
                    if (code.includes(attachment['media_src'])) {
                        await this._selectAttachment(attachment, false);
                        await this._renderThumbnails();
                    }
                }
                if (!this.selectedAttachments.length) {
                    // /web/content URL provided but no such resource in attachments
                    const urlSplit = code.split('/');
                    if (urlSplit[3]) {
                        const idAndUnique = urlSplit[3].split('-');
                        let searchDomain = this._getAttachmentsDomain('');
                        searchDomain.push(['id', '=', idAndUnique[0]]);
                        // Attempt to fetch it from DB
                        const attachment = await this._rpc({
                            model: 'ir.attachment',
                            method: 'search_read',
                            args: [],
                            kwargs: {
                                domain: searchDomain,
                                fields: ['name', 'mimetype', 'description', 'checksum', 'url', 'type', 'res_id',
                                    'res_model', 'public', 'access_token', 'media_src', 'media_width', 'media_height', 'original_id',
                                    'thumbnail'],
                                order: [{name: 'id', asc: false}],
                                context: this.options.context,
                                limit: 1,
                                offset: 0,
                            }
                        });
                        if (attachment.length !== 0) {
                            this.previousAttachment = attachment[0];
                            await this._renderThumbnails();
                            await this._selectAttachment(attachment[0], false);
                        } else {
                            // Edge case, attachment was deleted but video SRC was not reset
                            this.$('#o_video_text').val('');
                            await this._updateVideo();
                        }
                    }
                }
            } else {
                this._showURL();
                // Detect if we have an embed code rather than an URL
                const embedMatch = code.match(/(src|href)=["']?([^"']+)?/);
                if (embedMatch && embedMatch[2].length > 0 && embedMatch[2].indexOf('instagram')) {
                    embedMatch[1] = embedMatch[2]; // Instagram embed code is different
                }
                const url = embedMatch ? embedMatch[1] : code;

                query = await this._createVideoNode(url, {
                    'autoplay': this.isForBgVideo || autoplayChecked,
                    'hide_controls': this.isForBgVideo || this.$('input#o_video_hide_controls').is(':checked'),
                    'loop': this.isForBgVideo || this.$('input#o_video_loop').is(':checked'),
                    'hide_fullscreen': this.isForBgVideo || this.$('input#o_video_hide_fullscreen').is(':checked'),
                    'hide_yt_logo': this.isForBgVideo || this.$('input#o_video_hide_yt_logo').is(':checked'),
                    'hide_dm_logo': this.isForBgVideo || this.$('input#o_video_hide_dm_logo').is(':checked'),
                    'hide_dm_share': this.isForBgVideo || this.$('input#o_video_hide_dm_share').is(':checked'),
                });
                if (!this.selectedAttachments.length) {
                    // Check if this URL was previously saved and select or fetch it
                    if (url) {
                        let attachment = [];
                        const videoData = await this._getVideoURLData(url, {}, false);
                        const embedURL = (videoData && !videoData.error) ? videoData.embed_url.split("?")[0] : false;
                        let currentURL;
                        let foundIndex;
                        for (const att of this.attachments) {
                            currentURL = att.url ? att.url.split("?")[0] : false;
                            if (currentURL && embedURL && currentURL === embedURL) {
                                attachment = [att];
                                foundIndex = this.attachments.indexOf(att);
                            }
                        }
                        if (attachment.length !== 0 && foundIndex !== -1) {
                            if (foundIndex >= this.numberOfAttachmentsToDisplay) {
                                this.previousAttachment = attachment[0];
                                await this._renderThumbnails();
                            }
                            await this._selectAttachment(attachment[0], false);
                        }
                        if (!attachment && embedURL) {
                            let searchDomain = this._getAttachmentsDomain("");
                            searchDomain.push(["url", "=like", `%${embedURL}%`]);
                            // Attempt to fetch it from DB
                            attachment = await this._rpc({
                                model: 'ir.attachment',
                                method: 'search_read',
                                args: [],
                                kwargs: {
                                    domain: searchDomain,
                                    fields: ['name', 'mimetype', 'description', 'checksum', 'url', 'type', 'res_id',
                                        'res_model', 'public', 'access_token', 'media_src', 'media_width', 'media_height', 'original_id',
                                        'thumbnail'],
                                    order: [{name: 'id', asc: false}],
                                    context: this.options.context,
                                    limit: 1,
                                    offset: 0,
                                }
                            });
                            if (attachment.length !== 0) {
                                this.previousAttachment = attachment[0];
                                await this._renderThumbnails();
                                await this._selectAttachment(attachment[0], false);
                            }
                        }
                    }
                }
                // Toggle URL validation classes
                this.$el.find('#o_video_form_group')
                    .toggleClass('o_has_error', !query.$video)
                    .find('.form-control, .custom-select')
                    .toggleClass('is-invalid', !query.$video)
                    .end()
                    .toggleClass('o_has_success', !!query.$video)
                    .find('.form-control, .custom-select')
                    .toggleClass('is-valid', !!query.$video);
            }
        }
        if (!query) {
            return;
        }
        const $optBox = this.$('.o_video_dialog_options');
        // Show / Hide preview elements
        this.$el.find('.o_video_dialog_preview_text, .media_iframe_video_size').add($optBox).toggleClass('d-none', !query.$video);

        // Individually show / hide options base on the video provider
        const $platformGroup = $optBox.find(`div.o_${query.platform}_option`).removeClass('d-none');
        const $platformOptions = $platformGroup.find("input[id^='o_video']");
        // Gray out and disable options that are non-configurable for bg videos
        $platformOptions.prop("checked", this.isForBgVideo ? true : $platformGroup.prop("checked")).prop("disabled", this.isForBgVideo);
        $platformGroup.css("opacity", this.isForBgVideo ? '0.5' : '1');
        const $autoplay = $optBox.find('#o_video_autoplay');
        $autoplay.prop("checked", this.isForBgVideo ? true : $autoplay.prop("checked")).prop("disabled", this.isForBgVideo);
        const $loop = $optBox.find('#o_video_loop');
        $loop.prop("checked", this.isForBgVideo ? true : $loop.prop("checked")).prop("disabled", this.isForBgVideo);
        const $hideControls = $optBox.find('#o_video_hide_controls');
        $hideControls.prop("checked", this.isForBgVideo ? true : $hideControls.prop("checked")).prop("disabled", this.isForBgVideo);
        // Hide the entire options box if no options are available
        $optBox.toggleClass('d-none', $optBox.find('div:not(.d-none)').length === 0);

        if (query.platform === 'youtube') {
            // Youtube only: If 'hide controls' is checked, hide 'fullscreen'
            // and 'youtube logo' options too
            this.$('input#o_video_hide_fullscreen, input#o_video_hide_yt_logo').closest('div')
                .toggleClass('d-none', this.$('input#o_video_hide_controls').is(':checked'));
        }
        let $content = query.$video;
        if (!$content) {
            switch (query.errorCode) {
                case 0:
                    $content = $('<div/>', {
                        class: 'alert alert-danger o_video_dialog_iframe mb-2 mt-2',
                        text: _t("The provided url is not valid"),
                    });
                    break;
                case 1:
                    $content = $('<div/>', {
                        class: 'alert alert-warning o_video_dialog_iframe mb-2 mt-2',
                        text: _t("The provided url does not reference any supported video"),
                    });
                    break;
            }
            await this._selectAttachment(undefined, false, {type: "error"});
        }
        this.$content.replaceWith($content);
        this.$content = $content;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a video option changes -> Updates the video preview.
     *
     * @private
     */
    _onUpdateVideoOption() {
        this._updateVideo();
    },

    /**
     * Saves the currently pasted URL as an attachment. It gets a snapshot of the rendered
     * preview as the thumbnail, uses the video name as the attachment's name.
     *
     * @private
     */
    async _saveURL() {
        const $videoTextField = this.$('#o_video_text');
        if (!$videoTextField.hasClass("o_collapsed_video_text")) {
            const url = $videoTextField.val().trim();
            const options = {
                'uploaded': false,
                'autoplay': this.isForBgVideo || this.$('input#o_video_autoplay').is(':checked'),
                'muted': this.isForBgVideo || this.$('input#o_video_autoplay').is(':checked'),
                'controls': this.isForBgVideo || this.$('input#o_video_hide_controls').is(':checked'),
                'loop': this.isForBgVideo || this.$('input#o_video_loop').is(':checked')
            };
            const videoData = await this._getVideoURLData(url, options, true);
            if (!videoData.error && videoData.platform) {
                const thumbnail = "data:image/png;base64," + videoData.thumbnail;
                const attachment = await this._rpc({
                    route: '/web_editor/attachment/add_data',
                    params: {
                        'name': videoData.name,
                        'data': false,
                        'url': videoData.embed_url,
                        'res_id': this.options.res_id,
                        'res_model': this.options.res_model,
                        'filetype': "video_url",
                        'thumbnail': thumbnail,
                    }
                }, 0);
                this.previousAttachment = attachment;
                await this._selectAttachment(attachment, false);
                this.attachments.push(attachment);
                await this._renderThumbnails();
            } else {
                return {errorCode: 0};
            }
        } else {
            this._displayURLField();
            await this._selectAttachment(false);
        }
    },
    /**
     * Called when the video code (URL / Iframe) change is confirmed -> Updates
     * the video preview immediately.
     *
     * @private
     */
    _onVideoCodeChange() {
        this._updateVideo();
    },
    /**
     * Called when the video code (URL / Iframe) changes -> Updates the video
     * preview (note: this function is automatically debounced).
     *
     * @private
     */
    _onVideoCodeInput() {
        this._updateVideo();
    },
    /**
     * Parses a URL and returns the provider type and an emebedable URL.
     *
     * @private
     */
    _getVideoURLData(url, options, toSave) {
        return this._rpc({
            route: '/web_editor/video_url/data',
            params: Object.assign({video_url: url, to_save: toSave}, options),
        });
    },
});

return {
    MediaWidget: MediaWidget,
    SearchableMediaWidget: SearchableMediaWidget,
    FileWidget: FileWidget,
    ImageWidget: ImageWidget,
    DocumentWidget: DocumentWidget,
    IconWidget: IconWidget,
    VideoWidget: VideoWidget,
};
});
