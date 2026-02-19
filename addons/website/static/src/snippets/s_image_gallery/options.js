/** @odoo-module **/

import { MediaDialog } from "@web_editor/components/media_dialog/media_dialog";
import options from "@web_editor/js/editor/snippets.options";
import wUtils from '@website/js/utils';
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import {
    loadImageInfo,
    applyModifications,
} from "@web_editor/js/editor/image_processing";

/**
 * This class provides layout methods for interacting with the ImageGallery
 * snippet. It is used by all options that need the layout to be recomputed.
 * This is typically the case when adding/removing/moving images, changing the
 * layout mode and changing the number of columns.
 */
options.registry.GalleryLayout = options.registry.CarouselHandler.extend({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Get the image target's layout mode (slideshow, masonry, grid or nomode).
     *
     * @private
     * @returns {String('slideshow'|'masonry'|'grid'|'nomode')}
     */
    _getMode() {
        var mode = 'slideshow';
        if (this.$target.hasClass('o_masonry')) {
            mode = 'masonry';
        }
        if (this.$target.hasClass('o_grid')) {
            mode = 'grid';
        }
        if (this.$target.hasClass('o_nomode')) {
            mode = 'nomode';
        }
        return mode;
    },
    /**
     * Displays the images with the "grid" layout.
     *
     * @private
     */
    _grid() {
        const mediaHolderEls = this._getImgHolderEls();
        var $row = $('<div/>', {class: 'row s_nb_column_fixed'});
        var columns = this._getColumns();
        var colClass = 'col-lg-' + (12 / columns);
        var $container = this._replaceContent($row);

        mediaHolderEls.forEach((mediaHolderEl, index) => {
            const $mediaHolder = $(mediaHolderEl.cloneNode(true));
            var $col = $('<div/>', {class: colClass});
            $col.append($mediaHolder).appendTo($row);
            if ((index + 1) % columns === 0) {
                $row = $('<div/>', {class: 'row s_nb_column_fixed'});
                $row.appendTo($container);
            }
        });
        this.$target.css('height', '');
    },
    /**
     * Displays the images with the "masonry" layout.
     *
     * @private
     * @returns {Promise}
     */
    _masonry() {
        const mediaHolderEls = this._getImgHolderEls();
        var columns = this._getColumns();
        var colClass = 'col-lg-' + (12 / columns);
        var cols = [];

        var $row = $('<div/>', {class: 'row s_nb_column_fixed'});
        this._replaceContent($row);

        // Create columns
        for (var c = 0; c < columns; c++) {
            var $col = $('<div/>', {class: 'o_masonry_col o_snippet_not_selectable ' + colClass});
            $row.append($col);
            cols.push($col[0]);
        }

        // Dispatch medias in columns by always putting the next one in the
        // smallest-height column
        return new Promise(async resolve => {
            for (const mediaHolderEl of mediaHolderEls) {
                let min = Infinity;
                let smallestColEl;
                for (const colEl of cols) {
                    const colMediaEls = colEl.querySelectorAll("img, .media_iframe_video");
                    const lastMediaRect = colMediaEls.length && colMediaEls[colMediaEls.length - 1].getBoundingClientRect();
                    const height = lastMediaRect ? Math.round(lastMediaRect.top + lastMediaRect.height) : 0;
                    if (height < min) {
                        min = height;
                        smallestColEl = colEl;
                    }
                }
                // Only on Chrome: appended images are sometimes invisible
                // and not correctly loaded from cache, we use a clone of the
                // image to force the loading.
                smallestColEl.append(mediaHolderEl.cloneNode(true));
                await wUtils.onceAllImagesLoaded(this.$target);
            }
            resolve();
        });
    },
    /**
     * Allows to change the images layout. @see grid, masonry, nomode, slideshow
     *
     * @private
     * @param {string} modeName
     * @returns {Promise}
     */
    async _setMode(modeName) {
        modeName = modeName || 'slideshow'; // FIXME should not be needed
        if (modeName !== "slideshow") {
            this.$target.css("height", "");
        }
        this.$target
            .removeClass('o_nomode o_masonry o_grid o_slideshow')
            .addClass('o_' + modeName);
        // Used to prevent the editor's "unbreakable protection mechanism" from
        // restoring Image Wall adaptations (images removed > new images added
        // to the container & layout updates) when adding new images to the
        // snippet.
        if (this.options.wysiwyg) {
            this.options.wysiwyg.odooEditor.unbreakableStepUnactive();
        }
        await this[`_${modeName}`]();
        this.trigger_up('cover_update');
        await this._refreshPublicWidgets();
    },
    /**
     * Displays the medias with the standard layout: floating medias.
     *
     * @private
     */
    _nomode() {
        var $row = $('<div/>', {class: 'row s_nb_column_fixed'});
        const mediaEls = this._getItemsGallery();
        const mediaHolderEls = this._getImgHolderEls();

        this._replaceContent($row);

        mediaEls.forEach((mediaEl, index) => {
            var wrapClass = 'col-lg-3';
            if (mediaEl.width >= mediaEl.height * 2 || mediaEl.width > 600 || mediaEl.classList.contains("media_iframe_video")) {
                wrapClass = 'col-lg-6';
            }
            const $wrap = $("<div/>", { class: wrapClass }).append(mediaHolderEls[index]);
            $row.append($wrap);
        });
    },
    /**
     * Displays the medias with a "slideshow" layout.
     *
     * @private
     */
    async _slideshow() {
        const mediaEls = this._getItemsGallery();
        const mediaHolderEls = this._getImgHolderEls();
        // Get the images src and the videos thumbnail urls.
        const mediaSrc = [];
        for (const mediaEl of mediaHolderEls) {
            let src;
            if (mediaEl.tagName === "IMG") {
                // Use getAttribute to get the attribute value otherwise .src
                // returns the absolute url.
                src = mediaEl.getAttribute("src");
            } else if (mediaEl.classList.contains("media_iframe_video")) {
                // For videos, get the thumbnail image link.
                src = await this._getVideoThumbnailUrl(mediaEl.dataset.oeExpression);
            } else if (mediaEl.tagName === "A") {
                src = mediaEl.querySelector("img").getAttribute("src");
            }
            mediaSrc.push(src);
        }

        const images = mediaHolderEls.map((media, index) => ({
            src: mediaSrc[index],
            // TODO: remove me in master. This is not needed anymore as the
            // images of the rendered `website.gallery.slideshow` are replaced
            // by the elements of `mediaHolderEls`.
            alt: media.getAttribute("alt"),
        }));
        var currentInterval = this.$target.find('.carousel:first').attr('data-bs-interval');
        var params = {
            images: images,
            index: 0,
            title: "",
            interval: currentInterval || 0,
            id: 'slideshow_' + new Date().getTime(),
            // TODO: in master, remove `attrClass` and `attStyle` from `params`.
            // This is not needed anymore as the images of the rendered
            // `website.gallery.slideshow` are replaced by the elements of
            // `mediaHolderEls`.
            attrClass: mediaEls.length > 0 ? mediaEls[0].className : '',
            attrStyle: mediaEls.length > 0 ? mediaEls[0].style.cssText : "",
        },
        $slideshow = $(renderToElement('website.gallery.slideshow', params));
        const imgSlideshowEls = $slideshow[0].querySelectorAll("img[data-o-main-image]");
        imgSlideshowEls.forEach((imgSlideshowEl, index) => {
            // Replace the template image by the original one. This is needed in
            // order to keep the characteristics of the image such as the
            // filter, the width, the quality, the link on which the users are
            // redirected once they click on the image etc...
            imgSlideshowEl.after(mediaHolderEls[index]);
            imgSlideshowEl.remove();
        });
        this._replaceContent($slideshow);
        const indicatorEls = [...this.$target[0].querySelectorAll("[data-bs-slide-to]")];
        mediaEls.forEach((mediaEl, index) => {
            $(mediaEl).attr({ contenteditable: true, "data-index": index });
            if (mediaEl.classList.contains("media_iframe_video")) {
                this._addVideoPlayIcon(indicatorEls[index]);
            }
        });

        // Apply layout animation
        this.$target.off('slide.bs.carousel').off('slid.bs.carousel');
        this._slideshowStart();
        this.$('li.fa').off('click');
    },
    /**
     * @override
     */
    _getItemsGallery() {
        const mediaEls = this.$target.find("img, .media_iframe_video").get();
        return mediaEls.sort((a, b) => this._getIndex(a) - this._getIndex(b));
    },
    /**
     * Returns the medias, or the medias holder if this holder is an anchor,
     * sorted by index.
     *
     * @private
     * @returns {Array.<HTMLImageElement|HTMLAnchorElement>}
     */
    _getImgHolderEls: function () {
        const mediaEls = this._getItemsGallery();
        return mediaEls.map((mediaEl) => mediaEl.closest("a") || mediaEl);
    },
    /**
     * Returns the index associated to a given image.
     *
     * @private
     * @param {DOMElement} mediaEl
     * @returns {integer}
     */
    _getIndex: function (mediaEl) {
        return mediaEl.dataset.index || 0;
    },
    /**
     * Returns the currently selected column option.
     *
     * @private
     * @returns {integer}
     */
    _getColumns: function () {
        return parseInt(this.$target.attr('data-columns')) || 3;
    },
    /**
     * @override
     */
    _reorderItems(itemsEls, newItemPosition) {
        itemsEls.forEach((img, index) => {
            img.dataset.index = index;
        });
        this.trigger_up('snippet_edition_request', {exec: async () => {
            await this._relayout();
            if (this._getMode() === "slideshow") {
                this._updateIndicatorAndActivateSnippet(newItemPosition);
            } else {
                const imageEl = this.$target[0].querySelector(`[data-index='${newItemPosition}']`);
                this.trigger_up("activate_snippet", {
                    $snippet: $(imageEl),
                    ifInactiveOptions: true,
                });
            }
        }});
    },
    /**
     * Empties the container, adds the given content and returns the container.
     *
     * @private
     * @param {jQuery} $content
     * @returns {jQuery} the main container of the snippet
     */
    _replaceContent: function ($content) {
        var $container = this.$('> .container, > .container-fluid, > .o_container_small');
        $container.empty().append($content);
        return $container;
    },
    /**
     * Redraws the current layout.
     *
     * @private
     */
    _relayout() {
        return this._setMode(this._getMode());
    },
    /**
     * Sets up listeners on slideshow to activate selected image.
     */
    _slideshowStart() {
        const $carousel = this.$bsTarget.is(".carousel") ? this.$bsTarget : this.$bsTarget.find(".carousel");
        let _previousEditor;
        let _miniatureClicked;
        const carouselIndicatorsEl = this.$target[0].querySelector(".carousel-indicators");
        if (carouselIndicatorsEl) {
            carouselIndicatorsEl.addEventListener("click", () => {
                _miniatureClicked = true;
            });
        }
        let lastSlideTimeStamp;
        $carousel.on("slide.bs.carousel.image_gallery", (ev) => {
            lastSlideTimeStamp = ev.timeStamp;
            const activeImageEl = this.$target[0].querySelector(".carousel-item.active img");
            for (const editor of this.options.wysiwyg.snippetsMenu.snippetEditors) {
                if (editor.isShown() && editor.$target[0] === activeImageEl) {
                    _previousEditor = editor;
                    editor.toggleOverlay(false);
                }
            }
        });
        $carousel.on("slid.bs.carousel.image_gallery", (ev) => {
            if (!_previousEditor && !_miniatureClicked) {
                return;
            }
            _previousEditor = undefined;
            _miniatureClicked = false;
            // slid.bs.carousel is most of the time fired too soon by bootstrap
            // since it emulates the transitionEnd with a setTimeout. We wait
            // here an extra 20% of the time before retargeting edition, which
            // should be enough...
            const _slideDuration = new Date().getTime() - lastSlideTimeStamp;
            setTimeout(() => {
                const activeImageEl = this.$target[0].querySelector(".carousel-item.active img");
                this.trigger_up("activate_snippet", {
                    $snippet: $(activeImageEl),
                    ifInactiveOptions: true,
                });
            }, 0.2 * _slideDuration);
        });
    },
});

