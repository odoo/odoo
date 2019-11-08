odoo.define('web_unsplash.image_widgets', function (require) {
'use strict';

var core = require('web.core');
var UnsplashAPI = require('unsplash.api');
var widgetsMedia = require('wysiwyg.widgets.media');

var unsplashAPI = null;

widgetsMedia.ImageWidget.include({
    xmlDependencies: widgetsMedia.ImageWidget.prototype.xmlDependencies.concat(
        ['/web_unsplash/static/src/xml/unsplash_image_widget.xml']
    ),
    events: _.extend({}, widgetsMedia.ImageWidget.prototype.events, {
        'click .unsplash_img_container .o_image_controls': '_onUnsplashImgClick',
        'click button.save_unsplash': '_onSaveUnsplash',
    }),

    MAX_DB_IMAGES: 5,

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.maxDbImages = this.MAX_DB_IMAGES;

        this._unsplash = {
            records: [],
            selectedImages: {},
            isMaxed: false,
            query: false,
            error: false,
        };

        // TODO improve this
        //
        // This is a `hack` to prevent the UnsplashAPI to be destroyed every
        // time the media dialog is closed. Indeed, UnsplashAPI has a cache
        // system to recude unsplash call, it is then better to keep its state
        // to take advantage from it from one media dialog call to another.
        //
        // Unsplash API will either be (it's still being discussed):
        //  * a service (ideally coming with an improvement to not auto load
        //    the service)
        //  * initialized in the website_root (trigger_up)
        if (unsplashAPI === null) {
            this.unsplashAPI = new UnsplashAPI(this);
            unsplashAPI = this.unsplashAPI;
        } else {
            this.unsplashAPI = unsplashAPI;
            this.unsplashAPI.setParent(this);
        }
    },
    /**
     * @override
     */
    destroy: function () {
        // TODO See `hack` explained in `init`. This prevent the media dialog destroy
        //      to destroy unsplashAPI when destroying the children
        this.unsplashAPI.setParent(undefined);
        this._super.apply(this, arguments);
    },

    // --------------------------------------------------------------------------
    // Public
    // --------------------------------------------------------------------------

    /**
     * @override
     */
    _save: function () {
        if (!this._unsplash.query || !this.selectedAttachments[0].isUnsplash) {
            return this._super.apply(this, arguments);
        }
        var self = this;
        var args = arguments;
        var _super = this._super;
        return this._rpc({
            route: '/web_unsplash/attachment/add',
            params: {
                unsplashurls: self._unsplash.selectedImages,
                res_model: self.options.res_model,
                res_id: self.options.res_id,
                query: self._unsplash.query,
            }
        }).then(function (images) {
            self.attachments = images;
            self.selectedAttachments = images;
            return _super.apply(self, args);
        });
    },
    /**
     * @override
     */
    search: function (needle, noRender) {
        var self = this;

        this._unsplash.query = needle;

        var always = function () {
            if (!noRender) {
                self._renderImages(!!needle);
            }
        };
        return Promise.all([
            this._super.apply(this, [needle, true]),
            this.unsplashAPI.getImages(needle, this.numberOfAttachmentsToDisplay).then(function (res) {
                self._unsplash.isMaxed = res.isMaxed;
                self._unsplash.records = res.images;
                self._unsplash.error = false;
            }, function (err) {
                self._unsplash.error = err;
            })
        ]).then(always).guardedCatch(always);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _loadMoreImages: function (forceSearch) {
        this._super(true);
    },
    /**
     * @override
     */
    _renderImages: function (limitDbImages) {
        this.$('.unsplash_error').remove();
        if (!limitDbImages) {
            return this._super.apply(this, arguments);
        }
        if (this._unsplash.error) {
            this.$('.o_we_existing_attachments').after(
                core.qweb.render('web_unsplash.dialog.error.content', {
                    status: this._unsplash.error,
                })
            );
        }

        this.attachments = this.attachments.slice(0, this.maxDbImages)
            .concat(this._unsplash.records.map(r => _.extend({}, r, {
                isUnsplash: true,
                urls: {
                    thumbnail: r.urls.raw + '&w=256&h=192',
                    hd: r.urls.raw + '&w=1920',
                }
            })));
        this._super.apply(this, arguments);

        this._highlightSelected();

        this.$('.o_load_more').toggleClass('d-none', !!this._unsplash.error || this._unsplash.isMaxed);
        this.$('.o_load_done_msg').toggleClass('d-none', !!this._unsplash.error || !this._unsplash.isMaxed);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onSaveUnsplash: function () {
        var self = this;
        var key = this.$('#accessKeyInput').val().trim();
        var appId = this.$('#appIdInput').val().trim();

        this.$('#accessKeyInput').toggleClass('is-invalid', !key);
        this.$('#appIdInput').toggleClass('is-invalid', !appId);

        if (key && appId) {
            var params = {
                'key': key,
                'appId': appId,
            };

            if (!this.$el.find('.is-invalid').length) {
                this._rpc({
                    route: '/web_unsplash/save_unsplash',
                    params: params,
                }).then(function () {
                    self.unsplashAPI.clientId = key;
                    self._unsplash.error = false;
                    self.search(self._unsplash.query);
                });
            }
        }
    },
    /**
     * @private
     */
    _onUnsplashImgClick: function (ev) {
        const $img = $(ev.currentTarget).siblings().find('img[data-imgid]');
        var imgid = $img.data('imgid');
        if (!this.options.multiImages) {
            this._unsplash.selectedImages = {};
        }
        if (imgid in this._unsplash.selectedImages) {
            delete this._unsplash.selectedImages[imgid];
        } else {
            this._unsplash.selectedImages[imgid] = {
                alt: $img.attr('alt'),
                url: $img.data('url'),
                download_url: $img.data('download-url'),
            };
        }
        this._highlightSelected();
    },
});
});
