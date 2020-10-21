odoo.define('wysiwyg.widgets.MediaDialog', function (require) {
'use strict';

var core = require('web.core');
var MediaModules = require('wysiwyg.widgets.media');
var Dialog = require('wysiwyg.widgets.Dialog');

var _t = core._t;

/**
 * MediaDialog widget. Lets users change a media, including uploading a
 * new image, font awsome or video and can change a media into an other
 * media.
 */
var MediaDialog = Dialog.extend({
    template: 'wysiwyg.widgets.media',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/web_editor/static/src/xml/wysiwyg.xml']
    ),
    events: _.extend({}, Dialog.prototype.events, {
        'click a[data-toggle="tab"]': '_onTabChange',
    }),
    custom_events: _.extend({}, Dialog.prototype.custom_events || {}, {
        save_request: '_onSaveRequest',
    }),

    /**
     * @constructor
     */
    init: function (parent, options, media) {
        var self = this;
        options = options || {};

        this._super(parent, _.extend({}, {
            title: _t("Select a Media"),
            save_text: _t("Add"),
        }, options));

        this.trigger_up('getRecordInfo', {
            recordInfo: options,
            type: 'media',
            callback: function (recordInfo) {
                _.defaults(options, recordInfo);
            },
        });

        this.media = media;
        this.$media = $(media);

        this.multiImages = options.multiImages;
        var onlyImages = options.onlyImages || this.multiImages;
        this.noImages = options.noImages;
        this.noDocuments = onlyImages || options.noDocuments;
        this.noIcons = onlyImages || options.noIcons;
        this.noVideos = onlyImages || options.noVideos;

        if (!this.noDocuments) {
            this.documentDialog = new MediaModules.ImageWidget(this, this.media, _.extend({}, options, {
                document: true,
            }));
            this.documentDialog.tabToShow = 'document';
        }
        if (!this.noIcons) {
            this.iconDialog = new MediaModules.IconWidget(this, this.media, options);
            this.iconDialog.tabToShow = 'icon';
        }
        if (!this.noVideos) {
            this.videoDialog = new MediaModules.VideoWidget(this, this.media, options);
            this.videoDialog.tabToShow = 'video';
        }
        if (!this.noImages) {
            this.imageDialog = new MediaModules.ImageWidget(this, this.media, options);
            this.imageDialog.tabToShow = 'image';
        }

        this.active = this.imageDialog || this.documentDialog || this.iconDialog || this.videoDialog;
        if (this.imageDialog && this.$media.is('img')) {
            this.active = this.imageDialog;
        } else if (this.documentDialog && this.$media.is('a.o_image')) {
            this.active = this.documentDialog;
        } else if (this.videoDialog && this.$media.hasClass('media_iframe_video')) {
            this.active = this.videoDialog;
        } else if (this.iconDialog && this.$media.is('span, i')) {
            this.active = this.iconDialog;
        }

        this.opened(function () {
            self.$('[href="#editor-media-' + self.active.tabToShow + '"]').tab('show');
        });
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
            this.imageDialog.clear();
        }
        if (this.documentDialog) {
            this.documentDialog.clear();
        }
        if (this.iconDialog) {
            this.iconDialog.clear();
        }
        if (this.videoDialog) {
            this.videoDialog.clear();
        }

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

        return Promise.all(defs).then(function () {
            self._setActive(self.active);
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
        var _super = this._super;
        var args = arguments;
        var oldClasses = this.media ? _.toArray(this.media.classList) : [];
        return Promise.resolve(this.active.save()).then(function (data) {
            self.final_data = data;
            // In the case of multi images selection we suppose this was not to
            // replace an old media, so we only retrieve the images and save.
            if (!self.multiImages) {
                // Restore classes if the media was replaced (when changing type)
                data.className = _.union(_.toArray(data.classList), oldClasses).join(' ');
                // TODO this dialog triggers 'save' and 'saved' with different
                // data on close... should refactor to avoid confusion...
                self.trigger('saved', {
                    attachments: self.active.images,
                    media: data,
                });
            }
            return _super.apply(self, args);
        });
    },

    //--------------------------------------------------------------------------
    //
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} widget
     */
    _setActive: function (widget) {
        this.active = widget;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSaveRequest: function (ev) {
        ev.stopPropagation();
        this.save();
    },
    /**
     * @private
     * @param {JQueryEvent} ev
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

return MediaDialog;
});