options.registry.gallery = options.registry.GalleryLayout.extend({
    /**
     * @override
     */
    start() {
        const _super = this._super.bind(this);
        let layoutPromise;
        const containerEl = this.$target[0].querySelector(":scope > .container, :scope > .container-fluid, :scope > .o_container_small");
        if (containerEl.querySelector(":scope > *:not(div)")) {
            layoutPromise = this._relayout();
        } else {
            layoutPromise = Promise.resolve();
        }
        return layoutPromise.then(() => _super.apply(this, arguments).then(() => {
            // Call specific mode's start if defined (e.g. _slideshowStart)
            const startMode = this[`_${this._getMode()}Start`];
            if (startMode) {
                startMode.bind(this)();
            }
        }));
    },
    /**
     * @override
     */
    cleanForSave() {
        if (this.$target.hasClass('slideshow')) {
            this.$target.removeAttr('style');
        }
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Allows to change the number of columns when displaying images with a
     * grid-like layout.
     *
     * @see this.selectClass for parameters
     */
    columns(previewMode, widgetValue, params) {
        const nbColumns = parseInt(widgetValue || '1');
        this.$target.attr('data-columns', nbColumns);

        return this._relayout();
    },
    /**
     * Allows to change the images layout. @see grid, masonry, nomode, slideshow
     *
     * @see this.selectClass for parameters
     */
    mode(previewMode, widgetValue, params) {
        return this._setMode(widgetValue);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'mode': {
                let activeModeName = 'slideshow';
                for (const modeName of params.possibleValues) {
                    if (this.$target.hasClass(`o_${modeName}`)) {
                        activeModeName = modeName;
                        break;
                    }
                }
                this.activeMode = activeModeName;
                return activeModeName;
            }
            case 'columns': {
                return `${this._getColumns()}`;
            }
        }
        return this._super(...arguments);
    },
    /**
     * @private
     */
    async _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'slideshow_mode_opt') {
            return false;
        }
        return this._super(...arguments);
    },
});

