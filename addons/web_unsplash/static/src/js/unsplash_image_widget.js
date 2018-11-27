odoo.define('web_unsplash.image_widgets', function (require) {
'use strict';

var core = require('web.core');
var UnsplashAPI = require('unsplash.api');
var weWidgets = require('web_editor.widget');
var QWeb = core.qweb;

var unsplashAPI = null;

weWidgets.ImageWidget.include({
    xmlDependencies: weWidgets.ImageWidget.prototype.xmlDependencies.concat(
        ['/web_unsplash/static/src/xml/unsplash_image_widget.xml']
    ),
    events: _.extend({}, weWidgets.ImageWidget.prototype.events, {
        'dblclick .unsplash_img_container [data-imgid]': '_onUnsplashImgDblClick',
        'click .unsplash_img_container [data-imgid]': '_onUnsplashImgClick',
        'click button.save_unsplash': '_onSaveUnsplash',
        'click button.access_key': '_onSetAccessKey',
        'click .o_load_more': '_onLoadMore',
        'click .o_search_from_unsplash': '_onSearchFromUnsplash',
        'click .o_search_an_image': '_onSearchImage',
        'keyup input#icon-search, .o_dropdown_search': '_onPressKeySearch',
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
                res_model: self.options.res_model,
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

            self.$('.unsplash_img_container').html(QWeb.render('web_unsplash.dialog.image.content', {rows: rows}));
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
        this.$('.existing-attachments').toggleClass('d-none', !hideUnsplash);
        this.$('.unsplash_img_container').toggleClass('d-none', hideUnsplash);
        this.$('.o_load_more').toggleClass('d-none', hideUnsplash);
        this.$('.o_load_done_msg').toggleClass('d-none', !hideUnsplash);
        this.trigger_up('update_control_panel');
    },
    /**
     * @private
     */
     _toggleLoadMoreBtnUnsplash: function (display) {
        this.$('.o_load_done_msg').toggleClass('d-none', display);
    },
    /**
     * @private
     */
    _toggleSearchDropdown: function (show) {
        var inputValue = this.$('#icon-search').val();
        this.$('.o_search_value_input').text(inputValue);
        this.$('.o_dropdown_search').toggleClass('show', show);
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
        this._unsplash.query = this.$('#icon-search').val().trim();
        if (this._unsplash.query) {
            this.oldPage = this.page;
            this.page = 1;
            this._renderImages();
        } else {
            this.page = this.oldPage || 1;
            this._toggleAttachmentContaines(true);
        }
        this._toggleLoadMoreBtnUnsplash(true);
    }, 1000),
    /**
     * @private
     */
    _onUnsplashImgClick: function (ev) {
        var imgid = $(ev.currentTarget).data('imgid');
        var url = $(ev.currentTarget).data('url');
        var downloadUrl = $(ev.currentTarget).data('download-url');
        if (!this.multiImages) {
            this._unsplash.selectedImages = {};
        }
        if (imgid in this._unsplash.selectedImages) {
            delete this._unsplash.selectedImages[imgid];
        } else {
            this._unsplash.selectedImages[imgid] = {url: url, downloadUrl: downloadUrl};
        }
        this._highlightSelectedImages();
    },
    /**
     * @private
     */
    _onUnsplashImgDblClick: function (ev) {
        this.trigger_up('save_request');
    },
    /**
     * @private
     */
    _onLoadMore: function () {
        this._unsplash.query = this.$('#icon-search').val().trim();
        this._loadMoreImages();
    },
    /**
     * @private
     */
    _onSearchFromUnsplash: function () {
        this.$('.o_dropdown_search').removeClass('show');
        this._toggleAttachmentContaines(false);
        this._onChangeUnsplashSearch();
    },
    /**
     * @private
     */
    _onSearchImage: function () {
        var searchText = this.$('#icon-search').val().trim();
        this._unsplash.query = false;
        this.search(searchText);
        this.$('.o_dropdown_search').removeClass('show');
        this._toggleAttachmentContaines(true);
        this._renderImages();
    },
    /**
     * @private
     */
    _onPressKeySearch: function (ev) {
        var $searchAnImage = this.$('button.dropdown-item.o_search_an_image');
        switch (ev.which) {
            case $.ui.keyCode.ENTER:
                $searchAnImage.focus();
                break;
            case $.ui.keyCode.UP:
                $searchAnImage.focus();
                break;
            case $.ui.keyCode.DOWN:
                $searchAnImage.next().focus();
                break;
            default: return;
        }
        ev.preventDefault();
    },
    /**
     * @override
     */
    _onSearchInput: function (ev) {
        if (!this.options.document) {
            this._toggleSearchDropdown(true);
        } else {
            this.search($(ev.currentTarget).val() || '');
        }
    },
});

});
