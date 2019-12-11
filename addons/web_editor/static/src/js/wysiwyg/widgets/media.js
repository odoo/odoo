odoo.define('wysiwyg.widgets.media', function (require) {
'use strict';

var concurrency = require('web.concurrency');
var config = require('web.config');
var core = require('web.core');
var Dialog = require('web.Dialog');
var dom = require('web.dom');
var fonts = require('wysiwyg.fonts');
var ImageOptimizeDialog = require('wysiwyg.widgets.image_optimize_dialog').ImageOptimizeDialog;
var utils = require('web.utils');
var Widget = require('web.Widget');
var session = require('web.session');

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
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onSearchInput: function (ev) {
        this.search($(ev.currentTarget).val() || '');
        this.hasSearched = true;
    },
});

/**
 * Let users choose a file, including uploading a new file in odoo.
 */
var FileWidget = SearchableMediaWidget.extend({
    events: _.extend({}, SearchableMediaWidget.prototype.events || {}, {
        'click .o_upload_media_button': '_onUploadButtonClick',
        'click .o_we_quick_upload': '_onQuickUploadClick',
        'change .o_file_input': '_onFileInputChange',
        'click .o_upload_media_url_button': '_onUploadURLButtonClick',
        'input .o_we_url_input': '_onURLInputChange',
        'click .o_existing_attachment_cell': '_onAttachmentClick',
        'dblclick .o_existing_attachment_cell': '_onAttachmentDblClick',
        'click .o_existing_attachment_remove': '_onRemoveClick',
        'click .o_existing_attachment_optimize': '_onExistingOptimizeClick',
        'click .o_load_more': '_onLoadMoreClick',
    }),
    existingAttachmentsTemplate: undefined,

    IMAGE_MIMETYPES: ['image/gif', 'image/jpe', 'image/jpeg', 'image/jpg', 'image/gif', 'image/png', 'image/svg+xml'],
    NUMBER_OF_ATTACHMENTS_TO_DISPLAY: 30,

    // This factor is used to take into account that an image displayed in a BS
    // column might get bigger when displayed on a smaller breakpoint if that
    // breakpoint leads to have less columns.
    // Eg. col-lg-6 -> 480px per column -> col-md-12 -> 720px per column -> 1.5
    // However this will not be enough if going from 3 or more columns to 1, but
    // in that case, we consider it a snippet issue.
    OPTIMIZE_SIZE_FACTOR: 1.5,

    /**
     * @constructor
     */
    init: function (parent, media, options) {
        this._super.apply(this, arguments);
        this._mutex = new concurrency.Mutex();

        this.numberOfAttachmentsToDisplay = this.NUMBER_OF_ATTACHMENTS_TO_DISPLAY;

        this.options = _.extend({
            firstFilters: [],
            lastFilters: [],
            showQuickUpload: config.isDebug(),
        }, options || {});

        this.attachments = [];
        this.selectedAttachments = [];

        this._onUploadURLButtonClick = dom.makeAsyncHandler(this._onUploadURLButtonClick);
    },
    /**
     * Loads all the existing images related to the target media.
     *
     * @override
     */
    willStart: function () {
        return Promise.all([
            this._super.apply(this, arguments),
            this.search('', true)
        ]);
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

        this._renderImages();

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
        if (o.url) {
            self._selectAttachement(_.find(self.attachments, function (attachment) {
                return attachment.url === o.url;
            }) || o);
        }

        return def;
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
     * @param {boolean} noRender: if true, do not render the found attachments
     */
    search: function (needle, noRender) {
        var self = this;

        return this._rpc({
            model: 'ir.attachment',
            method: 'search_read',
            args: [],
            kwargs: {
                domain: this._getAttachmentsDomain(needle),
                fields: ['name', 'mimetype', 'checksum', 'url', 'type', 'res_id', 'res_model', 'public', 'access_token', 'image_src', 'image_width', 'image_height'],
                order: [{name: 'id', asc: false}],
                context: this.options.context,
            },
        }).then(function (attachments) {
            self.attachments = _.chain(attachments)
                .sortBy(function (r) {
                    if (_.any(self.options.firstFilters, function (filter) {
                        var regex = new RegExp(filter, 'i');
                        return r.name && r.name.match(regex);
                    })) {
                        return -1;
                    }
                    if (_.any(self.options.lastFilters, function (filter) {
                        var regex = new RegExp(filter, 'i');
                        return r.name && r.name.match(regex);
                    })) {
                        return 1;
                    }
                    return 0;
                })
                .value();
            if (!noRender) {
                self._renderImages();
            }
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _clear: function () {
        if (this.$media.is('img')) {
            return;
        }
        var allImgClasses = /(^|\s+)((img(\s|$)|img-(?!circle|rounded|thumbnail))[^\s]*)/g;
        var allImgClassModifiers = /(^|\s+)(rounded-circle|shadow|rounded|img-thumbnail|mx-auto)([^\s]*)/g;
        this.media.className = this.media.className && this.media.className
            .replace('o_we_custom_image', '')
            .replace(allImgClasses, ' ')
            .replace(allImgClassModifiers, ' ');
    },
    /**
     * Computes and returns the width that a new attachment should have to
     * ideally occupy the space where it will be inserted.
     * Only relevant for images.
     *
     * @see options.mediaWidth
     * @see OPTIMIZE_SIZE_FACTOR
     *
     * @private
     * @returns {integer}
     */
    _computeOptimizedWidth: function () {
        return Math.min(1920, parseInt(this.options.mediaWidth * this.OPTIMIZE_SIZE_FACTOR));
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
        domain.push('!', ['name', '=like', '%.crop']);
        domain.push('|', ['type', '=', 'binary'], ['url', '!=', false]);
        return domain;
    },
    /**
     * @private
     */
    _highlightSelected: function () {
        var self = this;
        this.$('.o_existing_attachment_cell.o_we_attachment_selected').removeClass("o_we_attachment_selected");
        _.each(this.selectedAttachments, function (attachment) {
            self.$('.o_existing_attachment_cell[data-id=' + attachment.id + ']').addClass("o_we_attachment_selected");
        });
    },
    /**
     * @private
     * @param {object} attachment
     */
    _handleNewAttachment: function (attachment) {
        this.attachments.unshift(attachment);
        this._renderImages();
        this._selectAttachement(attachment);
    },
    /**
     * @private
     * @returns {Promise}
     */
    _loadMoreImages: function (forceSearch) {
        this.numberOfAttachmentsToDisplay += 10;
        if (!forceSearch) {
            this._renderImages();
            return Promise.resolve();
        } else {
            return this.search(this.$('.o_we_search').val() || '');
        }
    },
    /**
     * Opens the image optimize dialog for the given attachment.
     *
     * Hides the media dialog while the optimize dialog is open to avoid an
     * overlap of modals.
     *
     * @private
     * @param {object} attachment
     * @param {boolean} isExisting: whether this is a new attachment that was
     *  just uploaded, or an existing attachment
     * @returns {Promise} resolved with the updated attachment object when the
     *  optimize dialog is saved. Rejected if the dialog is otherwise closed.
     */
    _openImageOptimizeDialog: function (attachment, isExisting) {
        var self = this;
        var promise = new Promise(function (resolve, reject) {
            self.trigger_up('hide_parent_dialog_request');
            var optimizeDialog = new ImageOptimizeDialog(self, {
                attachment: attachment,
                isExisting: isExisting,
                optimizedWidth: self._computeOptimizedWidth(),
            }).open();
            optimizeDialog.on('attachment_updated', self, function (ev) {
                optimizeDialog.off('closed');
                resolve(ev.data);
            });
            optimizeDialog.on('closed', self, function () {
                self.noSave = true;
                if (isExisting) {
                    reject();
                } else {
                    resolve(attachment);
                }
            });
        });
        var always = function () {
            self.trigger_up('show_parent_dialog_request');
        };
        promise.then(always).guardedCatch(always);
        return promise;
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
    _renderImages: function () {
        var attachments = this.attachments.slice(0, this.numberOfAttachmentsToDisplay);

        // Render menu & content
        this.$('.o_we_existing_attachments').replaceWith(
            this._renderExisting(attachments)
        );

        this._highlightSelected();

        // adapt load more
        var noLoadMoreButton = this.NUMBER_OF_ATTACHMENTS_TO_DISPLAY >= this.attachments.length;
        var noMoreImgToLoad = this.numberOfAttachmentsToDisplay >= this.attachments.length;
        this.$('.o_load_done_msg').toggleClass('d-none', noLoadMoreButton || !noMoreImgToLoad);
        this.$('.o_load_more').toggleClass('d-none', noMoreImgToLoad);
    },
    /**
     * @private
     * @returns {Promise}
     */
    _save: function () {
        var self = this;

        if (this.options.multiImages) {
            return Promise.resolve(this.selectedAttachments);
        }

        var img = this.selectedAttachments[0];
        if (!img || !img.id) {
            return Promise.resolve(this.media);
        }

        var prom;
        if (!img.public && !img.access_token) {
            prom = this._rpc({
                model: 'ir.attachment',
                method: 'generate_access_token',
                args: [[img.id]]
            }).then(function (access_token) {
                img.access_token = access_token[0];
            });
        }

        return Promise.resolve(prom).then(function () {
            if (img.image_src) {
                var src = img.image_src;
                if (!img.public && img.access_token) {
                    src += _.str.sprintf('?access_token=%s', img.access_token);
                }
                if (!self.$media.is('img')) {

                    // Note: by default the images receive the bootstrap opt-in
                    // img-fluid class. We cannot make them all responsive
                    // by design because of libraries and client databases img.
                    self.$media = $('<img/>', {class: 'img-fluid o_we_custom_image'});
                    self.media = self.$media[0];
                }
                self.$media.attr('src', src);
            } else {
                if (!self.$media.is('a')) {
                    $('.note-control-selection').hide();
                    self.$media = $('<a/>');
                    self.media = self.$media[0];
                }
                var href = '/web/content/' + img.id + '?';
                if (!img.public && img.access_token) {
                    href += _.str.sprintf('access_token=%s&', img.access_token);
                }
                href += 'unique=' + img.checksum + '&download=true';
                self.$media.attr('href', href);
                self.$media.addClass('o_image').attr('title', img.name).attr('data-mimetype', img.mimetype);
            }

            self.$media.attr('alt', img.alt);
            var style = self.style;
            if (style) {
                self.$media.css(style);
            }

            // Remove crop related attributes
            if (self.$media.attr('data-aspect-ratio')) {
                var attrs = ['aspect-ratio', 'x', 'y', 'width', 'height', 'rotate', 'scale-x', 'scale-y', 'crop:originalSrc'];
                self.$media.removeClass('o_cropped_img_to_save');
                _.each(attrs, function (attr) {
                    self.$media.removeData(attr);
                    self.$media.removeAttr('data-' + attr);
                });
            }
            return self.media;
        });
    },
    /**
     * @param {object} attachment
     * @param {boolean} [save=true] to save the given attachment in the DOM and
     *  and to close the media dialog
     * @private
     */
    _selectAttachement: function (attachment, save) {
        if (this.options.multiImages) {
            // if the clicked attachment is already selected then unselect it
            // unless it was a save request (then keep the current selection)
            var index = this.selectedAttachments.indexOf(attachment);
            if (index !== -1) {
                if (!save) {
                    this.selectedAttachments.splice(index, 1);
                }
            } else {
                // if the clicked attachment is not selected, add it to selected
                this.selectedAttachments.push(attachment);
            }
        } else {
            // select the clicked attachment
            this.selectedAttachments = [attachment];
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
    _onAttachmentClick: function (ev, save) {
        var $attachment = $(ev.currentTarget);
        var attachment = _.find(this.attachments, {id: $attachment.data('id')});
        this._selectAttachement(attachment, save);
    },
    /**
     * @private
     */
    _onAttachmentDblClick: function (ev) {
        this._onAttachmentClick(ev, true);
    },
    /**
     * @private
     */
    _onExistingOptimizeClick: function (ev) {
        var self = this;
        var $a = $(ev.currentTarget).closest('.o_existing_attachment_cell');
        var id = parseInt($a.data('id'), 10);
        var attachment = _.findWhere(this.attachments, {id: id});
        ev.stopPropagation();
        return this._openImageOptimizeDialog(attachment, true).then(function (newAttachment) {
            self._handleNewAttachment(newAttachment);
        });
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
    _addData: function () {
        var self = this;
        var uploadMutex = new concurrency.Mutex();
        var optimizeMutex = new concurrency.Mutex();

        // Upload the smallest file first to block the user the least possible.
        var files = _.sortBy(this.$fileInput[0].files, 'size');

        _.each(files, function (file) {
            // Upload one file at a time: no need to parallel as upload is
            // limited by bandwidth.
            uploadMutex.exec(function () {
                return utils.getDataURLFromFile(file).then(function (result) {
                    var params = {
                        'name': file.name,
                        'data': result.split(',')[1],
                        'res_id': self.options.res_id,
                        'res_model': self.options.res_model,
                        'filters': self.options.firstFilters.join('_'),
                    };
                    if (self.quickUpload) {
                        params['width'] = self._computeOptimizedWidth();
                        params['quality'] = 80;
                    } else {
                        params['width'] = 0;
                        params['quality'] = 0;
                    }
                    return self._rpc({
                        route: '/web_editor/attachment/add_data',
                        params: params,
                    }).then(function (attachment) {
                        if (attachment.image_src && !self.quickUpload) {
                            optimizeMutex.exec(function () {
                                return self._openImageOptimizeDialog(attachment).then(function (updatedAttachment) {
                                    self._handleNewAttachment(updatedAttachment);
                                });
                            });
                        } else {
                            self._handleNewAttachment(attachment);
                        }
                    });
                });
            });
        });

        return uploadMutex.getUnlockedDef().then(function () {
            return optimizeMutex.getUnlockedDef().then(function () {
                self.quickUpload = false;
                if (!self.options.multiImages && !self.noSave) {
                    self.trigger_up('save_request');
                }
                self.noSave = false;
            });
        });
    },
    /**
     * @private
     */
    _onQuickUploadClick: function () {
        this.quickUpload = true;
        this.$uploadButton.trigger('click');
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
                        if (!self.attachments.length) {
                            self._renderImages(); //render the message and image if empty
                        } else {
                            $a.closest('.o_existing_attachment_cell').remove();
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
        var inputValue = this.$urlInput.val();
        var emptyValue = (inputValue === '');

        var isURL = /^.+\..+$/.test(inputValue); // TODO improve
        var isImage = _.any(['.gif', '.jpeg', '.jpe', '.jpg', '.png'], function (format) {
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
                'filters': this.options.firstFilters.join('_'),
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
        this.numberOfAttachmentsToDisplay = this.NUMBER_OF_ATTACHMENTS_TO_DISPLAY;
        this._super.apply(this, arguments);
    },
});

/**
 * Let users choose an image, including uploading a new image in odoo.
 */
var ImageWidget = FileWidget.extend({
    template: 'wysiwyg.widgets.image',
    existingAttachmentsTemplate: 'wysiwyg.widgets.image.existing.attachments',

    /**
     * @constructor
     */
    init: function (parent, media, options) {
        options = _.extend({
            accept: 'image/*',
            mimetypeDomain: [['mimetype', 'in', this.IMAGE_MIMETYPES]],
        }, options || {});
        this._super(parent, media, options);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _updateAddUrlUi: function (emptyValue, isURL, isImage) {
        this._super.apply(this, arguments);
        this.$addUrlButton.text((isURL && !isImage) ? _t("Add as document") : _t("Add image"));
        this.$urlWarning.toggleClass('d-none', !isURL || isImage);
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
    _updateAddUrlUi: function (emptyValue, isURL, isImage) {
        this._super.apply(this, arguments);
        this.$addUrlButton.text((isURL && isImage) ? _t("Add as image") : _t("Add document"));
        this.$urlWarning.toggleClass('d-none', !isURL || !isImage);
    },
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
        'dblclick .font-icons-icon': '_onIconDblClick',
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
                this._highlightSelectedIcon();
            }
        }
        this.nonIconClasses = _.without(classes, 'media_iframe_video', this.selectedIcon);

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
        var finalClasses = _.uniq(this.nonIconClasses.concat([iconFont.base, iconFont.font]));
        if (!this.$media.is('span')) {
            var $span = $('<span/>');
            $span.data(this.$media.data());
            this.$media = $span;
            this.media = this.$media[0];
            style = style.replace(/\s*width:[^;]+/, '');
        }
        this.$media.attr({
            class: _.compact(finalClasses).join(' '),
            style: style || null,
        });
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
        var allFaClasses = /(^|\s)(fa(\s|$)|fa-[^\s]*)/g;
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
    },
    /**
     * @private
     */
    _onIconDblClick: function () {
        this.trigger_up('save_request');
    },
});

/**
 * Let users choose a video, support all summernote video, and embed iframe.
 */
var VideoWidget = MediaWidget.extend({
    template: 'wysiwyg.widgets.video',
    events: _.extend({}, MediaWidget.prototype.events || {}, {
        'change .o_video_dialog_options input': '_onUpdateVideoOption',
        'input textarea#o_video_text': '_onVideoCodeInput',
        'change textarea#o_video_text': '_onVideoCodeChange',
    }),

    /**
     * @constructor
     */
    init: function (parent, media, options) {
        this._super.apply(this, arguments);
        this.isForBgVideo = !!options.isForBgVideo;
        this._onVideoCodeInput = _.debounce(this._onVideoCodeInput, 1000);
    },
    /**
     * @override
     */
    start: function () {
        this.$content = this.$('.o_video_dialog_iframe');

        if (this.media) {
            var $media = $(this.media);
            var src = $media.data('oe-expression') || $media.data('src') || ($media.is('iframe') ? $media.attr('src') : '') || '';
            this.$('textarea#o_video_text').val(src);

            this.$('input#o_video_autoplay').prop('checked', src.indexOf('autoplay=1') >= 0);
            this.$('input#o_video_hide_controls').prop('checked', src.indexOf('controls=0') >= 0);
            this.$('input#o_video_loop').prop('checked', src.indexOf('loop=1') >= 0);
            this.$('input#o_video_hide_fullscreen').prop('checked', src.indexOf('fs=0') >= 0);
            this.$('input#o_video_hide_yt_logo').prop('checked', src.indexOf('modestbranding=1') >= 0);
            this.$('input#o_video_hide_dm_logo').prop('checked', src.indexOf('ui-logo=0') >= 0);
            this.$('input#o_video_hide_dm_share').prop('checked', src.indexOf('sharing-enable=0') >= 0);

            this._updateVideo();
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
        this._updateVideo();
        if (this.isForBgVideo) {
            return Promise.resolve({bgVideoSrc: this.$content.attr('src')});
        }
        if (this.$('.o_video_dialog_iframe').is('iframe')) {
            this.$media = $(
                '<div class="media_iframe_video" data-oe-expression="' + this.$content.attr('src') + '">' +
                    '<div class="css_editable_mode_display">&nbsp;</div>' +
                    '<div class="media_iframe_video_size" contenteditable="false">&nbsp;</div>' +
                    '<iframe src="' + this.$content.attr('src') + '" frameborder="0" contenteditable="false"></iframe>' +
                '</div>'
            );
            this.media = this.$media[0];
        }
        return Promise.resolve(this.media);
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
            } catch (e) {
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
     * Creates a video node according to the given URL and options. If not
     * possible, returns an error code.
     *
     * @private
     * @param {string} url
     * @param {Object} options
     * @returns {Object}
     *          $video -> the created video jQuery node
     *          type -> the type of the created video
     *          errorCode -> if defined, either '0' for invalid URL or '1' for
     *              unsupported video provider
     */
    _createVideoNode: function (url, options) {
        options = options || {};

        // Video url patterns(youtube, instagram, vimeo, dailymotion, youku, ...)
        var ytRegExp = /^(?:(?:https?:)?\/\/)?(?:www\.)?(?:youtu\.be\/|youtube(-nocookie)?\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))((?:\w|-){11})(?:\S+)?$/;
        var ytMatch = url.match(ytRegExp);

        var insRegExp = /(.*)instagram.com\/p\/(.[a-zA-Z0-9]*)/;
        var insMatch = url.match(insRegExp);

        var vinRegExp = /\/\/vine.co\/v\/(.[a-zA-Z0-9]*)/;
        var vinMatch = url.match(vinRegExp);

        var vimRegExp = /\/\/(player.)?vimeo.com\/([a-z]*\/)*([0-9]{6,11})[?]?.*/;
        var vimMatch = url.match(vimRegExp);

        var dmRegExp = /.+dailymotion.com\/(video|hub|embed)\/([^_]+)[^#]*(#video=([^_&]+))?/;
        var dmMatch = url.match(dmRegExp);

        var ykuRegExp = /(.*).youku\.com\/(v_show\/id_|embed\/)(.+)/;
        var ykuMatch = url.match(ykuRegExp);

        var $video = $('<iframe>').width(1280).height(720).attr('frameborder', 0).addClass('o_video_dialog_iframe');
        var videoType = 'yt';

        if (!/^(http:\/\/|https:\/\/|\/\/)[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(\/.*)?$/i.test(url)){
            return {errorCode: 0};
        }

        var autoplay = options.autoplay ? '?autoplay=1&mute=1' : '?autoplay=0';

        if (ytMatch && ytMatch[2].length === 11) {
            $video.attr('src', '//www.youtube' + (ytMatch[1] || '') + '.com/embed/' + ytMatch[2] + autoplay);
        } else if (insMatch && insMatch[2].length) {
            $video.attr('src', '//www.instagram.com/p/' + insMatch[2] + '/embed/');
            videoType = 'ins';
        } else if (vinMatch && vinMatch[0].length) {
            $video.attr('src', vinMatch[0] + '/embed/simple');
            videoType = 'vin';
        } else if (vimMatch && vimMatch[3].length) {
            $video.attr('src', '//player.vimeo.com/video/' + vimMatch[3] + autoplay.replace('mute', 'muted'));
            videoType = 'vim';
        } else if (dmMatch && dmMatch[2].length) {
            var justId = dmMatch[2].replace('video/', '');
            $video.attr('src', '//www.dailymotion.com/embed/video/' + justId + autoplay);
            videoType = 'dm';
        } else if (ykuMatch && ykuMatch[3].length) {
            var ykuId = ykuMatch[3].indexOf('.html?') >= 0 ? ykuMatch[3].substring(0, ykuMatch[3].indexOf('.html?')) : ykuMatch[3];
            $video.attr('src', '//player.youku.com/embed/' + ykuId);
            videoType = 'yku';
        } else {
            return {errorCode: 1};
        }

        if (ytMatch) {
            $video.attr('src', $video.attr('src') + '&rel=0');
        }
        if (options.loop && (ytMatch || vimMatch)) {
            var videoSrc = _.str.sprintf('%s&loop=1', $video.attr('src'));
            $video.attr('src', ytMatch ? _.str.sprintf('%s&playlist=%s', videoSrc, ytMatch[2]) : videoSrc);
        }
        if (options.hide_controls && (ytMatch || dmMatch)) {
            $video.attr('src', $video.attr('src') + '&controls=0');
        }
        if (options.hide_fullscreen && ytMatch) {
            $video.attr('src', $video.attr('src') + '&fs=0');
        }
        if (options.hide_yt_logo && ytMatch) {
            $video.attr('src', $video.attr('src') + '&modestbranding=1');
        }
        if (options.hide_dm_logo && dmMatch) {
            $video.attr('src', $video.attr('src') + '&ui-logo=0');
        }
        if (options.hide_dm_share && dmMatch) {
            $video.attr('src', $video.attr('src') + '&sharing-enable=0');
        }

        return {$video: $video, type: videoType};
    },
    /**
     * Updates the video preview according to video code and enabled options.
     *
     * @private
     */
    _updateVideo: function () {
        // Reset the feedback
        this.$content.empty();
        this.$('#o_video_form_group').removeClass('o_has_error o_has_success').find('.form-control, .custom-select').removeClass('is-invalid is-valid');
        this.$('.o_video_dialog_options div').addClass('d-none');

        // Check video code
        var $textarea = this.$('textarea#o_video_text');
        var code = $textarea.val().trim();
        if (!code) {
            return;
        }

        // Detect if we have an embed code rather than an URL
        var embedMatch = code.match(/(src|href)=["']?([^"']+)?/);
        if (embedMatch && embedMatch[2].length > 0 && embedMatch[2].indexOf('instagram')) {
            embedMatch[1] = embedMatch[2]; // Instagram embed code is different
        }
        var url = embedMatch ? embedMatch[1] : code;

        var query = this._createVideoNode(url, {
            'autoplay': this.isForBgVideo || this.$('input#o_video_autoplay').is(':checked'),
            'hide_controls': this.isForBgVideo || this.$('input#o_video_hide_controls').is(':checked'),
            'loop': this.isForBgVideo || this.$('input#o_video_loop').is(':checked'),
            'hide_fullscreen': this.isForBgVideo || this.$('input#o_video_hide_fullscreen').is(':checked'),
            'hide_yt_logo': this.isForBgVideo || this.$('input#o_video_hide_yt_logo').is(':checked'),
            'hide_dm_logo': this.isForBgVideo || this.$('input#o_video_hide_dm_logo').is(':checked'),
            'hide_dm_share': this.isForBgVideo || this.$('input#o_video_hide_dm_share').is(':checked'),
        });

        var $optBox = this.$('.o_video_dialog_options');

        // Show / Hide preview elements
        this.$el.find('.o_video_dialog_preview_text, .media_iframe_video_size').add($optBox).toggleClass('d-none', !query.$video);
        // Toggle validation classes
        this.$el.find('#o_video_form_group')
            .toggleClass('o_has_error', !query.$video).find('.form-control, .custom-select').toggleClass('is-invalid', !query.$video)
            .end()
            .toggleClass('o_has_success', !!query.$video).find('.form-control, .custom-select').toggleClass('is-valid', !!query.$video);

        // Individually show / hide options base on the video provider
        $optBox.find('div.o_' + query.type + '_option').removeClass('d-none');

        // Hide the entire options box if no options are available or if the
        // dialog is opened for a background-video
        $optBox.toggleClass('d-none', this.isForBgVideo || $optBox.find('div:not(.d-none)').length === 0);

        if (query.type === 'yt') {
            // Youtube only: If 'hide controls' is checked, hide 'fullscreen'
            // and 'youtube logo' options too
            this.$('input#o_video_hide_fullscreen, input#o_video_hide_yt_logo').closest('div').toggleClass('d-none', this.$('input#o_video_hide_controls').is(':checked'));
        }

        var $content = query.$video;
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
    _onUpdateVideoOption: function () {
        this._updateVideo();
    },
    /**
     * Called when the video code (URL / Iframe) change is confirmed -> Updates
     * the video preview immediately.
     *
     * @private
     */
    _onVideoCodeChange: function () {
        this._updateVideo();
    },
    /**
     * Called when the video code (URL / Iframe) changes -> Updates the video
     * preview (note: this function is automatically debounced).
     *
     * @private
     */
    _onVideoCodeInput: function () {
        this._updateVideo();
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
