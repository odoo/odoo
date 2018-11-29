odoo.define('web_unsplash.image_widgets', function (require) {
'use strict';

var core = require('web.core');
var UnsplashAPI = require('unsplash.api');

var ImageWidget = require('web_editor.widget').ImageWidget;
var QWeb = core.qweb;

var unsplashAPI = null;

ImageWidget.include({
    xmlDependencies: ImageWidget.prototype.xmlDependencies.concat(
        ['/web_unsplash/static/src/xml/unsplash_image_widget.xml']
    ),
    events: _.extend({}, ImageWidget.prototype.events, {
        'input input.unsplash_search': '_onChangeUnsplashSearch',
        'dblclick .unsplash_img_container [data-imgid]': '_onUnsplashImgDblClick',
        'click .unsplash_img_container [data-imgid]': '_onUnsplashImgClick',
        'click button.save_unsplash': '_onSaveUnsplash',
    }),
    /**
     * @override
     */
    init: function () {
        this._unsplash = {
            selectedImages: {},
            isMaxed: false,
            query: false,
        };
        // TODO This is a `hack` to prevent the UnsplashAPI to be destroyed every time
        //      the media dialog is closed.
        //      Indeed, UnsplashAPI has a cache system to recude unsplash call, it is
        //      then better to keep its state to benefic from it from one media dialog
        //      call to another.
        //      Unsplash API will either be (it's still being discussed):
        //      * a service (ideally coming with an improvement to not auto load the service)
        //      * initialized in the website_root (trigger_up)
        var def = this._super.apply(this, arguments);
        if (unsplashAPI === null) {
            this.unsplashAPI = new UnsplashAPI(this);
            unsplashAPI = this.unsplashAPI;
        } else {
            this.unsplashAPI = unsplashAPI;
            this.unsplashAPI.setParent(this);
        }
        return def;
    },
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
    getControlPanelConfig: function () {
        var config = this._super.apply(this, arguments);
        if (this._unsplash.query) {
            _.extend(config, {
                pagerLeftEnabled: this.page > 1,
                pagerRightEnabled: !this._unsplash.isMaxed,
            });
        }
        return config;
    },
    /**
     * @override
     */
    save: function () {
        if (!this._unsplash.query) {
            return this._super.apply(this, arguments);
        }
        var self = this;
        var args = arguments;
        var _super = this._super;
        return this._rpc({
            route: '/web_unsplash/attachment/add',
            params: {
                unsplashurls: self._unsplash.selectedImages,
                res_model : self.options.res_model,
                res_id: self.options.res_id,
                query: self._unsplash.query,
            }
        }).then(function (images) {
            _.each(images, function (image) {
                image.src = image.url;
                image.isDocument = !(/gif|jpe|jpg|png/.test(image.mimetype));
            });
            self.images = images;
            return _super.apply(self, args);
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Highlights selected image, when an image is clicked and when pager change
     *
     * @private
     */
    _highlightSelectedImages: function () {
        var self = this;
        if (!this._unsplash.query) {
            return this._super.apply(this, arguments);
        }
        this.$('.o_unsplash_img_cell.o_selected').removeClass("o_selected");
        var $select = this.$('.o_unsplash_img_cell [data-imgid]').filter(function () {
            return $(this).data('imgid') in self._unsplash.selectedImages;
        });
        $select.closest('.o_unsplash_img_cell').addClass("o_selected");
        return $select;
    },
    /**
     * @override
     */
    _renderImages: function () {
        var self = this;
        if (!this._unsplash.query) {
            return this._super.apply(this, arguments);
        }
        this.unsplashAPI.getImages(this._unsplash.query, this.IMAGES_PER_PAGE, this.page).then(function (res) {
            self._unsplash.isMaxed = res.isMaxed;
            var rows = _(res.images).chain()
                .groupBy(function (a, index) { return Math.floor(index / self.IMAGES_PER_ROW); })
                .values()
                .value();

            self.$('.unsplash_img_container').html(QWeb.render('web_unsplash.dialog.image.content', { rows: rows }));
            self._highlightSelectedImages();
        }).fail(function (err) {
            self.$('.unsplash_img_container').html(QWeb.render('web_unsplash.dialog.error.content', { status: err }));
        }).always(function () {
            self._toggleAttachmentContaines(false);
        });
    },
    /**
     * @private
     */
    _toggleAttachmentContaines: function (hideUnsplash) {
        this.$('.existing-attachments').toggleClass('o_hidden', !hideUnsplash);
        this.$('.unsplash_img_container').toggleClass('o_hidden', hideUnsplash);
        this.trigger_up('update_control_panel');
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
                    self._renderImages();
                });
            }
        }
    },
    /**
     * @private
     */
    _onChangeUnsplashSearch: _.debounce(function () {
        // oldPage saves the original image widget pager.
        // Emptying the unsplash search will set the pager to its previous state
        this._unsplash.query = this.$('.unsplash_search').val().trim();
        if (this._unsplash.query) {
            this.oldPage = this.page;
            this.page = 1;
            this._renderImages();
        } else {
            this.page = this.oldPage || 0;
            this._toggleAttachmentContaines(true);
        }
    }, 1000),
    /**
     * @private
     */
    _onUnsplashImgClick: function (ev) {
        var imgid = $(ev.currentTarget).data('imgid');
        var url = $(ev.currentTarget).data('url');
        var download_url = $(ev.currentTarget).data('download-url');
        if (!this.multiImages) {
            this._unsplash.selectedImages = {};
        }
        if (imgid in this._unsplash.selectedImages) {
            delete this._unsplash.selectedImages[imgid];
        } else {
            this._unsplash.selectedImages[imgid] = {url: url, download_url: download_url};
        }
        this._highlightSelectedImages();
    },
    /**
     * @private
     */
    _onUnsplashImgDblClick: function (ev) {
        this.trigger_up('save_request');
    },
});
});
