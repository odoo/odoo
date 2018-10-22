odoo.define('web_editor.widget', function (require) {
'use strict';

var ajax = require('web.ajax');
var base = require('web_editor.base');
var core = require('web.core');
var Dialog = require('web.Dialog');
var Widget = require('web.Widget');
var weContext = require("web_editor.context");

var QWeb = core.qweb;
var range = $.summernote.core.range;
var dom = $.summernote.core.dom;

var _t = core._t;

/**
 * @todo we should either get rid of this or move it somewhere else
 */
function simulateMouseEvent(el, type) {
    var evt = document.createEvent("MouseEvents");
    evt.initMouseEvent(type, true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, el);
    el.dispatchEvent(evt);
}

/**
 * Extend Dialog class to handle save/cancel of edition components.
 */
Dialog = Dialog.extend({
    /**
     * @constructor
     */
    init: function (parent, options) {
        options = options || {};
        this._super(parent, _.extend({}, {
            buttons: [
                {text: options.save_text || _t("Save"), classes: 'btn-primary', click: this.save},
                {text: _t("Discard"), close: true}
            ]
        }, options));

        this.destroyAction = 'cancel';

        var self = this;
        this.opened().then(function () {
            self.$('input:first').focus();
        });
        this.on('closed', this, function () {
            this.trigger(this.destroyAction, this.final_data || null);
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Called when the dialog is saved. Set the destroy action type to "save"
     * and should set the final_data variable correctly before closing.
     */
    save: function () {
        this.destroyAction = "save";
        this.close();
    },
});

/**
 * Let users change the alt & title of a media.
 */
var AltDialog = Dialog.extend({
    template: 'web_editor.dialog.alt',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/web_editor/static/src/xml/editor.xml']
    ),

    /**
     * @constructor
     */
    init: function (parent, options, $editable, media) {
        this._super(parent, _.extend({}, {
            title: _t("Change media description and tooltip")
        }, options));
        this.$editable = $editable;
        this.media = media;
        this.alt = ($(this.media).attr('alt') || "").replace(/&quot;/g, '"');
        this.tag_title = ($(this.media).attr('title') || "").replace(/&quot;/g, '"');
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    save: function () {
        var self = this;
        range.createFromNode(this.media).select();
        this.$editable.data('NoteHistory').recordUndo();
        var alt = this.$('#alt').val();
        var title = this.$('#title').val();
        $(this.media).attr('alt', alt ? alt.replace(/"/g, "&quot;") : null).attr('title', title ? title.replace(/"/g, "&quot;") : null);
        _.defer(function () {
            simulateMouseEvent(self.media, 'mouseup');
        });
        return this._super.apply(this, arguments);
    },
});

var MediaWidget = Widget.extend({
    xmlDependencies: ['/web_editor/static/src/xml/editor.xml'],

    /**
     * @constructor
     */
    init: function (parent, media, options) {
        this._super.apply(this, arguments);
        this.media = media;
        this.$media = $(media);
        this.page = 0;
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
     * @todo comment
     */
    getControlPanelConfig: function () {
        return {
            searchEnabled: true,
            pagerEnabled: true,
            pagerLeftEnabled: false,
            pagerRightEnabled: false,
        };
    },
    /**
     * @override
     */
    goToPage: function (page) {
        this.page = page;
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
    /**
     * @private
     */
    _replaceMedia: function ($media) {
        this.$media.replaceWith($media);
        this.$media = $media;
        this.media = $media[0];
    },
});

/**
 * Let users choose an image, including uploading a new image in odoo.
 */
var ImageWidget = MediaWidget.extend({
    template: 'web_editor.dialog.image',
    events: {
        'click .o_upload_image_button': '_onUploadButtonClick',
        'click .o_upload_image_button_no_optimization': '_onUploadButtonNoOptimizationClick',
        'change input[type=file]': '_onImageSelection',
        'click .o_upload_image_url_button': '_onUploadURLButtonClick',
        'input input.url': "_onSearchInput",
        'click .existing-attachments [data-src]': '_onImageClick',
        'dblclick .existing-attachments [data-src]': '_onImageDblClick',
        'click .o_existing_attachment_remove': '_onRemoveClick',
    },

    IMAGES_PER_ROW: 6,
    IMAGES_ROWS: 2,

    /**
     * @constructor
     */
    init: function (parent, media, options) {
        this._super.apply(this, arguments);

        this.IMAGES_PER_PAGE = this.IMAGES_PER_ROW * this.IMAGES_ROWS;

        this.options = options;
        this.accept = options.accept || (options.document ? '*/*' : 'image/*');
        if (options.domain) {
            this.domain = typeof options.domain === 'function' ? options.domain() : options.domain;
        } else if (options.res_id) {
            this.domain = ['|',
                '&', ['res_model', '=', options.res_model], ['res_id', '=', options.res_id],
                ['res_model', '=', 'ir.ui.view']];
        } else {
            this.domain = [['res_model', '=', 'ir.ui.view']];
        }

        this.multiImages = options.multiImages;

        this.firstFilters = options.firstFilters || [];
        this.lastFilters = options.lastFilters || [];

        this.images = [];
    },
    /**
     * @override
     */
    willStart: function () {
        return $.when(
            this._super.apply(this, arguments),
            this.search('', true)
        );
    },
    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        var self = this;

        this._renderImages();

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
            self._toggleImage(_.find(self.records, function (record) { return record.url === o.url;}) || o, true);
        }

        return def;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getControlPanelConfig: function () {
        return _.extend(this._super.apply(this, arguments), {
            pagerLeftEnabled: this.page > 0,
            pagerRightEnabled: (this.page + 1) * this.IMAGES_PER_PAGE < this.records.length,
        });
    },
    /**
     * @override
     */
    goToPage: function (page) {
        this._super.apply(this, arguments);
        this._renderImages();
    },
    /**
     * @override
     */
    save: function () {
        var self = this;
        if (this.multiImages) {
            return this.images;
        }

        var img = this.images[0];
        if (!img) {
            return this.media;
        }

        var def = $.when();
        if (!img.access_token) {
            def = this._rpc({
                model: 'ir.attachment',
                method: 'generate_access_token',
                args: [[img.id]]
            }).then(function (access_token) {
                img.access_token = access_token[0];
            });
        }

        return def.then(function () {
            if (!img.isDocument) {
                if (img.access_token && self.options.res_model !== 'ir.ui.view') {
                    img.src += _.str.sprintf('?access_token=%s', img.access_token);
                }
                if (!self.$media.is('img')) {
                    // Note: by default the images receive the bootstrap opt-in
                    // img-fluid class. We cannot make them all responsive
                    // by design because of libraries and client databases img.
                    self._replaceMedia($('<img/>', {class: 'img-fluid o_we_custom_image'}));
                }
                self.$media.attr('src', img.src);

            } else {
                if (!self.$media.is('a')) {
                    $('.note-control-selection').hide();
                    self._replaceMedia($('<a/>'));
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
                _.each(attrs, function (attr) {
                    self.$media.removeData(attr);
                    self.$media.removeAttr('data-' + attr);
                });
            }
            return self.media;
        });
    },
    /**
     * @override
     */
    search: function (needle, noRender) {
        var self = this;
        if (!noRender) {
            this.$('input.url').val('').trigger('input').trigger('change');
        }
        // TODO: Expand this for adding SVG
        var domain = this.domain.concat(['|', ['mimetype', '=', false], ['mimetype', this.options.document ? 'not in' : 'in', ['image/gif', 'image/jpe', 'image/jpeg', 'image/jpg', 'image/gif', 'image/png']]]);
        if (needle && needle.length) {
            domain.push('|', ['datas_fname', 'ilike', needle], ['name', 'ilike', needle]);
        }
        domain.push('|', ['datas_fname', '=', false], '!', ['datas_fname', '=like', '%.crop'], '!', ['name', '=like', '%.crop']);
        return this._rpc({
            model: 'ir.attachment',
            method: 'search_read',
            args: [],
            kwargs: {
                domain: domain,
                fields: ['name', 'datas_fname', 'mimetype', 'checksum', 'url', 'type', 'res_id', 'res_model', 'access_token'],
                order: [{name: 'id', asc: false}],
                context: weContext.get(),
            },
        }).then(function (records) {
            self.records = _.chain(records)
                .filter(function (r) {
                    return (r.type === "binary" || r.url && r.url.length > 0);
                })
                .uniq(function (r) {
                    return (r.url || r.id);
                })
                .sortBy(function (r) {
                    if (_.any(self.firstFilters, function (filter) {
                        var regex = new RegExp(filter, 'i');
                        return r.name.match(regex) || r.datas_fname && r.datas_fname.match(regex);
                    })) {
                        return -1;
                    }
                    if (_.any(self.lastFilters, function (filter) {
                        var regex = new RegExp(filter, 'i');
                        return r.name.match(regex) || r.datas_fname && r.datas_fname.match(regex);
                    })) {
                        return 1;
                    }
                    return 0;
                })
                .value();

            _.each(self.records, function (record) {
                record.src = record.url || _.str.sprintf('/web/image/%s/%s', record.id, encodeURI(record.name));  // Name is added for SEO purposes
                record.isDocument = !(/gif|jpe|jpg|png/.test(record.mimetype));
            });
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
        this.media.className = this.media.className.replace(/(^|\s+)((img(\s|$)|img-(?!circle|rounded|thumbnail))[^\s]*)/g, ' ');
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
    _renderImages: function () {
        var self = this;
        var startIndex = this.page * this.IMAGES_PER_PAGE;
        var rows = _(this.records).chain()
            .slice(startIndex, startIndex + this.IMAGES_PER_PAGE)
            .groupBy(function (a, index) { return Math.floor(index / self.IMAGES_PER_ROW); })
            .values()
            .value();

        this.$('.form-text').empty();

        this.$('.existing-attachments').replaceWith(QWeb.render('web_editor.dialog.image.existing.content', {rows: rows}));

        var $divs = this.$('.o_image');
        var imageDefs = _.map($divs, function (el) {
            var $div = $(el);
            if (/gif|jpe|jpg|png/.test($div.data('mimetype'))) {
                var $img = $('<img/>', {
                    class: 'img-fluid',
                    src: $div.data('url') || $div.data('src'),
                });
                var def = $.Deferred();
                $img[0].onload = def.resolve.bind(def);
                $div.addClass('o_webimage').append($img);
                return def;
            }
        });
        $.when.apply($, imageDefs).then(function () {
            _.delay(function () {
                $divs.removeClass('o_image_loading');
            }, 400);
        });
        this._highlightSelectedImages();
    },
    /**
     * @private
     */
    _toggleImage: function (attachment, clearSearch, force_select) {
        if (this.multiImages) {
            var img = _.select(this.images, function (v) { return v.id === attachment.id; });
            if (img.length) {
                if (!force_select) {
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
    _uploadImage: function () {
        var self = this;

        /**
         * @todo file upload cannot be handled with _rpc smoothly. This uses the
         * form posting in iframe trick to handle the upload.
         */
        var $iframe = this.$('iframe');
        $iframe.on('load', function () {
            var iWindow = $iframe[0].contentWindow;
            var attachments = iWindow.attachments;
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
        this.$el.submit();
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
        this.$('.o_upload_image_button').removeClass('btn-danger btn-success');
        this._uploadImage();
    },
    /**
     * @private
     */
    _onRemoveClick: function (ev) {
        var self = this;
        var $helpBlock = this.$('.form-text').empty();
        var $a = $(ev.currentTarget);
        var id = parseInt($a.data('id'), 10);
        var attachment = _.findWhere(this.records, {id: id});

        return this._rpc({
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
            $helpBlock.replaceWith(QWeb.render('web_editor.dialog.image.existing.error', {
                views: prevented[id]
            }));
        });
    },
    /**
     * @private
     */
    _onSearchInput: function (ev) {
        var $input = $(ev.currentTarget);
        var $button = $input.next('.input-group-append').children();
        var emptyValue = ($input.val() === '');
        $button.toggleClass('btn-secondary', emptyValue).toggleClass('btn-primary', !emptyValue)
               .prop('disabled', emptyValue);
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
        this.$('.o_upload_image_button').click();
    },
    /**
     * @private
     */
    _onUploadURLButtonClick: function () {
        this._uploadImage();
    },
});

/**
 * Let users choose a font awesome icon, support all font awesome loaded in the
 * css files.
 */
var IconWidget = MediaWidget.extend({
    template: 'web_editor.dialog.font-icons',
    events : {
        'click .font-icons-icon': '_onIconClick',
        'dblclick .font-icons-icon': '_onIconDblClick',
    },

    /**
     * @constructor
     */
    init: function (parent, media) {
        this._super.apply(this, arguments);

        base.computeFonts();
        this.iconsParser = base.fontIcons;
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
        for (var i = 0 ; i < classes.length ; i++) {
            var cls = classes[i];
            if (_.contains(this.alias, cls)) {
                this.selectedIcon = cls;
                this._highlightSelectedIcon();
            }
        }
        this.nonIconClasses = _.without(classes, this.selectedIcon);

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getControlPanelConfig: function () {
        return _.extend(this._super.apply(this, arguments), {
            pagerEnabled: false,
        });
    },
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
            this._replaceMedia($span);
            style = style.replace(/\s*width:[^;]+/, '');
        }
        this.$media.attr({
            class: _.compact(finalClasses).join(' '),
            style: style,
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
            QWeb.render('web_editor.dialog.font-icons.icons', {iconsParser: iconsParser})
        );
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _clear: function () {
        this.media.className = this.media.className.replace(/(^|\s)(fa(\s|$)|fa-[^\s]*)/g, ' ');
    },
    /**
     * @private
     */
    _getFont: function (classNames) {
        if (!(classNames instanceof Array)) {
            classNames = (classNames||"").split(/\s+/);
        }
        var fontIcon, cssData;
        for (var k=0; k<this.iconsParser.length; k++) {
            fontIcon = this.iconsParser[k];
            for (var s=0; s<fontIcon.cssData.length; s++) {
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
    template: 'web_editor.dialog.video',
    events : {
        'change .o_video_dialog_options input': '_onUpdateVideoOption',
        'input textarea#o_video_text': '_onVideoCodeInput',
        'change textarea#o_video_text': '_onVideoCodeChange',
    },

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

        var $media = $(this.media);
        if ($media.hasClass('media_iframe_video')) {
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
    getControlPanelConfig: function () {
        return _.extend(this._super.apply(this, arguments), {
            searchEnabled: false,
            pagerEnabled: false,
        });
    },
    /**
     * @override
     */
    save: function () {
        this._updateVideo();
        if (this.$('.o_video_dialog_iframe').is('iframe')) {
            this._replaceMedia($(
                '<div class="media_iframe_video" data-oe-expression="' + this.$content.attr('src') + '">'+
                    '<div class="css_editable_mode_display">&nbsp;</div>'+
                    '<div class="media_iframe_video_size" contenteditable="false">&nbsp;</div>'+
                    '<iframe src="' + this.$content.attr('src') + '" frameborder="0" contenteditable="false"></iframe>'+
                '</div>'
            ));
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
        this.media.className = this.media.className.replace(/(^|\s)media_iframe_video(\s|$)/g, ' ');
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
        var ytRegExp = /^(?:(?:https?:)?\/\/)?(?:www\.)?(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))((\w|-){11})(?:\S+)?$/;
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

        var autoplay = options.autoplay ? '?autoplay=1' : '?autoplay=0';

        if (ytMatch && ytMatch[1].length === 11) {
            $video.attr('src', '//www.youtube.com/embed/' + ytMatch[1] + autoplay);
        } else if (insMatch && insMatch[2].length) {
            $video.attr('src', '//www.instagram.com/p/' + insMatch[2] + '/embed/');
            videoType = 'ins';
        } else if (vinMatch && vinMatch[0].length) {
            $video.attr('src', vinMatch[0] + '/embed/simple');
            videoType = 'vin';
        } else if (vimMatch && vimMatch[3].length) {
            $video.attr('src', '//player.vimeo.com/video/' + vimMatch[3] + autoplay);
            videoType = 'vim';
        } else if (dmMatch && dmMatch[2].length) {
            var just_id = dmMatch[2].replace('video/','');
            $video.attr('src', '//www.dailymotion.com/embed/video/' + just_id + autoplay);
            videoType = 'dm';
        } else if (ykuMatch && ykuMatch[3].length) {
            var yku_id = ykuMatch[3].indexOf('.html?') >= 0 ? ykuMatch[3].substring(0, ykuMatch[3].indexOf('.html?')) : ykuMatch[3];
            $video.attr('src', '//player.youku.com/embed/' + yku_id);
            videoType = 'yku';
        } else {
            return {errorCode: 1};
        }

        if (ytMatch) {
            $video.attr('src', $video.attr('src') + '&rel=0');
        }
        if (options.loop && (ytMatch || vimMatch)) {
            $video.attr('src', $video.attr('src') + '&loop=1');
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
        this.$('.o_video_dialog_options li').addClass('d-none');

        // Check video code
        var $textarea = this.$('textarea#o_video_text');
        var code = $textarea.val().trim();
        if (!code) {
            return;
        }

        // Detect if we have an embed code rather than an URL
        var embedMatch = code.match(/(src|href)=["']?([^"']+)?/);
        if (embedMatch && embedMatch[2].length > 0 && embedMatch[2].indexOf('instagram')){
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

        var $opt_box = this.$('.o_video_dialog_options');

        // Show / Hide preview elements
        this.$el.find('.o_video_dialog_preview_text, .media_iframe_video_size').add($opt_box).toggleClass('d-none', !query.$video);
        // Toggle validation classes
        this.$el.find('#o_video_form_group')
            .toggleClass('o_has_error', !query.$video).find('.form-control, .custom-select').toggleClass('is-invalid', !query.$video)
            .end()
            .toggleClass('o_has_success', !!query.$video).find('.form-control, .custom-select').toggleClass('is-valid', !!query.$video);

        // Individually show / hide options base on the video provider
        $opt_box.find('li.o_' + query.type + '_option').removeClass('d-none');

        // Hide the entire options box if no options are available
        $opt_box.toggleClass('d-none', $opt_box.find('li:not(.d-none)').length === 0);

        if (query.type === 'yt') {
            // Youtube only: If 'hide controls' is checked, hide 'fullscreen'
            // and 'youtube logo' options too
            this.$('input#o_video_hide_fullscreen, input#o_video_hide_yt_logo').closest('li').toggleClass('d-none', this.$('input#o_video_hide_controls').is(':checked'));
        }

        var $content = query.$video;
        if (!$content) {
            switch (query.errorCode) {
                case 0:
                    $content = $('<div/>', {
                        class: 'alert alert-danger o_video_dialog_iframe',
                        text: _t("The provided url is not valid"),
                    });
                    break;
                case 1:
                    $content = $('<div/>', {
                        class: 'alert alert-warning o_video_dialog_iframe',
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

/**
 * MediaDialog widget. Lets users change a media, including uploading a
 * new image, font awsome or video and can change a media into an other
 * media.
 */
var MediaDialog = Dialog.extend({
    template: 'web_editor.dialog.media',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/web_editor/static/src/xml/editor.xml']
    ),
    events : _.extend({}, Dialog.prototype.events, {
        'input input#icon-search': '_onSearchInput',
        'shown.bs.tab a[data-toggle="tab"]': '_onTabChange',
        'click .previous:not(.disabled), .next:not(.disabled)': '_onPagerClick',
    }),
    custom_events: _.extend({}, Dialog.prototype.custom_events || {}, {
        save_request: '_onSaveRequest',
        update_control_panel: '_updateControlPanel',
    }),

    /**
     * @constructor
     */
    init: function (parent, options, $editable, media) {
        var self = this;
        this._super(parent, _.extend({}, {
            title: _t("Select a Media"),
        }, options));

        if ($editable) {
            this.$editable = $editable;
            this.rte = this.$editable.rte || this.$editable.data('rte');
        }

        this.media = media;
        this.$media = $(media);
        this.range = range.create();

        this.multiImages = options.multiImages;
        var onlyImages = options.onlyImages || this.multiImages || (this.media && (this.$media.parent().data('oeField') === 'image' || this.$media.parent().data('oeType') === 'image'));
        this.noImages = options.noImages;
        this.noDocuments = onlyImages || options.noDocuments;
        this.noIcons = onlyImages || options.noIcons;
        this.noVideos = onlyImages || options.noVideos;

        if (!this.noImages) {
            this.imageDialog = new ImageWidget(this, this.media, options);
        }
        if (!this.noDocuments) {
            this.documentDialog = new ImageWidget(this, this.media, _.extend({}, options, {document: true}));
        }
        if (!this.noIcons) {
            this.iconDialog = new IconWidget(this, this.media, options);
        }
        if (!this.noVideos) {
            this.videoDialog = new VideoWidget(this, this.media, options);
        }

        this.opened(function () {
            var tabToShow = 'icon';
            if (!self.media || self.$media.is('img')) {
                tabToShow = 'image';
            } else if (self.$media.is('a.o_image')) {
                tabToShow = 'document';
            } else if (self.$media.attr('class').match(/(^|\s)media_iframe_video($|\s)/)) {
                tabToShow = 'video';
            } else if (self.$media.parent().attr('class').match(/(^|\s)media_iframe_video($|\s)/)) {
                self.$media = self.$media.parent();
                self.media = self.$media[0];
                tabToShow = 'video';
            }
            self.$('[href="#editor-media-' + tabToShow + '"]').tab('show');
        });

        this._onSearchInput = _.debounce(this._onSearchInput, 250);
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        var defs = [this._super.apply(this, arguments)];
        this.$modal.addClass('note-image-dialog');
        this.$modal.find('.modal-dialog').addClass('o_select_media_dialog');

        if (this.imageDialog) {
            defs.push(this.imageDialog.appendTo(this.$("#editor-media-image")));
        }
        if (this.documentDialog) {
            defs.push(this.documentDialog.appendTo(this.$("#editor-media-document")));
        }
        if (this.iconDialog) {
            defs.push(this.iconDialog.appendTo(this.$("#editor-media-icon")));
        }
        if (this.videoDialog) {
            defs.push(this.videoDialog.appendTo(this.$("#editor-media-video")));
        }

        return $.when.apply($, defs).then(function () {
            self._setActive(self.imageDialog);
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    save: function () {
        var self = this;
        var args = arguments;
        var _super = this._super;
        if (this.multiImages) {
            // In the case of multi images selection we suppose this was not to
            // replace an old media, so we only retrieve the images and save.
            return $.when(this.active.save()).then(function (data) {
                self.final_data = data;
                return _super.apply(self, args);
            });
        }

        if (this.rte) {
            this.range.select();
            this.rte.historyRecordUndo(this.media);
        }

        if (this.media) {
            this.$media.html('');
            _.each(['imageDialog', 'documentDialog', 'iconDialog', 'videoDialog'], function (v) {
                // Note: hack since imageDialog is the same type as the documentDialog
                if (self[v] && self.active._clear.toString() !== self[v]._clear.toString()) {
                    self[v].clear();
                }
            });
        }

        return $.when(this.active.save()).then(function (media) {
            if (!self.media && media) {
                self.range.insertNode(media, true);
            }
            self.media = media;
            self.$media = $(media);

            self.final_data = self.media;
            $(self.final_data).trigger('input').trigger('save');
            $(document.body).trigger("media-saved", self.final_data); // TODO get rid of this

            // Update editor bar after image edition (in case the image change to icon or other)
            _.defer(function () {
                if (!self.media || !self.media.parentNode) {
                    return;
                }
                range.createFromNode(self.media).select();
                simulateMouseEvent(self.media, 'mousedown');
                simulateMouseEvent(self.media, 'mouseup');
            });
            return _super.apply(self, args);
        });
    },

    //--------------------------------------------------------------------------
    //
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _setActive: function (widget) {
        this.active = widget;
        this.active.goToPage(0);
        this._updateControlPanel();
    },
    /**
     * @private
     */
    _updateControlPanel: function () {
        var cpConfig = this.active.getControlPanelConfig();
        this.$('li.search').toggleClass('d-none', !cpConfig.searchEnabled);
        this.$('.previous, .next').toggleClass('d-none', !cpConfig.pagerEnabled);
        this.$('.previous').toggleClass("disabled", !cpConfig.pagerLeftEnabled);
        this.$('.next').toggleClass("disabled", !cpConfig.pagerRightEnabled);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onPagerClick: function (ev) {
        this.active.goToPage(this.active.page + ($(ev.currentTarget).hasClass('previous') ? -1 : 1));
        this._updateControlPanel();
    },
    /**
     * @private
     */
    _onSaveRequest: function (ev) {
        ev.stopPropagation();
        this.save();
    },
    /**
     * @private
     */
    _onSearchInput: function (ev) {
        var self = this;
        this.active.goToPage(0);
        this.active.search($(ev.currentTarget).val() || '').then(function () {
            self._updateControlPanel();
        });
    },
    /**
     * @private
     */
    _onTabChange: function (ev) {
        var $target = $(ev.target);
        if ($target.is('[href="#editor-media-image"]')) {
            this._setActive(this.imageDialog);
        } else if ($target.is('[href="#editor-media-document"]')) {
            this._setActive(this.documentDialog);
        } else if ($target.is('[href="#editor-media-icon"]')) {
            this._setActive(this.active = this.iconDialog);
        } else if ($target.is('[href="#editor-media-video"]')) {
            this._setActive(this.active = this.videoDialog);
        }
    },
});

/**
 * Allows to customize link content and style.
 */
var LinkDialog = Dialog.extend({
    template: 'web_editor.dialog.link',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/web_editor/static/src/xml/editor.xml']
    ),
    events: _.extend({}, Dialog.prototype.events || {}, {
        'input': '_onAnyChange',
        'change': '_onAnyChange',
        'input input[name="url"]': '_onURLInput',
    }),

    /**
     * @constructor
     */
    init: function (parent, options, editable, linkInfo) {
        this._super(parent, _.extend({
            title: _t("Link to"),
        }, options || {}));

        this.editable = editable;
        this.data = linkInfo || {};

        this.data.className = "";

        var r = this.data.range;
        this.needLabel = !r || (r.sc === r.ec && r.so === r.eo);

        if (this.data.range) {
            this.data.iniClassName = $(this.data.range.sc).filter("a").attr("class") || "";
            this.data.className = this.data.iniClassName.replace(/(^|\s+)btn(-[a-z0-9_-]*)?/gi, ' ');

            var is_link = this.data.range.isOnAnchor();

            var sc = r.sc;
            var so = r.so;
            var ec = r.ec;
            var eo = r.eo;

            var nodes;
            if (!is_link) {
                if (sc.tagName) {
                    sc = dom.firstChild(so ? sc.childNodes[so] : sc);
                    so = 0;
                } else if (so !== sc.textContent.length) {
                    if (sc === ec) {
                        ec = sc = sc.splitText(so);
                        eo -= so;
                    } else {
                        sc = sc.splitText(so);
                    }
                    so = 0;
                }
                if (ec.tagName) {
                    ec = dom.lastChild(eo ? ec.childNodes[eo-1] : ec);
                    eo = ec.textContent.length;
                } else if (eo !== ec.textContent.length) {
                    ec.splitText(eo);
                }

                nodes = dom.listBetween(sc, ec);

                // browsers can't target a picture or void node
                if (dom.isVoid(sc) || dom.isImg(sc)) {
                    so = dom.listPrev(sc).length-1;
                    sc = sc.parentNode;
                }
                if (dom.isBR(ec)) {
                    eo = dom.listPrev(ec).length-1;
                    ec = ec.parentNode;
                } else if (dom.isVoid(ec) || dom.isImg(sc)) {
                    eo = dom.listPrev(ec).length;
                    ec = ec.parentNode;
                }

                this.data.range = range.create(sc, so, ec, eo);
                this.data.range.select();
            } else {
                nodes = dom.ancestor(sc, dom.isAnchor).childNodes;
            }

            if (dom.isImg(sc) && nodes.indexOf(sc) === -1) {
                nodes.push(sc);
            }
            if (nodes.length > 1 || dom.ancestor(nodes[0], dom.isImg)) {
                var text = "";
                this.data.images = [];
                for (var i=0; i<nodes.length; i++) {
                    if (dom.ancestor(nodes[i], dom.isImg)) {
                        this.data.images.push(dom.ancestor(nodes[i], dom.isImg));
                        text += '[IMG]';
                    } else if (!is_link && nodes[i].nodeType === 1) {
                        // just use text nodes from listBetween
                    } else if (!is_link && i===0) {
                        text += nodes[i].textContent.slice(so, Infinity);
                    } else if (!is_link && i===nodes.length-1) {
                        text += nodes[i].textContent.slice(0, eo);
                    } else {
                        text += nodes[i].textContent;
                    }
                }
                this.data.text = text;
            }
        }

        this.data.text = this.data.text.replace(/[ \t\r\n]+/g, ' ');
    },
    /**
     * @override
     */
    start: function () {
        var self = this;

        this.$('input.link-style').prop('checked', false).first().prop('checked', true);
        if (this.data.iniClassName) {
            _.each(this.$('input.link-style, select.link-style > option'), function (el) {
                var $option = $(el);
                if ($option.val() && self.data.iniClassName.indexOf($option.val()) >= 0) {
                    if ($option.is("input")) {
                        $option.prop("checked", true);
                    } else {
                        $option.parent().val($option.val());
                    }
                }
            });
        }
        if (this.data.url) {
            var match = /mailto:(.+)/.exec(this.data.url);
            this.$('input[name="url"]').val(match ? match[1] : this.data.url);
        }

        // Hide the duplicate color buttons (most of the times, primary = alpha
        // and secondary = beta for example but this may depend on the theme)
        this.opened().then(function () {
            var colors = [];
            _.each(self.$('.o_btn_preview.o_link_dialog_color_item'), function (btn) {
                var $btn = $(btn);
                var color = $btn.css('background-color');
                if (_.contains(colors, color)) {
                    $btn.hide(); // Not remove to be able to edit buttons with those styles
                } else {
                    colors.push(color);
                }
            });
        });

        this._adaptPreview();

        this.$('input:visible:first').focus();

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    save: function () {
        var data = this._getData();
        if (data === null) {
            var $url = this.$('input[name="url"]');
            $url.closest('.form-group').addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
            $url.focus();
            return $.Deferred().reject();
        }
        this.data.text = data.label;
        this.data.url = data.url;
        this.data.className = data.classes.replace(/\s+/gi, ' ').replace(/^\s+|\s+$/gi, '');
        if (data.classes.replace(/(^|[ ])(btn-secondary|btn-success|btn-primary|btn-info|btn-warning|btn-danger)([ ]|$)/gi, ' ')) {
            this.data.style = {'background-color': '', 'color': ''};
        }
        this.data.isNewWindow = data.isNewWindow;
        this.final_data = this.data;
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _adaptPreview: function () {
        var $preview = this.$("#link-preview");
        var data = this._getData();
        if (data === null) {
            return;
        }
        $preview.attr({
            target: data.isNewWindow ? '_blank' : '',
            href: data.url && data.url.length ? data.url : '#',
            class: data.classes.replace(/float-\w+/, '') + ' o_btn_preview',
        }).html((data.label && data.label.length) ? data.label : data.url);
    },
    /**
     * @private
     */
    _getData: function () {
        var $url = this.$('input[name="url"]');
        var url = $url.val();
        var label = this.$('input[name="label"]').val() || url;

        if (label && this.data.images) {
            for (var i = 0 ; i < this.data.images.length ; i++) {
                label = label.replace(/</, "&lt;").replace(/>/, "&gt;").replace(/\[IMG\]/, this.data.images[i].outerHTML);
            }
        }

        if ($url.prop('required') && (!url || !$url[0].checkValidity())) {
            return null;
        }

        var style = this.$('input[name="link_style_color"]:checked').val() || '';
        var shape = this.$('select[name="link_style_shape"]').val() || '';
        var size = this.$('select[name="link_style_size"]').val() || '';
        var shapes = shape.split(',');
        var outline = shapes[0] === 'outline';
        shape = shapes.slice(outline ? 1 : 0).join(' ');
        var classes = (this.data.className || '')
            + (style ? (' btn btn-' + (outline ? 'outline-' : '') + style) : '')
            + (shape ? (' ' + shape) : '')
            + (size ? (' btn-' + size) : '');
        var isNewWindow = this.$('input[name="is_new_window"]').prop('checked');

        if (url.indexOf('@') >= 0 && url.indexOf('mailto:') < 0 && !url.match(/^http[s]?/i)) {
            url = ('mailto:' + url);
        }
        return {
            label: label,
            url: url,
            classes: classes,
            isNewWindow: isNewWindow,
        };
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAnyChange: function () {
        this._adaptPreview();
    },
    /**
     * @private
     */
    _onURLInput: function (ev) {
        $(ev.currentTarget).closest('.form-group').removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');
        var isLink = $(ev.currentTarget).val().indexOf('@') < 0;
        this.$('input[name="is_new_window"]').closest('.form-group').toggleClass('d-none', !isLink);
    },
});

/**
 * CropImageDialog widget. Let users crop an image.
 */
var CropImageDialog = Dialog.extend({
    template: 'web_editor.dialog.crop_image',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/web_editor/static/src/xml/editor.xml']
    ),
    jsLibs: [
        '/web_editor/static/lib/cropper/js/cropper.js',
    ],
    cssLibs: [
        '/web_editor/static/lib/cropper/css/cropper.css',
    ],
    events : _.extend({}, Dialog.prototype.events, {
        'click .o_crop_options [data-event]': '_onCropOptionClick',
    }),

    /**
     * @constructor
     */
    init: function (parent, options, $editable, media) {
        this.media = media;
        this.$media = $(this.media);
        var src = this.$media.attr('src').split('?')[0];
        this.aspectRatioList = [
            [_t("Free"), '0/0', 0],
            ["16:9", '16/9', 16 / 9],
            ["4:3", '4/3', 4 / 3],
            ["1:1", '1/1', 1],
            ["2:3", '2/3', 2 / 3],
        ];
        this.imageData = {
            imageSrc: src,
            originalSrc: this.$media.data('crop:originalSrc') || src, // the original src for cropped DB images will be fetched later
            mimetype: this.$media.data('crop:mimetype') || (_.str.endsWith(src, '.png') ? 'image/png' : 'image/jpeg'), // the mimetype for DB images will be fetched later
            aspectRatio: this.$media.data('aspectRatio') || this.aspectRatioList[0][1],
            isExternalImage: src.substr(0, 5) !== 'data:' && src[0] !== '/' && src.indexOf(window.location.host) < 0,
        };
        this.options = _.extend({
            title: _t("Crop Image"),
            buttons: this.imageData.isExternalImage ? [{
                text: _t("Close"),
                close: true,
            }] : [{
                text: _t("Save"),
                classes: 'btn-primary',
                click: this.save,
            }, {
                text: _t("Discard"),
                close: true,
            }],
        }, options || {});
        this._super(parent, this.options);
    },
    /**
     * @override
     */
    willStart: function () {
        var self = this;
        var def = this._super.apply(this, arguments);
        if (this.imageData.isExternalImage) {
            return def;
        }

        var defs = [def, ajax.loadLibs(this)];
        var params = {};
        var isDBImage = false;
        var matchImageID = this.imageData.imageSrc.match(/^\/web\/image\/(\d+)/);
        if (matchImageID) {
            params['image_id'] = parseInt(matchImageID[1]);
            isDBImage = true;
        } else {
            var matchXmlID = this.imageData.imageSrc.match(/^\/web\/image\/([^/?]+)/);
            if (matchXmlID) {
                params['xml_id'] = matchXmlID[1];
                isDBImage = true;
            }
        }
        if (isDBImage) {
            defs.push(this._rpc({
                route: '/web_editor/get_image_info',
                params: params,
            }).then(function (res) {
                _.extend(self.imageData, res);
            }));
        }
        return $.when.apply($, defs);
    },
    /**
     * @override
     */
    start: function () {
        this.$cropperImage = this.$('.o_cropper_image');
        if (this.$cropperImage.length) {
            var data = this.$media.data();
            var ratio = 0;
            for (var i = 0 ; i < this.aspectRatioList.length ; i++) {
                if (this.aspectRatioList[i][1] === data.aspectRatio) {
                    ratio = this.aspectRatioList[i][2];
                    break;
                }
            }
            this.$cropperImage.cropper({
                viewMode: 1,
                autoCropArea: 1,
                aspectRatio: ratio,
                data: _.pick(data, 'x', 'y', 'width', 'height', 'rotate', 'scaleX', 'scaleY')
            });
        }
        return this._super.apply(this, arguments);
     },
    /**
     * @override
     */
    destroy: function () {
        if (this.$cropperImage.length) {
            this.$cropperImage.cropper('destroy');
        }
        this._super.apply(this, arguments);
    },
    /**
     * Updates the DOM image with cropped data and associates required
     * information for a potential future save (where required cropped data
     * attachments will be created).
     *
     * @override
     */
    save: function () {
        var self = this;
        var cropperData = this.$cropperImage.cropper('getData');

        // Mark the media for later creation of required cropped attachments...
        this.$media.addClass('o_cropped_img_to_save');

        // ... and attach required data
        this.$media.data('crop:resModel', this.options.res_model);
        this.$media.data('crop:resID', this.options.res_id);
        this.$media.data('crop:id', this.imageData.id);
        this.$media.data('crop:mimetype', this.imageData.mimetype);
        this.$media.data('crop:originalSrc', this.imageData.originalSrc);

        // Mark the media with the cropping information which is required for
        // a future crop edition
        this.$media
            .attr('data-aspect-ratio', this.imageData.aspectRatio)
            .data('aspectRatio', this.imageData.aspectRatio);
        _.each(cropperData, function (value, key) {
            key = _.str.dasherize(key);
            self.$media.attr('data-' + key, value);
            self.$media.data(key, value);
        });

        // Update the media with base64 source for preview before saving
        var canvas = this.$cropperImage.cropper('getCroppedCanvas', {
            width: cropperData.width,
            height: cropperData.height,
        });
        this.$media.attr('src', canvas.toDataURL(this.imageData.mimetype));

        this.$media.trigger('content_changed');

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a crop option is clicked -> change the crop area accordingly.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onCropOptionClick: function (ev) {
        var $option = $(ev.currentTarget);
        var opt = $option.data('event');
        var value = $option.data('value');
        switch (opt) {
            case 'ratio':
                this.$cropperImage.cropper('reset');
                this.imageData.aspectRatio = $option.data('label');
                this.$cropperImage.cropper('setAspectRatio', value);
                break;
            case 'zoom':
            case 'rotate':
            case 'reset':
                this.$cropperImage.cropper(opt, value);
                break;
            case 'flip':
                var direction = value === 'horizontal' ? 'x' : 'y';
                var scaleAngle = -$option.data(direction);
                $option.data(direction, scaleAngle);
                this.$cropperImage.cropper('scale' + direction.toUpperCase(), scaleAngle);
                break;
        }
    },
});

return {
    Dialog: Dialog,
    AltDialog: AltDialog,
    MediaDialog: MediaDialog,
    LinkDialog: LinkDialog,
    CropImageDialog: CropImageDialog,
    ImageWidget: ImageWidget,
};
});
