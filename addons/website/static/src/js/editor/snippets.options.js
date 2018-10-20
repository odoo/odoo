odoo.define('website.snippets.options', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var widgets = require('web_editor.widget');
var options = require('web_editor.snippets.options');

var _t = core._t;
var qweb = core.qweb;

options.registry.menu_data = options.Class.extend({
    xmlDependencies: ['/website/static/src/xml/website.editor.xml'],

    /**
     * When the users selects a menu, a dialog is opened to ask him if he wants
     * to follow the link (and leave editor), edit the menu or do nothing.
     *
     * @override
     */
    onFocus: function () {
        var self = this;
        (new Dialog(this, {
            title: _t("Confirmation"),
            $content: $(core.qweb.render('website.leaving_current_page_edition')),
            buttons: [
                {text: _t("Go to Link"), classes: 'btn-primary', click: function () {
                    self.trigger_up('request_save', {
                        reload: false,
                        onSuccess: function () {
                            window.location.href = self.$target.attr('href');
                        },
                    });
                }},
                {text: _t("Edit the menu"), classes: 'btn-primary', click: function () {
                    this.trigger_up('action_demand', {
                        actionName: 'edit_menu',
                        params: [
                            function () {
                                var def = $.Deferred();
                                self.trigger_up('request_save', {
                                    onSuccess: def.resolve.bind(def),
                                    onFailure: def.reject.bind(def),
                                });
                                return def;
                            },
                        ],
                    });
                }},
                {text: _t("Stay on this page"), close: true}
            ]
        })).open();
    },
});

options.registry.company_data = options.Class.extend({
    /**
     * Fetches data to determine the URL where the user can edit its company
     * data. Saves the info in the prototype to do this only once.
     *
     * @override
     */
    start: function () {
        var proto = options.registry.company_data.prototype;
        var def;
        var self = this;
        if (proto.__link === undefined) {
            def = this._rpc({route: '/web/session/get_session_info'}).then(function (session) {
                return self._rpc({
                    model: 'res.users',
                    method: 'read',
                    args: [session.uid, ['company_id']],
                });
            }).then(function (res) {
                proto.__link = '/web#action=base.action_res_company_form&view_type=form&id=' + (res && res[0] && res[0].company_id[0] || 1);
            });
        }
        return $.when(this._super.apply(this, arguments), def);
    },
    /**
     * When the users selects company data, opens a dialog to ask him if he
     * wants to be redirected to the company form view to edit it.
     *
     * @override
     */
    onFocus: function () {
        var self = this;
        var proto = options.registry.company_data.prototype;

        Dialog.confirm(this, _t("Do you want to edit the company data ?"), {
            confirm_callback: function () {
                self.trigger_up('request_save', {
                    reload: false,
                    onSuccess: function () {
                        window.location.href = proto.__link;
                    },
                });
            },
        });
    },
});

/**
 * @todo should be refactored / reviewed
 */
options.registry.carousel = options.Class.extend({
    /**
     * @override
     */
    start: function () {
        var self = this;

        this.$target.carousel({interval: false});
        this.id = this.$target.attr('id');
        this.$inner = this.$target.find('.carousel-inner');
        this.$indicators = this.$target.find('.carousel-indicators');
        this.$target.carousel('pause');
        this._rebindEvents();

        var def = this._super.apply(this, arguments);

        // set background and prepare to clean for save
        this.$target.on('slid.bs.carousel', function () {
            self.$target.carousel('pause');
            self.trigger_up('option_update', {
                optionNames: ['background', 'background_position', 'colorpicker'],
                name: 'target',
                data: self.$target.find('.item.active'),
            });
        });
        this.$target.trigger('slid.bs.carousel');

        return def;
    },
    /**
     * Associates unique ID on slider elements.
     *
     * @override
     */
    onBuilt: function () {
        this.id = 'myCarousel' + new Date().getTime();
        this.$target.attr('id', this.id);
        this.$target.find('[data-slide]').attr('data-cke-saved-href', '#' + this.id);
        this.$target.find('[data-target]').attr('data-target', '#' + this.id);
        this._rebindEvents();
    },
    /**
     * Associates unique ID on cloned slider elements.
     *
     * @override
     */
    onClone: function () {
        var id = 'myCarousel' + new Date().getTime();
        this.$target.attr('id', id);
        this.$target.find('[data-slide]').attr('href', '#' + id);
        this.$target.find('[data-slide-to]').attr('data-target', '#' + id);
    },
    /**
     * @override
     */
    cleanForSave: function () {
        this._super.apply(this, arguments);
        this.$target.find('.item').removeClass('next prev left right active')
            .first().addClass('active');
        this.$target.find('.carousel-indicators').find('li').removeClass('active')
            .first().addClass('active');
        this.$target.removeClass('oe_img_bg ' + this._class).css('background-image', '');
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Adds a slide.
     *
     * @see this.selectClass for parameters
     */
    addSlide: function (previewMode) {
        var self = this;
        var cycle = this.$inner.find('.item').length;
        var $active = this.$inner.find('.item.active, .item.prev, .item.next').first();
        var index = $active.index();
        this.$('.carousel-control, .carousel-indicators').removeClass('hidden');
        this.$indicators.append('<li data-target="#' + this.id + '" data-slide-to="' + cycle + '"></li>');
        var $clone = this.$('.item:first').clone(true);
        $clone.removeClass('active').insertAfter($active);
        _.defer(function () {
            self.$target.carousel().carousel(++index);
            self._rebindEvents();
        });
    },
    /**
     * Removes the current slide.
     *
     * @see this.selectClass for parameters.
     */
    removeSlide: function (previewMode) {
        if (this.remove_process) {
            return;
        }

        var self = this;

        var $items = this.$inner.find('.item');
        var cycle = $items.length - 1;
        var $active = $items.filter('.active');
        var index = $active.index();

        if (cycle > 0) {
            this.remove_process = true;
            this.$target.on('slid.bs.carousel.slide_removal', function (event) {
                $active.remove();
                self.$indicators.find('li:last').remove();
                self.$target.off('slid.bs.carousel.slide_removal');
                self._rebindEvents();
                self.remove_process = false;
                if (cycle === 1) {
                    self.$target.find('.carousel-control, .carousel-indicators').addClass('hidden');
                }
            });
            _.defer(function () {
                self.$target.carousel(index > 0 ? --index : cycle);
            });
        }
    },
    /**
     * Changes the interval for autoplay.
     *
     * @see this.selectClass for parameters
     */
    interval: function (previewMode, value) {
        this.$target.attr('data-interval', value);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _setActive: function () {
        this._super.apply(this, arguments);
        this.$el.find('[data-interval]').removeClass('active')
            .filter('[data-interval=' + this.$target.attr('data-interval') + ']').addClass('active');
    },
    /**
     * Rebinds carousel events on indicators.
     *
     * @private
     */
    _rebindEvents: function () {
        var self = this;
        this.$target.find('.carousel-control').off('click').on('click', function () {
            self.$target.carousel($(this).data('slide'));
        });
        this.$target.find('.carousel-indicators [data-slide-to]').off('click').on('click', function () {
            self.$target.carousel(+$(this).data('slide-to'));
        });

        /* Fix: backward compatibility saas-3 */
        this.$target.find('.item.text_image, .item.image_text, .item.text_only').find('.container > .carousel-caption > div, .container > img.carousel-image').attr('contentEditable', 'true');
    },
});

options.registry['margin-x'] = options.registry.marginAndResize.extend({
    preventChildPropagation: true,

    /**
     * @override
     */
    onClone: function (options) {
        this._super.apply(this, arguments);
        // Below condition is added to remove offset of target element only
        // and not its children to avoid design alteration of a container/block.
        if (options.isCurrent) {
            var _class = this.$target.attr('class').replace(/\s*(col-lg-offset-|col-md-offset-)([0-9-]+)/g, '');
            this.$target.attr('class', _class);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getSize: function () {
        this.grid = this._super();
        var width = this.$target.parents('.row:first').first().outerWidth();

        var grid = [1,2,3,4,5,6,7,8,9,10,11,12];
        this.grid.e = [_.map(grid, function (v) {return 'col-md-'+v;}), _.map(grid, function (v) {return width/12*v;})];

        grid = [-12,-11,-10,-9,-8,-7,-6,-5,-4,-3,-2,-1,0,1,2,3,4,5,6,7,8,9,10,11];
        this.grid.w = [_.map(grid, function (v) {return 'col-md-offset-'+v;}), _.map(grid, function (v) {return width/12*v;}), 12];

        return this.grid;
    },
    /**
     * @override
     */
    _onResize: function (compass, beginClass, current) {
        if (compass === 'w') {
            // don't change the right border position when we change the offset (replace col size)
            var beginCol = Number(beginClass.match(/col-md-([0-9]+)|$/)[1] || 0);
            var beginOffset = Number(beginClass.match(/col-md-offset-([0-9-]+)|$/)[1] || beginClass.match(/col-lg-offset-([0-9-]+)|$/)[1] || 0);
            var offset = Number(this.grid.w[0][current].match(/col-md-offset-([0-9-]+)|$/)[1] || 0);
            if (offset < 0) {
                offset = 0;
            }
            var colSize = beginCol - (offset - beginOffset);
            if (colSize <= 0) {
                colSize = 1;
                offset = beginOffset + beginCol - 1;
            }
            this.$target.attr('class',this.$target.attr('class').replace(/\s*(col-lg-offset-|col-md-offset-|col-md-)([0-9-]+)/g, ''));

            this.$target.addClass('col-md-' + (colSize > 12 ? 12 : colSize));
            if (offset > 0) {
                this.$target.addClass('col-md-offset-' + offset);
            }
        }
        this._super(compass, beginClass, current);
    },
});

options.registry.parallax = options.Class.extend({
    /**
     * @override
     */
    start: function () {
        this._refresh_callback = this._refresh.bind(this);
        this.$target.on('snippet-option-change snippet-option-preview', this._refresh_callback);
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    onFocus: function () {
        this.trigger_up('option_update', {
            optionNames: ['background', 'background_position'],
            name: 'target',
            data: this.$target.find('> .s_parallax_bg'),
        });
        this._refresh();
    },
    /**
     * @override
     */
    onMove: function () {
        this._refresh();
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Changes the scrolling speed of the parallax effect.
     *
     * @see this.selectClass for parameters
     */
    scroll: function (previewMode, value) {
        this.$target.attr('data-scroll-background-ratio', value);
        this._refresh();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Notifies the parallax animation that it needs to be reinitialized.
     *
     * @private
     */
    _refresh: function () {
        var self = this;
        _.defer(function () {
            self.$target.data('snippet-view')._rebuild();
        });
    },
    /**
     * @override
     */
    _setActive: function () {
        this._super.apply(this, arguments);
        this.$el.find('[data-scroll]').removeClass('active')
            .filter('[data-scroll="' + (this.$target.attr('data-scroll-background-ratio') || 0) + '"]').addClass('active');
    },
});

options.registry.ul = options.Class.extend({
    /**
     * @override
     */
    start: function () {
        var self = this;
        this.$target.on('mouseup', '.o_ul_toggle_self, .o_ul_toggle_next', function () {
            self.trigger_up('cover_update');
        });
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    cleanForSave: function () {
        this._super();
        if (!this.$target.hasClass('o_ul_folded')) {
            this.$target.find('.o_close').removeClass('o_close');
        }
        this.$target.find('li:not(:has(>ul))').css('list-style', '');
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    toggleClass: function () {
        this._super.apply(this, arguments);

        this.$target.data('snippet-view').destroy();

        this.$target.find('.o_ul_toggle_self, .o_ul_toggle_next').remove();
        this.$target.find('li:has(>ul,>ol)').map(function () {
            // get if the li contain a text label
            var texts = _.filter(_.toArray(this.childNodes), function (a) { return a.nodeType === 3;});
            if (!texts.length || !texts.reduce(function (a,b) { return a.textContent + b.textContent;}).match(/\S/)) {
                return;
            }
            $(this).children('ul,ol').addClass('o_close');
            return $(this).children(':not(ul,ol)')[0] || this;
        })
        .prepend('<a href="#" class="o_ul_toggle_self fa" />');
        var $li = this.$target.find('li:has(+li:not(>.o_ul_toggle_self)>ul, +li:not(>.o_ul_toggle_self)>ol)');
        $li.map(function () { return $(this).children()[0] || this; })
            .prepend('<a href="#" class="o_ul_toggle_next fa" />');
        $li.removeClass('o_open').next().addClass('o_close');
        this.$target.find('li').removeClass('o_open').css('list-style', '');
        this.$target.find('li:has(.o_ul_toggle_self, .o_ul_toggle_next), li:has(>ul,>ol):not(:has(>li))').css('list-style', 'none');

        this.$target.find('li:not(:has(>ul))').css('list-style', '');
        this.trigger_up('animation_start_demand', {
            editableMode: true,
            $target: this.$target,
        });
    },
});

options.registry.collapse = options.Class.extend({
    /**
     * @override
     */
    start: function () {
        var self = this;
        this.$target.on('shown.bs.collapse hidden.bs.collapse', '[role="tabpanel"]', function () {
            self.trigger_up('cover_update');
        });
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    onBuilt: function () {
        this._createIDs();
    },
    /**
     * @override
     */
    onClone: function () {
        this.$target.find('[data-toggle="collapse"]').removeAttr('data-target').removeData('target');
        this.$target.find('.panel-collapse').removeAttr('id');
        this._createIDs();
    },
    /**
     * @override
     */
    onMove: function () {
        this._createIDs();
        var $panel = this.$target.find('.panel-collapse').removeData('bs.collapse');
        if ($panel.attr('aria-expanded') === 'true') {
            $panel.closest('.panel-group').find('.panel-collapse[aria-expanded="true"]')
                .filter(function () {return this !== $panel[0];})
                .collapse('hide')
                .one('hidden.bs.collapse', function () {
                    $panel.trigger('shown.bs.collapse');
                });
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Associates unique ids on collapse elements.
     *
     * @private
     */
    _createIDs: function () {
        var time = new Date().getTime();
        var $tab = this.$target.find('[data-toggle="collapse"]');

        // link to the parent group
        var $tablist = this.$target.closest('.panel-group');
        var tablist_id = $tablist.attr('id');
        if (!tablist_id) {
            tablist_id = 'myCollapse' + time;
            $tablist.attr('id', tablist_id);
        }
        $tab.attr('data-parent', '#'+tablist_id);
        $tab.data('parent', '#'+tablist_id);

        // link to the collapse
        var $panel = this.$target.find('.panel-collapse');
        var panel_id = $panel.attr('id');
        if (!panel_id) {
            while ($('#'+(panel_id = 'myCollapseTab' + time)).length) {
                time++;
            }
            $panel.attr('id', panel_id);
        }
        $tab.attr('data-target', '#'+panel_id);
        $tab.data('target', '#'+panel_id);
    },
});

options.registry.gallery = options.Class.extend({
    xmlDependencies: ['/website/static/src/xml/website.gallery.xml'],

    /**
     * @override
     */
    start: function () {
        var self = this;

        // The snippet should not be editable
        this.$target.attr('contentEditable', false);

        // Make sure image previews are updated if images are changed
        this.$target.on('save', 'img', function (ev) {
            var $img = $(ev.currentTarget);
            var index = self.$target.find('.item.active').index();
            self.$('.carousel:first li[data-target]:eq(' + index + ')')
                .css('background-image', 'url(' + $img.attr('src') + ')');
        });

        // When the snippet is empty, an edition button is the default content
        // TODO find a nicer way to do that to have editor style
        this.$target.on('click', '.o_add_images', function (e) {
            e.stopImmediatePropagation();
            self.addImages(false);
        });

        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    onBuilt: function () {
        var uuid = new Date().getTime();
        this.$target.find('.carousel').attr('id', 'slideshow_' + uuid);
        this.$target.find('[data-target]').attr('data-target', '#slideshow_' + uuid);
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
    addImages: function (previewMode) {
        var self = this;
        var $container = this.$('.container:first');
        var dialog = new widgets.MediaDialog(this, {select_images: true}, this.$target.closest('.o_editable'), null);
        var lastImage = _.last(this._getImages());
        var index = lastImage ? this._getIndex(lastImage) : -1;
        dialog.on('save', this, function (attachments) {
            for (var i = 0 ; i < attachments.length; i++) {
                $('<img/>', {
                    class: 'img img-responsive',
                    src: attachments[i].src,
                    'data-index': ++index,
                }).appendTo($container);
            }
            self._reset();
            self.trigger_up('cover_update');
        });
        dialog.open();
    },
    /**
     * Allows to change the number of columns when displaying images with a
     * grid-like layout.
     *
     * @see this.selectClass for parameters
     */
    columns: function (previewMode, value) {
        this.$target.attr('data-columns', value);

        var $activeMode = this.$el.find('.active[data-mode]');
        this.mode(null, $activeMode.data('mode'), $activeMode);
    },
    /**
     * Displays the images with the "grid" layout.
     */
    grid: function () {
        var imgs = this._getImages();
        var $row = $('<div/>', {class: 'row'});
        var columns = this._getColumns();
        var colClass = 'col-md-' + (12 / columns);
        var $container = this._replaceContent($row);

        _.each(imgs, function (img, index) {
            var $img = $(img);
            var $col = $('<div/>', {class: colClass});
            $col.append($img).appendTo($row);
            if ((index + 1) % columns === 0) {
                $row = $('<div/>', {class: 'row'});
                $row.appendTo($container);
            }
        });
        this.$target.css('height', '');
    },
    /**
     * Allows to changes the interval of automatic slideshow (not active in
     * edit mode).
     */
    interval: function (previewMode, value) {
        this.$target.find('.carousel:first').attr('data-interval', value);
    },
    /**
     * Displays the images with the "masonry" layout.
     */
    masonry: function () {
        var imgs = this._getImages();
        var columns = this._getColumns();
        var colClass = 'col-md-' + (12 / columns);
        var cols = [];

        var $row = $('<div/>', {class: 'row'});
        this._replaceContent($row);

        // Create columns
        for (var c = 0; c < columns; c++) {
            var $col = $('<div/>', {class: 'col o_snippet_not_selectable ' + colClass});
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
                var height = $col.height();
                if (height < min) {
                    min = height;
                    $lowest = $col;
                }
            });
            $lowest.append(imgs.pop());
        }
    },
    /**
     * Allows to change the images layout. @see grid, masonry, nomode, slideshow
     *
     * @see this.selectClass for parameters
     */
    mode: function (previewMode, value, $li) {
        this.$target.css('height', '');
        this[value]();
        this.$target
            .removeClass('o_nomode o_masonry o_grid o_slideshow')
            .addClass('o_' + value);
    },
    /**
     * Displays the images with the standard layout: floating images.
     */
    nomode: function () {
        var $row = $('<div/>', {class: 'row'});
        var imgs = this._getImages();

        this._replaceContent($row);

        _.each(imgs, function (img) {
            var wrapClass = 'col-md-3';
            if (img.width >= img.height * 2 || img.width > 600) {
                wrapClass = 'col-md-6';
            }
            var $wrap = $('<div/>', {class: wrapClass}).append(img);
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
            class: 'alert alert-info css_editable_mode_display text-center',
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
        var imgStyle = this.$el.find('li.active[data-styling]').data('styling') || '';
        var urls = _.map(this._getImages(), function (img) {
            return $(img).attr('src');
        });
        var params = {
            srcs : urls,
            index: 0,
            title: "",
            interval : this.$target.data('interval') || false,
            id: 'slideshow_' + new Date().getTime(),
            userStyle: imgStyle,
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
        this.trigger_up('animation_start_demand', {
            editableMode: true,
            $target: this.$target,
        });
    },
    /**
     * Allows to change the style of the individual images.
     *
     * @see this.selectClass for parameters
     */
    styling: function (previewMode, value) {
        var classes = _.map(this.$el.find('li[data-styling]'), function (li) {
            return $(li).data('styling');
        }).join(' ');
        this.$('img').removeClass(classes).addClass(value);
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
        this._super.apply(this, arguments);
        if (name === 'image_removed') {
            data.$image.remove(); // Force the removal of the image before reset
            this._reset();
        } else if (name === 'image_index_request') {
            var imgs = this._getImages();
            var position = _.indexOf(imgs, data.$image[0]);
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
            _.each(imgs, function (img, index) {
                // Note: there might be more efficient ways to do that but it is
                // more simple this way and allows compatibility with 10.0 where
                // indexes were not the same as positions.
                $(img).attr('data-index', index);
            });
            this._reset();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
        var $container = this.$('.container:first');
        $container.empty().append($content);
        return $container;
    },
    /**
     * @override
     */
    _setActive: function () {
        this._super();
        var classes = _.uniq((this.$target.attr('class').replace(/(^|\s)o_/g, ' ') || '').split(/\s+/));
        this.$el.find('[data-mode]')
            .removeClass('active')
            .filter('[data-mode="' + classes.join('"], [data-mode="') + '"]').addClass('active');
        var mode = this.$el.find('[data-mode].active').data('mode');

        classes = _.uniq((this.$('img:first').attr('class') || '').split(/\s+/));
        this.$el.find('[data-styling]')
            .removeClass('active')
            .filter('[data-styling="' + classes.join('"], [data-styling="') + '"]').addClass('active');

        this.$el.find('li[data-interval]').removeClass('active')
            .filter('li[data-interval='+this.$target.find('.carousel:first').attr('data-interval')+']')
            .addClass('active');

        var interval = this.$target.find('.carousel:first').attr('data-interval');
        this.$el.find('[data-interval]')
            .removeClass('active')
            .filter('[data-interval=' + interval + ']').addClass('active');

        var columns = this._getColumns();
        this.$el.find('[data-columns]')
            .removeClass('active')
            .filter('[data-columns=' + columns + ']').addClass('active');

        this.$el.find('[data-columns]:first, [data-select-class="spc-none"]')
            .parent().parent().toggle(['grid', 'masonry'].indexOf(mode) !== -1);
        this.$el.find('[data-interval]:first').parent().parent().toggle(mode === 'slideshow');
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
    position: function (previewMode, value) {
        this.trigger_up('deactivate_snippet');
        this.trigger_up('option_update', {
            optionName: 'gallery',
            name: 'image_index_request',
            data: {
                $image: this.$target,
                position: value,
            },
        });
    },
});
});
