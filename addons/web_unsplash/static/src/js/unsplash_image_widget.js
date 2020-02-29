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
        'dblclick .unsplash_img_container [data-imgid]': '_onUnsplashImgDblClick',
        'click .unsplash_img_container [data-imgid]': '_onUnsplashImgClick',
        'click button.save_unsplash': '_onSaveUnsplash',
        'click .o_search_an_image, .o_search_from_unsplash': '_onSourceSwitchClick',
        'keyup .o_we_search, .o_search_an_image, .o_search_from_unsplash': '_onPressKeySearch',
    }),

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);

        this._unsplash = {
            isActive: false,
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
    start: function () {
        this.$('.o_we_search_icon').replaceWith(core.qweb.render('web_unsplash.dialog.media.search_icon'));
        return this._super.apply(this, arguments);
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
        if (!this._unsplash.isActive) {
            return this._super.apply(this, arguments);
        }

        this._unsplash.query = needle;

        var always = function () {
            if (!noRender) {
                self._renderImages();
            }
        };
        return this.unsplashAPI.getImages(needle, this.numberOfAttachmentsToDisplay).then(function (res) {
            self._unsplash.isMaxed = res.isMaxed;
            self._unsplash.records = res.images;
            self._unsplash.error = false;
        }, function (err) {
            self._unsplash.error = err;
        }).then(always).guardedCatch(always);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _highlightSelected: function () {
        var self = this;
        if (!this._unsplash.isActive) {
            return this._super.apply(this, arguments);
        }

        this.$('.o_unsplash_img_cell.o_selected').removeClass('o_selected');
        var $select = this.$('.o_unsplash_img_cell [data-imgid]').filter(function () {
            return $(this).data('imgid') in self._unsplash.selectedImages;
        });
        $select.closest('.o_unsplash_img_cell').addClass('o_selected');
        return $select;
    },
    /**
     * @private
     */
    _loadMoreImages: function (forceSearch) {
        this._super(this._unsplash.isActive || forceSearch);
    },
    /**
     * @override
     */
    _renderImages: function () {
        if (!this._unsplash.isActive) {
            return this._super.apply(this, arguments);
        }

        if (this._unsplash.error) {
            this.$('.unsplash_img_container').html(
                core.qweb.render('web_unsplash.dialog.error.content', {
                    status: this._unsplash.error,
                })
            );
            return;
        }

        this.$('.unsplash_img_container').html(core.qweb.render('web_unsplash.dialog.image.content', {records: this._unsplash.records}));
        this._highlightSelected();

        this.$('.o_load_more').toggleClass('d-none', !!this._unsplash.error || this._unsplash.isMaxed);
        this.$('.o_load_done_msg').toggleClass('d-none', !!this._unsplash.error || !this._unsplash.isMaxed);
    },
    /**
     * @private
     * @param {boolean} show
     */
    _toggleUnsplashContainer: function (show) {
        this._unsplash.isActive = show;
        this.$('.o_we_existing_attachments').toggleClass('d-none', show);
        this.$('.unsplash_img_container').toggleClass('d-none', !show);
        this.$('.o_we_search_icon > span').text(show ? "Unsplash" : "");
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
        var imgid = $(ev.currentTarget).data('imgid');
        var url = $(ev.currentTarget).data('url');
        var downloadURL = $(ev.currentTarget).data('download-url');
        if (!this.options.multiImages) {
            this._unsplash.selectedImages = {};
        }
        if (imgid in this._unsplash.selectedImages) {
            delete this._unsplash.selectedImages[imgid];
        } else {
            this._unsplash.selectedImages[imgid] = {url: url, download_url: downloadURL};
        }
        this._highlightSelected();
    },
    /**
     * @private
     */
    _onUnsplashImgDblClick: function (ev) {
        this.trigger_up('save_request');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onSourceSwitchClick: function (ev) {
        this._toggleUnsplashContainer(!$(ev.currentTarget).is('.o_search_an_image'));
        this.search(this.$('.o_we_search').val() || '');
    },
    /**
     * @private
     */
    _onPressKeySearch: function (ev) {
        switch (ev.which) {
            case $.ui.keyCode.UP:
                this.$('.o_search_an_image').focus();
                break;
            case $.ui.keyCode.DOWN:
                this.$('.o_search_from_unsplash').focus();
                break;
            default:
                return;
        }
        ev.preventDefault();
    },
    /**
     * @override
     */
    _onSearchInput: function (ev) {
        var $input = $(ev.currentTarget);
        var inputValue = $input.val();
        this.$('.o_search_value_input').text(inputValue);

        var $icon = this.$('.o_we_search_icon');
        if ($icon.parent().is('.show')) {
            $icon.dropdown('update');
        } else if (!this.hasSearched) {
            $icon.dropdown('toggle');
            $input.focus();
        }
        this._super.apply(this, arguments);
    },
});
});