options.registry.GalleryImageList = options.registry.GalleryLayout.extend({
    /**
     * @override
     */
    init() {
        this.video_thumbnail_cache = new Map();
        this.rpc = this.bindService("rpc");
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    start() {
        // Make sure image and video previews are updated if they are replaced.
        this.$target.on("image_changed.gallery", "img", (ev) => {
            const mediaEl = ev.currentTarget;
            const src = mediaEl.getAttribute("src");
            this.onMediaChanged(ev, mediaEl, src, false);
        });
        this.$target.on("media_changed.gallery", ".media_iframe_video", async (ev) => {
            const mediaEl = ev.currentTarget;
            const thumbnailUrl = await this._getVideoThumbnailUrl(mediaEl.dataset.oeExpression);
            this.onMediaChanged(ev, mediaEl, thumbnailUrl, true);
        });

        // When the snippet is empty, an edition button is the default content
        // TODO find a nicer way to do that to have editor style
        this.$target.on('click.gallery', '.o_add_images', ev => {
            ev.stopImmediatePropagation();
            this.addImages(false);
        });

        this.$target.on('dropped.gallery', 'img', ev => {
            this._relayout();
            if (!ev.target.height) {
                $(ev.target).one('load', () => {
                    setTimeout(() => {
                        this.trigger_up('cover_update');
                    });
                });
            }
        });

        // If some medias do not have the `data-index` attribute, reset the mode
        // so everything is consistent. (Needed for already dropped snippets
        // whose images have been previously replaced by other media types).
        const mediaEls = this._getItemsGallery();
        const indexedMediaEls = this.$target[0].querySelectorAll("[data-index]");
        if (mediaEls.length !== indexedMediaEls.length) {
            this._relayout();
        }

        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    async onBuilt() {
        await this._super(...arguments);
        if (this.$target.find('.o_add_images').length) {
            await this.addImages(false);
        }
        // TODO should consider the async parts
        this._adaptNavigationIDs();
    },
    /**
     * @override
     */
    onClone() {
        this._adaptNavigationIDs();
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        this.$target.off('.gallery');
    },
    /**
     * @override
     */
    onRemove() {
        this.isBeingRemoved = true;
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Allows to select images to add as part of the snippet.
     *
     * @see this.selectClass for parameters
     */
    addImages(previewMode) {
        const $images = this.$('img');
        const $container = this.$('> .container, > .container-fluid, > .o_container_small');
        const lastImage = this._getItemsGallery().at(-1);
        let index = lastImage ? this._getIndex(lastImage) : -1;
        return new Promise(resolve => {
            let savedPromise = Promise.resolve();
            const props = {
                multiImages: true,
                onlyImages: true,
                save: images => {
                    const imagePromises = [];
                    for (const image of images) {
                        const $img = $('<img/>', {
                            class: $images.length > 0 ? $images[0].className : 'img img-fluid d-block ',
                            src: image.src,
                            'data-index': ++index,
                            alt: image.alt || '',
                            'data-name': _t('Image'),
                            style: $images.length > 0 ? $images[0].style.cssText : '',
                        }).appendTo($container);
                        const imgEl = $img[0];
                        imagePromises.push(new Promise(resolve => {
                            loadImageInfo(imgEl, this.rpc).then(() => {
                                if (imgEl.dataset.mimetype && ![
                                    "image/gif",
                                    "image/svg+xml",
                                    "image/webp",
                                ].includes(imgEl.dataset.mimetype)) {
                                    // Convert to webp but keep original width.
                                    imgEl.dataset.mimetype = "image/webp";
                                    applyModifications(imgEl, {
                                        mimetype: "image/webp",
                                    }).then(src => {
                                        imgEl.src = src;
                                        imgEl.classList.add("o_modified_image_to_save");
                                        resolve();
                                    });
                                } else {
                                    resolve();
                                }
                            });
                        }));
                    }
                    savedPromise = Promise.all(imagePromises);
                    if (images.length > 0) {
                        savedPromise = savedPromise.then(async () => {
                            await this._relayout();
                        });
                        this.trigger_up('cover_update');
                    }
                },
            };
            this.call("dialog", "add", MediaDialog, props, {
                onClose: () => {
                    savedPromise.then(resolve);
                },
            });
        });
    },
    /**
     * Allows to remove all images. Restores the snippet to the way it was when
     * it was added in the page.
     *
     * @see this.selectClass for parameters
     */
    removeAllImages(previewMode) {
        const $addImg = $('<div>', {
            class: 'alert alert-info css_non_editable_mode_hidden text-center',
        });
        const $text = $('<span>', {
            class: 'o_add_images',
            style: 'cursor: pointer;',
            text: _t(" Add Images"),
        });
        const $icon = $('<i>', {
            class: ' fa fa-plus-circle',
        });
        this._replaceContent($addImg.append($icon).append($text));
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Updates the carousel indicator after a media item (image or video) is
     * replaced.
     *
     * Synchronizes the media `data-index` provided, finds the active carousel
     * item, and updates its corresponding indicator background. Adds a play
     * icon when the media is a video.
     *
     * @param {Event} ev - Media change event
     * @param {HTMLElement} mediaEl - Updated media element.
     * @param {string} backgroundSrc - URL used as the indicator background.
     * @param {boolean} isVideo - Whether the media element is a video.
     */
    onMediaChanged(ev, mediaEl, backgroundSrc, isVideo) {
        if (ev.node) {
            mediaEl.setAttribute("data-index", ev.node.dataset.index);
        }

        const index = this.$target.find(".carousel-item.active").index();
        const $indicator = this.$(`.carousel:first li[data-bs-target]:eq(${index})`);
        if (!$indicator.length) {
            return;
        }

        if (isVideo) {
            this._addVideoPlayIcon($indicator[0]);
        } else {
            $indicator.empty().removeClass("o_not_editable");
        }
        $indicator.css("background-image", `url(${backgroundSrc})`);
    },
    /**
     * Handles image removals and image index updates.
     *
     * @override
     */
    notify(name, data) {
        this._super(...arguments);
        if (name === 'image_removed' && !this.isBeingRemoved) {
            data.$image.remove(); // Force the removal of the image before reset
            this.trigger_up('snippet_edition_request', {exec: () => {
                return this._relayout();
            }});
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Gets the thumbnail url of the given video.
     *
     * @private
     * @param {String} videoUrl the video url
     * @returns {String}
     */
    async _getVideoThumbnailUrl(videoUrl) {
        // First, check if it was not already cached.
        if (this.video_thumbnail_cache.has(videoUrl)) {
            return this.video_thumbnail_cache.get(videoUrl);
        }
        let [platform, thumbnailUrl] = await this.rpc("/website/get_video_thumbnail_url", {
            video_url: videoUrl,
        });
        if (!thumbnailUrl || platform === "instagram") {
            thumbnailUrl = "/web/static/img/placeholder.png";
        }

        this.video_thumbnail_cache.set(videoUrl, thumbnailUrl);
        return thumbnailUrl;
    },
    /**
     * Adds a play icon in the given carousel indicator element, in order to
     * show that its corresponding slide contains a video.
     *
     * @param {HTMLElement} indicatorEl the carousel indicator
     */
    _addVideoPlayIcon(indicatorEl) {
        const playIconEl = document.createElement("i");
        playIconEl.className = "fa fa-2x fa-play-circle text-white o_video_thumbnail";
        indicatorEl.append(playIconEl);
        indicatorEl.classList.add("o_not_editable"); // So the icon is not editable.
    },
    /**
     * @private
     */
    _adaptNavigationIDs() {
        const uuid = new Date().getTime();
        this.$target.find('.carousel').attr('id', 'slideshow_' + uuid);
        this.$target.find('[data-bs-slide], [data-bs-slide-to]').toArray().forEach((el) => {
            const $el = $(el);
            if ($el.attr('data-bs-target')) {
                $el.attr('data-bs-target', '#slideshow_' + uuid);
            } else if ($el.attr('href')) {
                $el.attr('href', '#slideshow_' + uuid);
            }
        });
    },
});

options.registry.gallery_img = options.Class.extend({
    /**
     * Rebuilds the whole gallery when one image is removed.
     *
     * @override
     */
    onRemove: function () {
        this.trigger_up('option_update', {
            optionName: 'GalleryImageList',
            name: 'image_removed',
            data: {
                $image: this.$target,
            },
        });
    },
});
