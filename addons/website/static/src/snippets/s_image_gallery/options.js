odoo.define('website.s_image_gallery_options', function (require) {
'use strict';

var core = require('web.core');
var weWidgets = require('wysiwyg.widgets');
var options = require('web_editor.snippets.options');
const wUtils = require("website.utils");

var _t = core._t;
var qweb = core.qweb;

options.registry.gallery = options.Class.extend({
    xmlDependencies: ['/website/static/src/snippets/s_image_gallery/000.xml'],

    /**
     * @override
     */
    start: function () {
        var self = this;
        // TODO In master: define distinct classes.
        // Differentiate both instances of this class: we want to avoid
        // registering the same event listener twice.
        this.hasAddImages = this.el.querySelector("we-button[data-add-images]");

        if (!this.hasAddImages) {
            let layoutPromise;
            const containerEl = this.$target[0].querySelector(":scope > .container, :scope > .container-fluid, :scope > .o_container_small");
            if (containerEl.querySelector(":scope > *:not(div)")) {
                layoutPromise = self._modeWithImageWait(null, self.getMode());
            } else {
                layoutPromise = Promise.resolve();
            }
            return layoutPromise.then(this._super.apply(this, arguments));
        }

        // Make sure image previews are updated if images are changed
        this.$target.on('image_changed.gallery', 'img', function (ev) {
            var $img = $(ev.currentTarget);
            var index = self.$target.find('.carousel-item.active').index();
            self.$('.carousel:first li[data-target]:eq(' + index + ')')
                .css('background-image', 'url(' + $img.attr('src') + ')');
        });

        // When the snippet is empty, an edition button is the default content
        // TODO find a nicer way to do that to have editor style
        this.$target.on('click.gallery', '.o_add_images', function (e) {
            e.stopImmediatePropagation();
            self.addImages(false);
        });

        this.$target.on('dropped.gallery', 'img', function (ev) {
            self.mode(null, self.getMode());
            if (!ev.target.height) {
                $(ev.target).one('load', function () {
                    setTimeout(function () {
                        self.trigger_up('cover_update');
                    });
                });
            }
        });

        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    onBuilt: function () {
        if (this.$target.find('.o_add_images').length) {
            this.addImages(false);
        }
        // TODO should consider the async parts
        this._adaptNavigationIDs();
    },
    /**
     * @override
     */
    onClone: function () {
        this._adaptNavigationIDs();
    },
    /**
     * @override
     */
    cleanForSave: function () {
        if (this.$target.hasClass('slideshow')) {
            this.$target.removeAttr('style');
        }
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
    addImages: function (previewMode) {
        const $images = this.$('img');
        var $container = this.$('> .container, > .container-fluid, > .o_container_small');
        var dialog = new weWidgets.MediaDialog(this, {multiImages: true, onlyImages: true, mediaWidth: 1920});
        var lastImage = _.last(this._getImages());
        var index = lastImage ? this._getIndex(lastImage) : -1;
        return new Promise(resolve => {
            let savedPromise = Promise.resolve();
            dialog.on('save', this, function (attachments) {
                for (var i = 0; i < attachments.length; i++) {
                    $('<img/>', {
                        class: $images.length > 0 ? $images[0].className : 'img img-fluid d-block ',
                        src: attachments[i].image_src,
                        'data-index': ++index,
                        alt: attachments[i].description || '',
                        'data-name': _t('Image'),
                        style: $images.length > 0 ? $images[0].style.cssText : '',
                    }).appendTo($container);
                }
                if (attachments.length > 0) {
                    savedPromise = this._modeWithImageWait('reset', this.getMode()).then(() => {
                        this.trigger_up('cover_update');
                    });
                }
            });
            dialog.on('closed', this, () => savedPromise.then(resolve));
            dialog.open();
        });
    },
    /**
     * Allows to change the number of columns when displaying images with a
     * grid-like layout.
     *
     * @see this.selectClass for parameters
     */
    columns: function (previewMode, widgetValue, params) {
        const nbColumns = parseInt(widgetValue || '1');
        this.$target.attr('data-columns', nbColumns);

        // TODO In master return mode's result.
        this.mode(previewMode, this.getMode(), {}); // TODO improve
    },
    /**
     * Get the image target's layout mode (slideshow, masonry, grid or nomode).
     *
     * @returns {String('slideshow'|'masonry'|'grid'|'nomode')}
     */
    getMode: function () {
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
     */
    grid: function () {
        const imgs = this._getImgHolderEls();
        var $row = $('<div/>', {class: 'row s_nb_column_fixed'});
        var columns = this._getColumns();
        var colClass = 'col-lg-' + (12 / columns);
        var $container = this._replaceContent($row);

        _.each(imgs, function (img, index) {
            var $img = $(img);
            var $col = $('<div/>', {class: colClass});
            $col.append($img).appendTo($row);
            if ((index + 1) % columns === 0) {
                $row = $('<div/>', {class: 'row s_nb_column_fixed'});
                $row.appendTo($container);
            }
        });
        this.$target.css('height', '');
    },
    /**
     * Displays the images with the "masonry" layout.
     */
    masonry: function () {
        var self = this;
        const imgs = this._getImgHolderEls();
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

        // Dispatch images in columns by always putting the next one in the
        // smallest-height column
        if (this._masonryAwaitImages) {
            // TODO In master return promise.
            this._masonryAwaitImagesPromise = new Promise(async resolve => {
                for (const imgEl of imgs) {
                    let min = Infinity;
                    let smallestColEl;
                    for (const colEl of cols) {
                        const imgEls = colEl.querySelectorAll("img");
                        const lastImgRect = imgEls.length && imgEls[imgEls.length - 1].getBoundingClientRect();
                        const height = lastImgRect ? Math.round(lastImgRect.top + lastImgRect.height) : 0;
                        if (height < min) {
                            min = height;
                            smallestColEl = colEl;
                        }
                    }
                    smallestColEl.append(imgEl);
                    await wUtils.onceAllImagesLoaded(this.$target);
                }
                resolve();
            });
            return;
        }
        // TODO Remove in master.
        // Order might be wrong if images were not loaded yet.
        while (imgs.length) {
            var min = Infinity;
            var $lowest;
            _.each(cols, function (col) {
                var $col = $(col);
                var height = $col.is(':empty') ? 0 : $col.find('img').last().offset().top + $col.find('img').last().height() - self.$target.offset().top;
                // Neutralize invisible sub-pixel height differences.
                height = Math.round(height);
                if (height < min) {
                    min = height;
                    $lowest = $col;
                }
            });
            $lowest.append(imgs.shift());
        }
    },
    /**
     * Allows to change the images layout. @see grid, masonry, nomode, slideshow
     *
     * @see this.selectClass for parameters
     */
    mode: function (previewMode, widgetValue, params) {
        widgetValue = widgetValue || 'slideshow'; // FIXME should not be needed
        this.$target.css('height', '');
        this.$target
            .removeClass('o_nomode o_masonry o_grid o_slideshow')
            .addClass('o_' + widgetValue);
        this[widgetValue]();
        this.trigger_up('cover_update');
        this._refreshPublicWidgets();
    },
    /**
     * Displays the images with the standard layout: floating images.
     */
    nomode: function () {
        var $row = $('<div/>', {class: 'row s_nb_column_fixed'});
        var imgs = this._getImages();
        const imgHolderEls = this._getImgHolderEls();

        this._replaceContent($row);

        _.each(imgs, function (img, index) {
            var wrapClass = 'col-lg-3';
            if (img.width >= img.height * 2 || img.width > 600) {
                wrapClass = 'col-lg-6';
            }
            var $wrap = $('<div/>', {class: wrapClass}).append(imgHolderEls[index]);
            $row.append($wrap);
        });
    },
    /**
     * Allows to remove all images. Restores the snippet to the way it was when
     * it was added in the page.
     *
     * @see this.selectClass for parameters
     */
    removeAllImages: function (previewMode) {
        var $addImg = $('<div>', {
            class: 'alert alert-info css_non_editable_mode_hidden text-center',
        });
        var $text = $('<span>', {
            class: 'o_add_images',
            style: 'cursor: pointer;',
            text: _t(" Add Images"),
        });
        var $icon = $('<i>', {
            class: ' fa fa-plus-circle',
        });
        this._replaceContent($addImg.append($icon).append($text));
    },
    /**
     * Displays the images with a "slideshow" layout.
     */
    slideshow: function () {
        const imageEls = this._getImages();
        const imgHolderEls = this._getImgHolderEls();
        const images = _.map(imageEls, img => ({
            // Use getAttribute to get the attribute value otherwise .src
            // returns the absolute url.
            src: img.getAttribute('src'),
            // TODO: remove me in master. This is not needed anymore as the
            // images of the rendered `website.gallery.slideshow` are replaced
            // by the elements of `imgHolderEls`.
            alt: img.getAttribute('alt'),
        }));
        var currentInterval = this.$target.find('.carousel:first').attr('data-interval');
        var params = {
            images: images,
            index: 0,
            title: "",
            interval: currentInterval || 0,
            id: 'slideshow_' + new Date().getTime(),
            // TODO: in master, remove `attrClass` and `attStyle` from `params`.
            // This is not needed anymore as the images of the rendered
            // `website.gallery.slideshow` are replaced by the elements of
            // `imgHolderEls`.
            attrClass: imageEls.length > 0 ? imageEls[0].className : '',
            attrStyle: imageEls.length > 0 ? imageEls[0].style.cssText : '',
        },
        $slideshow = $(qweb.render('website.gallery.slideshow', params));
        const imgSlideshowEls = $slideshow[0].querySelectorAll("img[data-o-main-image]");
        imgSlideshowEls.forEach((imgSlideshowEl, index) => {
            // Replace the template image by the original one. This is needed in
            // order to keep the characteristics of the image such as the
            // filter, the width, the quality, the link on which the users are
            // redirected once they click on the image etc...
            imgSlideshowEl.after(imgHolderEls[index]);
            imgSlideshowEl.remove();
        });
        this._replaceContent($slideshow);
        _.each(this.$('img'), function (img, index) {
            $(img).attr({contenteditable: true, 'data-index': index});
        });
        this.$target.css('height', Math.round(window.innerHeight * 0.7));

        // Apply layout animation
        this.$target.off('slide.bs.carousel').off('slid.bs.carousel');
        this.$('li.fa').off('click');
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Handles image removals and image index updates.
     *
     * @override
     */
    notify: function (name, data) {
        this._super(...arguments);
        // TODO Remove in master.
        if (!this.hasAddImages) {
            // In stable, the widget is instanciated twice. We do not want
            // operations, especially moves, to be performed twice.
            // We therefore ignore the requests from one of the instances.
            return;
        }
        // TODO In master: nest in a snippet_edition_request to await mode.
        if (name === 'image_removed') {
            data.$image.remove(); // Force the removal of the image before reset
            // TODO In 16.0: use _modeWithImageWait.
            this.mode('reset', this.getMode());
        } else if (name === 'image_index_request') {
            var imgs = this._getImages();
            var position = _.indexOf(imgs, data.$image[0]);
            if (position === 0 && data.position === "prev") {
                data.position = "last";
            } else if (position === imgs.length - 1 && data.position === "next") {
                data.position = "first";
            }
            imgs.splice(position, 1);
            switch (data.position) {
                case 'first':
                    imgs.unshift(data.$image[0]);
                    break;
                case 'prev':
                    imgs.splice(position - 1, 0, data.$image[0]);
                    break;
                case 'next':
                    imgs.splice(position + 1, 0, data.$image[0]);
                    break;
                case 'last':
                    imgs.push(data.$image[0]);
                    break;
            }
            position = imgs.indexOf(data.$image[0]);
            _.each(imgs, function (img, index) {
                // Note: there might be more efficient ways to do that but it is
                // more simple this way and allows compatibility with 10.0 where
                // indexes were not the same as positions.
                $(img).attr('data-index', index);
            });
            const currentMode = this.getMode();
            // TODO In 16.0: use _modeWithImageWait.
            this.mode('reset', currentMode);
            if (currentMode === 'slideshow') {
                const $carousel = this.$target.find('.carousel');
                $carousel.removeClass('slide');
                $carousel.carousel(position);
                this.$target.find('.carousel-indicators li').removeClass('active');
                this.$target.find('.carousel-indicators li[data-slide-to="' + position + '"]').addClass('active');
                this.trigger_up('activate_snippet', {
                    $snippet: this.$target.find('.carousel-item.active img'),
                    ifInactiveOptions: true,
                });
                $carousel.addClass('slide');
            } else {
                this.trigger_up('activate_snippet', {
                    $snippet: data.$image,
                    ifInactiveOptions: true,
                });
            }
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _adaptNavigationIDs: function () {
        var uuid = new Date().getTime();
        this.$target.find('.carousel').attr('id', 'slideshow_' + uuid);
        _.each(this.$target.find('[data-slide], [data-slide-to]'), function (el) {
            var $el = $(el);
            if ($el.attr('data-target')) {
                $el.attr('data-target', '#slideshow_' + uuid);
            } else if ($el.attr('href')) {
                $el.attr('href', '#slideshow_' + uuid);
            }
        });
    },
    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
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
    /**
     * Returns the images, sorted by index.
     *
     * @private
     * @returns {DOMElement[]}
     */
    _getImages: function () {
        var imgs = this.$('img').get();
        var self = this;
        imgs.sort(function (a, b) {
            return self._getIndex(a) - self._getIndex(b);
        });
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
        const imgEls = this._getImages();
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
     * Call mode while ensuring that all images are loaded.
     *
     * @see this.selectClass for parameters
     * @returns {Promise}
     */
    _modeWithImageWait(previewMode, widgetValue, params) {
        // TODO Remove in master.
        let promise;
        this._masonryAwaitImages = true;
        try {
            this.mode(previewMode, widgetValue, params);
            promise = this._masonryAwaitImagesPromise;
        } finally {
            this._masonryAwaitImages = false;
            this._masonryAwaitImagesPromise = undefined;
        }
        return promise || Promise.resolve();
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
            optionName: 'gallery',
            name: 'image_removed',
            data: {
                $image: this.$target,
            },
        });
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Allows to change the position of an image (its order in the image set).
     *
     * @see this.selectClass for parameters
     */
    position: function (previewMode, widgetValue, params) {
        this.trigger_up('option_update', {
            optionName: 'gallery',
            name: 'image_index_request',
            data: {
                $image: this.$target,
                position: widgetValue,
            },
        });
    },
});
});
