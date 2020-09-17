odoo.define('website.s_image_gallery_options', function (require) {
'use strict';

var core = require('web.core');
var weWidgets = require('wysiwyg.widgets');
var snippetOptions = require('web_editor.snippets.options');

var _t = core._t;
var qweb = core.qweb;

snippetOptions.registry.gallery = snippetOptions.SnippetOptionWidget.extend({
    xmlDependencies: ['/website/static/src/snippets/s_image_gallery/000.xml'],

    /**
     * @override
     */
    start: async function () {
        const _super = this._super;

        this._images = this.$('img').get();

        const galleryStart = async (context) => {
            // The snippet should not be editable
            await this.editorHelpers.addClass(context, this.$target[0], 'o_fake_not_editable');
            await this.editorHelpers.setAttribute(context, this.$target[0], 'contentEditable', 'false');

            // Make sure image previews are updated if images are changed
            this.$target.on('save', 'img', async (ev) => {
                var $img = $(ev.currentTarget);
                var index = this.$target.find('.carousel-item.active').index();
                const $li = this.$('.carousel:first li[data-target]:eq(' + index + ')');
                await this.editorHelpers.setStyle(context, $li[0], 'background-image', 'url(' + $img.attr('src') + ')');
            });

            // When the snippet is empty, an edition button is the default content
            // TODO find a nicer way to do that to have editor style
            this.$target.on('click', '.o_add_images', (e) => {
                e.stopImmediatePropagation();
                this.addImages(false);
            });

            this.$target.on('dropped', 'img', (ev) => {
                this._setMode(null, this.getMode());
                if (!ev.target.height) {
                    $(ev.target).one('load', function () {
                        setTimeout(function () {
                            this.trigger_up('cover_update');
                        });
                    });
                }
            });

            if (!this.$('> div:first-child img').length) {
                // reset the images to show the "Add images" button.
                this.removeAllImages()
            }
        };
        await this.wysiwyg.editor.execCommand(galleryStart);

        const $container = this.$('> .container, > .container-fluid, > .o_container_small');
        if ($container.find('> *:not(div)').length) {
            this._setMode(null, this.getMode());
        }

        return _super.apply(this, arguments);
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

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Allows to select images to add as part of the snippet.
     *
     * @see this.selectClass for parameters
     */
    addImages: async function (previewMode) {
        const $images = this.$('img');
        var $container = this.$('> .container, > .container-fluid, > .o_container_small');
        var dialog = new weWidgets.MediaDialog(this, {multiImages: true, onlyImages: true, mediaWidth: 1920});
        var lastImage = _.last(this._getImages());
        var index = lastImage ? this._getIndex(lastImage) : -1;
        await new Promise(resolve => {
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
                    this._setMode('reset', this.getMode());
                    this.trigger_up('cover_update');
                }
            });
            dialog.on('closed', this, () => resolve());
            dialog.open();
        });
        await this._refreshTarget();
    },
    /**
     * Allows to change the number of columns when displaying images with a
     * grid-like layout.
     *
     * @see this.selectClass for parameters
     */
    columns: async function (previewMode, widgetValue, params) {
        const nbColumns = parseInt(widgetValue || '1');
        this.$target.attr('data-columns', nbColumns);

        await this.mode(previewMode, this.getMode(), {}); // TODO improve
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
    grid: async function (previewMode, widgetValue, params) {
        var imgs = this._getImages();
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
        if (previewMode === false) await this._refreshTarget();
    },
    /**
     * Displays the images with the "masonry" layout.
     */
    masonry: async function (previewMode, widgetValue, params) {
        var self = this;
        var imgs = this._getImages();
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
        while (imgs.length) {
            var min = Infinity;
            var $lowest;
            _.each(cols, function (col) {
                var $col = $(col);
                var height = $col.is(':empty') ? 0 : $col.find('img').last().offset().top + $col.find('img').last().height() - self.$target.offset().top;
                if (height < min) {
                    min = height;
                    $lowest = $col;
                }
            });
            $lowest.append(imgs.shift());
        }
        if (previewMode === false) await this._refreshTarget();
    },
    /**
     * Allows to change the images layout. @see grid, masonry, nomode, slideshow
     *
     * @see this.selectClass for parameters
     */
    mode: async function (previewMode, widgetValue, params) {
        this._setMode(previewMode, widgetValue, params);
        if (previewMode === false) await this._refreshTarget();
    },
    /**
     * Displays the images with the standard layout: floating images.
     */
    nomode: async function (previewMode, widgetValue, params) {
        var $row = $('<div/>', {class: 'row s_nb_column_fixed'});
        var imgs = this._getImages();


        _.each(imgs, function (img) {
            var wrapClass = 'col-lg-3';
            if (img.width >= img.height * 2 || img.width > 600) {
                wrapClass = 'col-lg-6';
            }
            var $wrap = $('<div/>', {class: wrapClass}).append(img);
            $row.append($wrap);
        });

        this._replaceContent($row);
        if (previewMode === false) await this._refreshTarget();
    },
    /**
     * Allows to remove all images. Restores the snippet to the way it was when
     * it was added in the page.
     *
     * @see this.selectClass for parameters
     */
    removeAllImages: async function () {
        this._images = [];
        const $addImg = $('<div>', {
            class: 'alert alert-info css_editable_mode_display text-center',
        });
        const $text = $('<span>', {
            class: 'o_add_images',
            style: 'cursor: pointer;',
            text: _t(" Add Images"),
        });
        const $icon = $('<i>', {
            class: ' fa fa-plus-circle',
        });
        this._replaceContent($addImg.append($icon).append($text), false);
        await this._refreshTarget();
    },
    /**
     * Displays the images with a "slideshow" layout.
     */
    slideshow: async function (previewMode, widgetValue, params) {
        const imageEls = this._getImages();
        const images = _.map(imageEls, img => ({
            // Use getAttribute to get the attribute value otherwise .src
            // returns the absolute url.
            src: img.getAttribute('src'),
            alt: img.getAttribute('alt'),
        }));
        var currentInterval = this.$target.find('.carousel:first').attr('data-interval');
        var params = {
            images: images,
            index: 0,
            title: "",
            interval: currentInterval || 0,
            id: 'slideshow_' + new Date().getTime(),
            attrClass: imageEls.length > 0 ? imageEls[0].className : '',
            attrStyle: imageEls.length > 0 ? imageEls[0].style.cssText : '',
        },
        $slideshow = $(qweb.render('website.gallery.slideshow', params));
        this._replaceContent($slideshow);
        _.each(this.$('img'), function (img, index) {
            $(img).attr({contenteditable: true, 'data-index': index});
        });
        this.$target.css('height', Math.round(window.innerHeight * 0.7));

        // Apply layout animation
        this.$target.off('slide.bs.carousel').off('slid.bs.carousel');
        this.$('li.fa').off('click');

        if (previewMode === false) await this._refreshTarget();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Handles image removals and image index updates.
     *
     * @override
     */
    notify: async function (name, data) {
        this._super(...arguments);
        if (name === 'image_removed') {
            data.$image.remove(); // Force the removal of the image before reset
            await this.mode('reset', this.getMode());
        } else if (name === 'image_index_request') {
            const images = this._getImages(this.$('img').get());
            let position = _.indexOf(images, data.$image[0]);
            images.splice(position, 1);
            switch (data.position) {
                case 'first':
                    images.unshift(data.$image[0]);
                    break;
                case 'prev':
                    images.splice(position - 1, 0, data.$image[0]);
                    break;
                case 'next':
                    images.splice(position + 1, 0, data.$image[0]);
                    break;
                case 'last':
                    images.push(data.$image[0]);
                    break;
            }
            position = images.indexOf(data.$image[0]);
            _.each(images, function (img, index) {
                // Note: there might be more efficient ways to do that but it is
                // more simple this way and allows compatibility with 10.0 where
                // indexes were not the same as positions.
                $(img).attr('data-index', index);
            });
            const currentMode = this.getMode();
            this._setMode('reset', currentMode);
            if (currentMode === 'slideshow') {
                const $carousel = this.$target.find('.carousel');
                $carousel.removeClass('slide');
                $carousel.carousel(position);
                this.$target.find('.carousel-indicators li').removeClass('active');
                this.$target.find('.carousel-indicators li[data-slide-to="' + position + '"]').addClass('active');
                this.trigger_up('activate_snippet', {
                    $element: this.$target.find('.carousel-item.active img'),
                    ifInactiveOptions: true,
                });
                $carousel.addClass('slide');
            } else {
                this.trigger_up('activate_snippet', {
                    $element: data.$image,
                    ifInactiveOptions: true,
                });
            }
            await this._refreshTarget();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------


    /**
     * Allows to change the images layout. @see grid, masonry, nomode, slideshow
     *
     * @private
     * @see this.selectClass for parameters
     */
    _setMode: async function (previewMode, widgetValue, params) {
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
    _getImages: function (imgs) {
        var imgs = this.$('img').get();
        var self = this;
        imgs.sort(function (a, b) {
            return self._getIndex(a) - self._getIndex(b);
        });
        return imgs;
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
    _replaceContent: function ($content, inEditor = true) {
        var $container = this.$('> .container, > .container-fluid, > .o_container_small');
        $container.empty().append($content);
        return $container;
    },
});

snippetOptions.registry.gallery_img = snippetOptions.SnippetOptionWidget.extend({
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
