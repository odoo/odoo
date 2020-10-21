odoo.define('wysiwyg.widgets.media', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var fonts = require('wysiwyg.fonts');
var Widget = require('web.Widget');
var concurrency = require('web.concurrency');
var session = require('web.session');

var QWeb = core.qweb;

var _t = core._t;

var MediaWidget = Widget.extend({
    xmlDependencies: ['/web_editor/static/src/xml/wysiwyg.xml'],
    events: {
        'input input.o_we_search': '_onSearchInput',
    },

    /**
     * @constructor
     */
    init: function (parent, media, options) {
        this._super.apply(this, arguments);
        this.media = media;
        this.$media = $(media);
        this._onSearchInput = _.debounce(this._onSearchInput, 500);
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
     * @abstract
     * @param {string} needle
     * @returns {Deferred}
     */
    search: function (needle) {},
    /**
     * @abstract
     * @returns {*}
     */
    save: function () {},

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @abstract
     */
    _clear: function () {},

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
 * Let users choose an image, including uploading a new image in odoo.
 */
var ImageWidget = MediaWidget.extend({
    template: 'wysiwyg.widgets.image',
    events: _.extend({}, MediaWidget.prototype.events || {}, {
        'click .o_upload_media_button': '_onUploadButtonClick',
        'click .o_upload_media_button_no_optimization': '_onUploadButtonNoOptimizationClick',
        'change input[type=file]': '_onImageSelection',
        'click .o_upload_media_url_button': '_onUploadURLButtonClick',
        'input input[name="url"]': '_onURLInputChange',
        'click .existing-attachments [data-src]': '_onImageClick',
        'dblclick .existing-attachments [data-src]': '_onImageDblClick',
        'click .o_existing_attachment_remove': '_onRemoveClick',
        'click .o_load_more': '_onLoadMoreClick',
    }),

    IMAGES_PER_ROW: 6,
    IMAGES_ROWS: 5,

    /**
     * @constructor
     */
    init: function (parent, media, options) {
        this._super.apply(this, arguments);
        this._mutex = new concurrency.Mutex();

        this.imagesRows = this.IMAGES_ROWS;
        this.IMAGES_DISPLAYED_TOTAL = this.IMAGES_PER_ROW * this.imagesRows;

        this.options = options;
        this.context = options.context;
        this.accept = options.accept || (options.document ? '*/*' : 'image/*');

        this.multiImages = options.multiImages;

        // No longer supported, kept for compatibility with custos. TODO: Remove in master.
        this.firstFilters = options.firstFilters || [];
        this.lastFilters = options.lastFilters || [];

        this.images = [];
    },
    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        var self = this;

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

        return this.search('').then(function () {
            if (o.url) {
                self._toggleImage(_.find(self.records, function (record) { return record.url === o.url;}) || o);
            }
            return def;
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    save: function () {
        return this._mutex.exec(this._save.bind(this));
    },
    /**
     * @override
     */
    search: function (needle) {
        var self = this;
        this.$('input.o_we_url_input').val('').trigger('input').trigger('change');
        this.records = [];
        this.needle = needle;
        return this.fetchRecords(this.IMAGES_ROWS * this.IMAGES_PER_ROW, 0).then(function () {
            self._renderImages();
            self._adaptLoadMore();
        });
    },
    /**
     * @override
     */
    fetchRecords: function (number, offset) {
        var self = this;
        return this._rpc({
            model: 'ir.attachment',
            method: 'search_read',
            args: [],
            kwargs: {
                domain: this._getAttachmentsDomain(this.needle),
                fields: ['name', 'datas_fname', 'mimetype', 'checksum', 'url', 'type', 'res_id', 'res_model', 'access_token'],
                order: [{name: 'id', asc: false}],
                context: this.context,
                // Try to fetch first record of next page just to know whether there is a next page.
                limit: number + 1,
                offset: offset,
            }
        }).then(function (records) {
            self.records = self.records.slice();
            Array.prototype.splice.apply(self.records, [offset, records.length].concat(records));
            _.each(self.records, function (record) {
                record.src = record.url || _.str.sprintf('/web/image/%s/%s', record.id, encodeURI(record.name));  // Name is added for SEO purposes
                record.isDocument = !(/gif|jpe|jpg|png/.test(record.mimetype));
            });
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _adaptLoadMore: function () {
        var noMoreImgToLoad = this.IMAGES_DISPLAYED_TOTAL >= this.records.length;
        this.$('.o_load_more').toggleClass('d-none', noMoreImgToLoad);
        this.$('.o_load_done_msg').toggleClass('d-none', !noMoreImgToLoad);
    },
    /**
     * @override
     */
    _clear: function () {
        if (!this.$media.is('img')) {
            return;
        }
        var allImgClasses = /(^|\s+)(img|img-(?!circle|rounded|thumbnail)\S*|o_we_custom_image|o_image)(?=\s|$)/g;
        this.media.className = this.media.className && this.media.className.replace(allImgClasses, ' ');
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

        domain.push('|',
            ['mimetype', '=', false],
            ['mimetype', this.options.document ? 'not in' : 'in', ['image/gif', 'image/jpe', 'image/jpeg', 'image/jpg', 'image/gif', 'image/png']],
            '|',
            ['type', '=like', 'binary'],
            ['url', '!=', false]
        );
        if (needle && needle.length) {
            domain.push('|', ['datas_fname', 'ilike', needle], ['name', 'ilike', needle]);
        }
        domain.push('|', ['datas_fname', '=', false], '!', ['datas_fname', '=like', '%.crop'], '!', ['name', '=like', '%.crop']);
        return domain;
    },
    /**
     * @private
     */
    _highlightSelectedImages: function () {
        var self = this;
        this.$('.o_existing_attachment_cell.o_selected').removeClass("o_selected");
        var $select = this.$('.o_existing_attachment_cell [data-src]').filter(function () {
            var $img = $(this);
            return !!_.find(self.images, function (v) {
                return (v.url === $img.data("src") || ($img.data("url") && v.url === $img.data("url")) || v.id === $img.data("id"));
            });
        });
        $select.closest('.o_existing_attachment_cell').addClass("o_selected");
        return $select;
    },
    /**
     * @private
     */
    _loadMoreImages: function (forceSearch) {
        var self = this;
        return this.fetchRecords(2 * this.IMAGES_PER_ROW, this.imagesRows * this.IMAGES_PER_ROW).then(function () {
            self.imagesRows += 2;
            self.IMAGES_DISPLAYED_TOTAL = self.imagesRows * self.IMAGES_PER_ROW;
            if (!forceSearch) {
                self._renderImages();
                self._adaptLoadMore();
            } else {
                self.search(self.$('.o_we_search').val() || '');
            }
        });
    },
    /**
     * @private
     */
    _renderImages: function (withEffect) {
        var self = this;
        var rows = _(this.records).chain()
            .slice(0, this.IMAGES_DISPLAYED_TOTAL)
            .groupBy(function (a, index) { return Math.floor(index / self.IMAGES_PER_ROW); })
            .values()
            .value();

        this.$('.form-text').empty();

       // Render menu & content
        this.$('.existing-attachments').replaceWith(
            QWeb.render('wysiwyg.widgets.files.existing.content', {
                rows: rows,
                isDocument: this.options.document,
                withEffect: withEffect,
            })
        );

        var $divs = this.$('.o_image');
        var imageDefs = _.map($divs, function (el) {
            var $div = $(el);
            if (/gif|jpe|jpg|png/.test($div.data('mimetype'))) {
                var $img = $('<img/>', {
                    class: 'img-fluid',
                    src: $div.data('url') || $div.data('src'),
                });
                var prom = new Promise(function (resolve, reject) {
                    $img[0].onload = resolve();
                    $div.addClass('o_webimage').append($img);
                });
                return prom;
            }
        });
        if (withEffect) {
            Promise.all(imageDefs).then(function () {
                _.delay(function () {
                    $divs.removeClass('o_image_loading');
                }, 400);
            });
        }
        this._highlightSelectedImages();
    },
    /**
     * @private
     */
    _save: function () {
        var self = this;
        if (this.multiImages) {
            return this.images;
        }

        var img = this.images[0];
        if (!img) {
            return this.media;
        }

        var prom;
        if (!img.access_token) {
            prom = this._rpc({
                model: 'ir.attachment',
                method: 'generate_access_token',
                args: [[img.id]]
            }).then(function (access_token) {
                img.access_token = access_token[0];
            });
        }

        return Promise.resolve(prom).then(function () {
            if (!img.isDocument) {
                if (img.access_token && self.options.res_model !== 'ir.ui.view') {
                    img.src += _.str.sprintf('?access_token=%s', img.access_token);
                }
                if (!self.$media.is('img')) {
                    // Note: by default the images receive the bootstrap opt-in
                    // img-fluid class. We cannot make them all responsive
                    // by design because of libraries and client databases img.
                    self.$media = $('<img/>', {class: 'img-fluid o_we_custom_image'});
                    self.media = self.$media[0];
                }
                self.$media.attr('src', img.src);

            } else {
                if (!self.$media.is('a')) {
                    $('.note-control-selection').hide();
                    self.$media = $('<a/>');
                    self.media = self.$media[0];
                }
                var href = '/web/content/' + img.id + '?';
                if (img.access_token && self.options.res_model !== 'ir.ui.view') {
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

            if (self.options.onUpload) {
                // We consider that when selecting an image it is as if we upload it in the html content.
                self.options.onUpload([img]);
            }

            // Remove crop related attributes
            if (self.$media.attr('data-aspect-ratio')) {
                var attrs = ['aspect-ratio', 'x', 'y', 'width', 'height', 'rotate', 'scale-x', 'scale-y'];
                Object.keys(self.$media.data()).forEach(function (key) {
                    if (_.str.startsWith(key, 'crop:')) {
                        attrs.push(key);
                    }
                });
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
     * @private
     */
    _toggleImage: function (attachment, clearSearch, forceSelect) {
        if (this.multiImages) {
            var img = _.select(this.images, function (v) { return v.id === attachment.id; });
            if (img.length) {
                if (!forceSelect) {
                    this.images.splice(this.images.indexOf(img[0]),1);
                }
            } else {
                this.images.push(attachment);
            }
        } else {
            this.images = [attachment];
        }
        this._highlightSelectedImages();

        if (clearSearch) {
            this.search('');
        }
    },
    /**
     * @private
     */
    _uploadFile: function () {
        return this._mutex.exec(this._uploadImageIframe.bind(this));
    },
    /**
     * @returns {Promise}
     */
    _uploadImageIframe: function () {
        var self = this;
        return new Promise(function (resolve) {

            /**
             * @todo file upload cannot be handled with _rpc smoothly. This uses the
             * form posting in iframe trick to handle the upload.
             */
            var $iframe = self.$('iframe');
            $iframe.on('load', function () {
                var iWindow = $iframe[0].contentWindow;

                var attachments = iWindow.attachments || [];
                var error = iWindow.error;

                self.$('.well > span').remove();
                self.$('.well > div').show();
                _.each(attachments, function (record) {
                    record.src = record.url || _.str.sprintf('/web/image/%s/%s', record.id, encodeURI(record.name)); // Name is added for SEO purposes
                    record.isDocument = !(/gif|jpe|jpg|png/.test(record.mimetype));
                });
                if (error || !attachments.length) {
                    _processFile(null, error || !attachments.length);
                }
                self.images = attachments;
                for (var i = 0 ; i < attachments.length ; i++) {
                    _processFile(attachments[i], error);
                }

                if (self.options.onUpload) {
                    self.options.onUpload(attachments);
                }

                resolve();

                function _processFile(attachment, error) {
                    var $button = self.$('.o_upload_image_button');
                    if (!error) {
                        $button.addClass('btn-success');
                        self._toggleImage(attachment, true);
                    } else {
                        $button.addClass('btn-danger');
                        self.$el.addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
                        self.$el.find('.form-text').text(error);
                    }

                    if (!self.multiImages) {
                        self.trigger_up('save_request');
                    }
                }
            });
            self.$el.submit();

            self.$('.o_file_input').val('');
        });
    },


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onImageClick: function (ev, force_select) {
        var $img = $(ev.currentTarget);
        var attachment = _.find(this.records, function (record) {
            return record.id === $img.data('id');
        });
        this._toggleImage(attachment, false, force_select);
    },
    /**
     * @private
     */
    _onImageDblClick: function (ev) {
        this._onImageClick(ev, true);
        this.trigger_up('save_request');
    },
    /**
     * @private
     */
    _onImageSelection: function () {
        var $form = this.$('form');
        this.$el.addClass('nosave');
        $form.removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');
        $form.find('.form-text').empty();
        this.$('.o_upload_media_button').removeClass('btn-danger btn-success');
        this._uploadFile();
    },
    /**
     * @private
     */
    _onRemoveClick: function (ev) {
        var self = this;
        Dialog.confirm(this, _t("Are you sure you want to delete this file ?"), {
            confirm_callback: function () {
                var $helpBlock = self.$('.form-text').empty();
                var $a = $(ev.currentTarget);
                var id = parseInt($a.data('id'), 10);
                var attachment = _.findWhere(self.records, {id: id});
                 return self._rpc({
                    route: '/web_editor/attachment/remove',
                    params: {
                        ids: [id],
                    },
                }).then(function (prevented) {
                    if (_.isEmpty(prevented)) {
                        self.records = _.without(self.records, attachment);
                        self._renderImages();
                        return;
                    }
                    $helpBlock.replaceWith(QWeb.render('wysiwyg.widgets.image.existing.error', {
                        views: prevented[id],
                    }));
                });
            }
        });
    },
    /**
     * @private
     */
    _onURLInputChange: function (ev) {
        var $input = $(ev.currentTarget);
        var $button = this.$('.o_upload_media_url_button');
        var $success = this.$('.o_we_url_success');
        var $warning = this.$('.o_we_url_warning');
        var $error = this.$('.o_we_url_error');

        var inputValue = $input.val();
        var emptyValue = (inputValue === '');

        var isURL = /^.+\..+$/.test(inputValue); // TODO improve
        var isImage = _.any(['.gif', '.jpe', '.jpg', '.png'], function (format) {
            return inputValue.endsWith(format);
        });

        $button.toggleClass('btn-secondary', emptyValue).toggleClass('btn-primary', !emptyValue)
               .prop('disabled', !isURL);
        if (!this.options.document) {
            $button.text((isURL && !isImage) ? _t("Add as document") : _t("Add image"));
        }
        $success.toggleClass('d-none', !isURL);
        $warning.toggleClass('d-none', !isURL || this.options.document || isImage);
        $error.toggleClass('d-none', emptyValue || isURL);
    },
    /**
     * @private
     */
    _onUploadButtonClick: function () {
        this.$('input[type=file]').click();
    },
    /**
     * @private
     */
    _onUploadButtonNoOptimizationClick: function () {
        this.$('input[name="disable_optimization"]').val('1');
        this.$('.o_upload_media_button').click();
    },
    /**
     * @private
     */
    _onUploadURLButtonClick: function () {
        this._uploadFile();
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
        this.imagesRows = this.IMAGES_ROWS;
        this.IMAGES_DISPLAYED_TOTAL = this.IMAGES_PER_ROW * this.imagesRows;
        this._super.apply(this, arguments);
    },
});

/**
 * Let users choose a font awesome icon, support all font awesome loaded in the
 * css files.
 */
var IconWidget = MediaWidget.extend({
    template: 'wysiwyg.widgets.font-icons',
    events: _.extend({}, MediaWidget.prototype.events || {}, {
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
        var oldClasses = this.media ? _.toArray(this.media.classList) : [];
        var finalClasses = _.union(oldClasses, [iconFont.base, iconFont.font]);
        if (!this.$media.is('span, i')) {
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
        return this.media;
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
            QWeb.render('wysiwyg.widgets.font-icons.icons', {iconsParser: iconsParser})
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
        var allFaClasses = /(^|\s)(fa|fa-\S*)(?=\s|$)/g;
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
        this.$icons.removeClass('o_selected');
        this.$icons.filter(function (i, el) {
            return _.contains($(el).data('alias').split(','), self.selectedIcon);
        }).addClass('o_selected');
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
    init: function (parent, media) {
        this._super.apply(this, arguments);
        this._onVideoCodeInput = _.debounce(this._onVideoCodeInput, 1000);
    },
    /**
     * @override
     */
    start: function () {
        this.$content = this.$('.o_video_dialog_iframe');

        if (this.media) {
            var $media = $(this.media);
            var src = $media.data('oe-expression') || $media.data('src') || '';
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
        if (this.$('.o_video_dialog_iframe').is('iframe')) {
            this.$media = $(
                '<div class="media_iframe_video" data-oe-expression="' + this.$content.attr('src') + '">' +
                    '<div class="css_editable_mode_display">&nbsp;</div>' +
                    '<div class="media_iframe_video_size" contenteditable="false">&nbsp;</div>' +
                    '<iframe src="' + this.$content.attr('src') + '" frameborder="0" contenteditable="false" allowfullscreen="allowfullscreen"></iframe>' +
                '</div>'
            );
            this.media = this.$media[0];
        }
        return this.media;
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
        this.media.className = this.media.className && this.media.className.replace(allVideoClasses, ' ');
        this.media.innerHTML = '';
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

        var dmRegExp = /.+dailymotion.com\/(video|hub|embed)\/([^_?]+)[^#]*(#video=([^_&]+))?/;
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
            autoplay: this.$('input#o_video_autoplay').is(':checked'),
            hide_controls: this.$('input#o_video_hide_controls').is(':checked'),
            loop: this.$('input#o_video_loop').is(':checked'),
            hide_fullscreen: this.$('input#o_video_hide_fullscreen').is(':checked'),
            hide_yt_logo: this.$('input#o_video_hide_yt_logo').is(':checked'),
            hide_dm_logo: this.$('input#o_video_hide_dm_logo').is(':checked'),
            hide_dm_share: this.$('input#o_video_hide_dm_share').is(':checked'),
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

        // Hide the entire options box if no options are available
        $optBox.toggleClass('d-none', $optBox.find('div:not(.d-none)').length === 0);

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
    ImageWidget: ImageWidget,
    IconWidget: IconWidget,
    VideoWidget: VideoWidget,
};
});
