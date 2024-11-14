import { MediaDialog } from "@web_editor/components/media_dialog/media_dialog";
import options from "@web_editor/js/editor/snippets.options";
import wUtils from '@website/js/utils';
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import {
    loadImageInfo,
    applyModifications,
} from "@web_editor/js/editor/image_processing";
import * as gridUtils from "@web_editor/js/common/grid_layout_utils";
import * as masonryUtils from "@web_editor/js/common/masonry_layout_utils";

/**
 * This class provides layout methods for interacting with the ImageGallery
 * snippet. It is used by all options that need the layout to be recomputed.
 * This is typically the case when adding/removing/moving images, changing the
 * layout mode and changing the number of columns.
 */
options.registry.GalleryLayout = options.registry.CarouselHandler.extend({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async notify(name) {
        if (name === "change_container_width") {
            const mode = this._getMode();
            const relayoutRequiredModes = ["grid", "masonry"];
            if (relayoutRequiredModes.includes(mode)) {
                await this._relayout();
            }
        } else {
            this._super(...arguments);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Get the image target's layout mode (slideshow, masonry, grid or col).
     *
     * @private
     * @returns {String('slideshow'|'masonry'|'grid'|'col')}
     */
    _getMode() {
        var mode = 'slideshow';
        if (this.$target.hasClass('o_masonry')) {
            mode = 'masonry';
        }
        if (this.$target.hasClass('o_grid')) {
            mode = 'grid';
        }
        if (this.$target[0].classList.contains("o_col")) {
            mode = "col";
        }
        return mode;
    },
    /**
     * Displays the images with the "grid" layout.
     *
     * @private
     */
    async _grid() {
        const imgs = this._getImgHolderEls();
        const columnCount = this._getColumns();
        const mobileColumnCount = this._getMobileColumns();
        const rowEl = document.createElement("div");
        rowEl.classList.add("row", "s_nb_column_fixed");
        const $container = this._replaceContent($(rowEl));
        imgs.forEach((imgEl) => {
            const imgContainerEl = document.createElement("div");
            imgContainerEl.classList.add(
                `col-${12 / mobileColumnCount}`,
                `col-lg-${12 / columnCount}`
            );
            rowEl.appendChild(imgContainerEl);
            const clonedImgEl = imgEl.cloneNode(true);
            imgContainerEl.appendChild(clonedImgEl);
        });
        // Wait for images to load to ensure grid areas are properly calculated.
        await wUtils.onceAllImagesLoaded($container);
        gridUtils._toggleGridMode($container[0]);
        this.$target.css('height', '');
    },
    /**
     * Displays the images with the "masonry" layout.
     *
     * @private
     * @returns {Promise}
     */
    _masonry() {
        const imgs = this._getImgHolderEls();

        // Create initial row structure
        const rowEl = document.createElement("div");
        rowEl.classList.add("row", "s_nb_column_fixed");
        const $container = this._replaceContent($(rowEl));

        // Add images to container
        imgs.forEach((imgEl) => {
            const clonedImgEl = imgEl.cloneNode(true);
            rowEl.appendChild(clonedImgEl);
        });

        return masonryUtils.toggleMasonryMode($container[0]);
    },
    /**
     * Displays the images with the "column" layout.
     *
     * @private
     * @returns {Promise}
     */
    _col() {
        const imgEls = this._getImgHolderEls();
        const columnCount = this._getColumns();
        const mobileColumnCount = this._getMobileColumns();

        // Create initial row structure
        const rowEl = document.createElement("div");
        rowEl.classList.add("row", "s_nb_column_fixed", "o_col_mode");
        this._replaceContent($(rowEl));

        // Add images to container
        imgEls.forEach((imgEl) => {
            const imgContainerEl = document.createElement("div");
            imgContainerEl.classList.add(
                "o_col_col",
                `col-${12 / mobileColumnCount}`,
                `col-lg-${12 / columnCount}`
            );
            rowEl.appendChild(imgContainerEl);
            const clonedImgEl = imgEl.cloneNode(true);
            imgContainerEl.appendChild(clonedImgEl);
        });
    },
    /**
     * Allows to change the images layout. @see grid, masonry, col, slideshow
     *
     * @private
     * @param {string} modeName
     * @returns {Promise}
     */
    async _setMode(modeName) {
        modeName = modeName || 'slideshow'; // FIXME should not be needed
        this.$target.css('height', '');
        this.$target[0].classList.remove("o_masonry", "o_grid", "o_col", "o_slideshow");
        this.$target[0].classList.add("o_" + modeName);
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
     * Displays the images with a "slideshow" layout.
     *
     * @private
     */
    _slideshow() {
        const imageEls = this._getItemsGallery();
        const imgHolderEls = this._getImgHolderEls();
        var currentInterval = this.$target.find('.carousel:first').attr('data-bs-interval');
        let params = {
            images: imageEls,
            index: 0,
            interval: currentInterval || 0,
            ride: !currentInterval ? "false" : "carousel",
            id: 'slideshow_' + new Date().getTime(),
            hideImage: true,
        };
        // Since there is no versioning for this snippet we use the last version
        // of "website.gallery.slideshow" called "website.s_image_gallery_mirror"
        if (this.$target[0].dataset.vcss === '002') {
            let carouselEl = this.$target[0].querySelector('.carousel');
            params.colorContrast  = carouselEl && carouselEl.classList.contains('carousel-dark') ? 'carousel-dark' : ' ';
        }
        let $slideshow = $(renderToElement('website.s_image_gallery_mirror', params));
        const carouselItemEls = $slideshow[0].querySelectorAll(".carousel-item");
        carouselItemEls.forEach((carouselItemEl, index) => {
            // Add the images in the carousel items.
            carouselItemEl.appendChild(imgHolderEls[index]);
        });
        this._replaceContent($slideshow);
        this.$("img").toArray().forEach((img, index) => {
            $(img).attr({contenteditable: true, 'data-index': index});
        });
        this.$target.css('height', Math.round(window.innerHeight * 0.7));

        // Apply layout animation
        this.$target.off('slide.bs.carousel').off('slid.bs.carousel');
        this._slideshowStart();
        this.$('li.fa').off('click');
    },
    /**
     * @override
     */
    _getItemsGallery() {
        const imgs = this.$('img').get();
        imgs.sort((a, b) => this._getIndex(a) - this._getIndex(b));
        return imgs;
    },
    /**
     * Returns the images, or the images holder if this holder is an anchor,
     * sorted by index.
     *
     * @private
     * @returns {Array.<HTMLImageElement|HTMLAnchorElement>}
     */
    _getImgHolderEls: function () {
        const imgEls = this._getItemsGallery();
        return imgEls.map(imgEl => imgEl.closest("a") || imgEl);
    },
    /**
     * Returns the index associated to a given image.
     *
     * @private
     * @param {DOMElement} img
     * @returns {integer}
     */
    _getIndex: function (img) {
        return img.dataset.index || 0;
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
     * Returns the currently selected mobile column option.
     *
     * @private
     * @returns {integer}
     */
    _getMobileColumns: function () {
        return parseInt(this.$target[0].dataset.mobileColumns) || 1;
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
            this.trigger_up("is_element_selected", {
                el: activeImageEl,
                callback: () => {
                    _previousEditor = true;
                },
            });
            this.trigger_up("hide_overlay");
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
     * Allows to change the number of columns on mobile when displaying
     * images in different layout.
     *
     * @see this.selectClass for parameters
     */
    mobileColumns(previewMode, widgetValue, params) {
        const nbColumns = parseInt(widgetValue || "1");
        this.$target[0].setAttribute("data-mobile-columns", nbColumns);

        return this._relayout();
    },
    /**
     * Allows to change the images layout. @see grid, masonry, col, slideshow
     *
     * @see this.selectClass for parameters
     */
    mode(previewMode, widgetValue, params) {
        // Set the mode during preview only if it differs from the current mode
        // to avoid redundant calls.
        if (previewMode && widgetValue !== this._getMode()) {
            return this._setMode(widgetValue);
        }
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
            case "mobileColumns": {
                return `${this._getMobileColumns()}`;
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
    start() {
        // Make sure image previews are updated if images are changed
        this.$target.on('image_changed.gallery', 'img', ev => {
            const $img = $(ev.currentTarget);
            const index = this.$target.find('.carousel-item.active').index();
            this.$('.carousel:first li[data-bs-target]:eq(' + index + ')')
                .css('background-image', 'url(' + $img.attr('src') + ')');
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
                            class: $images.length > 0 ? $images[0].className : 'img img-fluid d-block mh-100 mw-100 mx-auto rounded object-fit-cover',
                            src: image.src,
                            'data-index': ++index,
                            alt: image.alt || '',
                            'data-name': _t('Image'),
                            style: $images.length > 0 ? $images[0].style.cssText : '',
                        }).appendTo($container);
                        const imgEl = $img[0];
                        imagePromises.push(new Promise(resolve => {
                            loadImageInfo(imgEl).then(() => {
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
     * Handles image removals and image index updates.
     *
     * @override
     */
    notify(name, data) {
        this._super(...arguments);
        if (name === 'image_removed') {
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
