odoo.define('website.editor.snippets.options', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
const wUtils = require('website.utils');
var options = require('web_editor.snippets.options');

var _t = core._t;
var qweb = core.qweb;

options.Class.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Refreshes all public widgets related to the given element.
     *
     * @private
     * @param {jQuery} [$el=this.$target]
     * @returns {Promise}
     */
    _refreshPublicWidgets: function ($el) {
        return new Promise((resolve, reject) => {
            this.trigger_up('widgets_start_request', {
                editableMode: true,
                $target: $el || this.$target,
                onSuccess: resolve,
                onFailure: reject,
            });
        });
    },
    /**
     * @override
     */
    _select: async function (previewMode, widget) {
        await this._super(...arguments);

        if (!widget.$el.closest('[data-no-widget-refresh="true"]').length) {
            // TODO the flag should be retrieved through widget params somehow
            await this._refreshPublicWidgets();
        }
    },
});

options.registry.background.include({
    background: async function (previewMode, widgetValue, params) {
        if (previewMode === 'reset' && this.videoSrc) {
            return this._setBgVideo(false, this.videoSrc);
        }

        const _super = this._super.bind(this);
        if (!params.isVideo) {
            await this._setBgVideo(previewMode, '');
            return _super(...arguments);
        }
        return this._setBgVideo(previewMode, widgetValue);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName) {
        if (methodName === 'background' && this.$target[0].classList.contains('o_background_video')) {
            return this.$('> .o_bg_video_container iframe').attr('src');
        }
        return this._super(...arguments);
    },
    /**
     * Updates the background video used by the snippet.
     *
     * @private
     * @see this.selectClass for parameters
     * @returns {Promise}
     */
    _setBgVideo: async function (previewMode, value) {
        this.$('> .o_bg_video_container').toggleClass('d-none', previewMode === true);

        if (previewMode !== false) {
            return;
        }

        this.videoSrc = value;
        var target = this.$target[0];
        target.classList.toggle('o_background_video', !!(value && value.length));
        if (value && value.length) {
            target.dataset.bgVideoSrc = value;
        } else {
            delete target.dataset.bgVideoSrc;
        }
        await this._refreshPublicWidgets();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
     _onBackgroundColorUpdate: async function (ev, previewMode) {
        const ret = await this._super(...arguments);
        if (ret) {
            this._setBgVideo(previewMode, '');
        }
        return ret;
    },
});

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
                                var prom = new Promise(function (resolve, reject) {
                                    self.trigger_up('request_save', {
                                        onSuccess: resolve,
                                        onFailure: reject,
                                    });
                                });
                                return prom;
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
        var prom;
        var self = this;
        if (proto.__link === undefined) {
            prom = this._rpc({route: '/web/session/get_session_info'}).then(function (session) {
                return self._rpc({
                    model: 'res.users',
                    method: 'read',
                    args: [session.uid, ['company_id']],
                });
            }).then(function (res) {
                proto.__link = '/web#action=base.action_res_company_form&view_type=form&id=' + (res && res[0] && res[0].company_id[0] || 1);
            });
        }
        return Promise.all([this._super.apply(this, arguments), prom]);
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

options.registry.Carousel = options.Class.extend({
    /**
     * @override
     */
    start: function () {
        this.$target.carousel('pause');
        this.$indicators = this.$target.find('.carousel-indicators');
        this.$controls = this.$target.find('.carousel-control-prev, .carousel-control-next, .carousel-indicators');

        // Prevent enabling the carousel overlay when clicking on the carousel
        // controls (indeed we want it to change the carousel slide then enable
        // the slide overlay) + See "CarouselItem" option.
        this.$controls.addClass('o_we_no_overlay');

        let _slideTimestamp;
        this.$target.on('slide.bs.carousel.carousel_option', () => {
            _slideTimestamp = window.performance.now();
            setTimeout(() => this.trigger_up('hide_overlay'));
        });
        this.$target.on('slid.bs.carousel.carousel_option', () => {
            // slid.bs.carousel is most of the time fired too soon by bootstrap
            // since it emulates the transitionEnd with a setTimeout. We wait
            // here an extra 20% of the time before retargeting edition, which
            // should be enough...
            const _slideDuration = (window.performance.now() - _slideTimestamp);
            setTimeout(() => {
                this.trigger_up('activate_snippet', {
                    $snippet: this.$target.find('.carousel-item.active'),
                    ifInactiveOptions: true,
                });
                this.$target.trigger('active_slide_targeted');
            }, 0.2 * _slideDuration);
        });

        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        this.$target.off('.carousel_option');
    },
    /**
     * @override
     */
    onBuilt: function () {
        this._assignUniqueID();
    },
    /**
     * @override
     */
    onClone: function () {
        this._assignUniqueID();
    },
    /**
     * @override
     */
    cleanForSave: function () {
        const $items = this.$target.find('.carousel-item');
        $items.removeClass('next prev left right active').first().addClass('active');
        this.$indicators.find('li').removeClass('active').empty().first().addClass('active');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Creates a unique ID for the carousel and reassign data-attributes that
     * depend on it.
     *
     * @private
     */
    _assignUniqueID: function () {
        const id = 'myCarousel' + Date.now();
        this.$target.attr('id', id);
        this.$target.find('[data-target]').attr('data-target', '#' + id);
        this.$target.find('[data-slide]').attr('href', '#' + id);
    },
});

options.registry.CarouselItem = options.Class.extend({
    isTopOption: true,

    /**
     * @override
     */
    start: function () {
        this.$carousel = this.$target.closest('.carousel');
        this.$indicators = this.$carousel.find('.carousel-indicators');
        this.$controls = this.$carousel.find('.carousel-control-prev, .carousel-control-next, .carousel-indicators');

        var leftPanelEl = this.$overlay.data('$optionsSection')[0];
        var titleTextEl = leftPanelEl.querySelector('we-title > span');
        this.counterEl = document.createElement('span');
        titleTextEl.appendChild(this.counterEl);

        leftPanelEl.querySelector('.oe_snippet_remove').classList.add('d-none'); // TODO improve the way to do that

        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super(...arguments);
        this.$carousel.off('.carousel_item_option');
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Updates the slide counter.
     *
     * @override
     */
    updateUI: async function () {
        await this._super(...arguments);
        const $items = this.$carousel.find('.carousel-item');
        const $activeSlide = $items.filter('.active');
        const updatedText = ` (${$activeSlide.index() + 1}/${$items.length})`;
        this.counterEl.textContent = updatedText;
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
        const $items = this.$carousel.find('.carousel-item');
        this.$controls.removeClass('d-none');
        this.$indicators.append($('<li>', {
            'data-target': '#' + this.$target.attr('id'),
            'data-slide-to': $items.length,
        }));
        // Need to remove editor data from the clone so it gets its own.
        const $active = $items.filter('.active');
        $active.clone(false)
            .removeClass('active')
            .insertAfter($active);
        this.$carousel.carousel('next');
    },
    /**
     * Removes the current slide.
     *
     * @see this.selectClass for parameters.
     */
    removeSlide: function (previewMode) {
        const $items = this.$carousel.find('.carousel-item');
        const newLength = $items.length - 1;
        if (!this.removing && newLength > 0) {
            const $toDelete = $items.filter('.active');
            this.$carousel.one('active_slide_targeted.carousel_item_option', () => {
                $toDelete.remove();
                this.$indicators.find('li:last').remove();
                this.$controls.toggleClass('d-none', newLength === 1);
                this.$carousel.trigger('content_changed');
                this.removing = false;
            });
            this.removing = true;
            this.$carousel.carousel('prev');
        }
    },
    /**
     * Goes to next slide or previous slide.
     *
     * @see this.selectClass for parameters
     */
    slide: function (previewMode, widgetValue, params) {
        switch (widgetValue) {
            case 'left':
                this.$controls.filter('.carousel-control-prev')[0].click();
                break;
            case 'right':
                this.$controls.filter('.carousel-control-next')[0].click();
                break;
        }
    },
});

options.registry.sizing_x = options.registry.sizing.extend({
    /**
     * @override
     */
    onClone: function (options) {
        this._super.apply(this, arguments);
        // Below condition is added to remove offset of target element only
        // and not its children to avoid design alteration of a container/block.
        if (options.isCurrent) {
            var _class = this.$target.attr('class').replace(/\s*(offset-xl-|offset-lg-)([0-9-]+)/g, '');
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
        var width = this.$target.closest('.row').width();
        var gridE = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
        var gridW = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
        this.grid = {
            e: [_.map(gridE, v => ('col-lg-' + v)), _.map(gridE, v => width / 12 * v), 'width'],
            w: [_.map(gridW, v => ('offset-lg-' + v)), _.map(gridW, v => width / 12 * v), 'margin-left'],
        };
        return this.grid;
    },
    /**
     * @override
     */
    _onResize: function (compass, beginClass, current) {
        if (compass === 'w') {
            // don't change the right border position when we change the offset (replace col size)
            var beginCol = Number(beginClass.match(/col-lg-([0-9]+)|$/)[1] || 0);
            var beginOffset = Number(beginClass.match(/offset-lg-([0-9-]+)|$/)[1] || beginClass.match(/offset-xl-([0-9-]+)|$/)[1] || 0);
            var offset = Number(this.grid.w[0][current].match(/offset-lg-([0-9-]+)|$/)[1] || 0);
            if (offset < 0) {
                offset = 0;
            }
            var colSize = beginCol - (offset - beginOffset);
            if (colSize <= 0) {
                colSize = 1;
                offset = beginOffset + beginCol - 1;
            }
            this.$target.attr('class', this.$target.attr('class').replace(/\s*(offset-xl-|offset-lg-|col-lg-)([0-9-]+)/g, ''));

            this.$target.addClass('col-lg-' + (colSize > 12 ? 12 : colSize));
            if (offset > 0) {
                this.$target.addClass('offset-lg-' + offset);
            }
        }
        this._super.apply(this, arguments);
    },
});

options.registry.layout_column = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Changes the number of columns.
     *
     * @see this.selectClass for parameters
     */
    selectCount: function (previewMode, widgetValue, params) {
        const nbColumns = parseInt(widgetValue);
        this._updateColumnCount(nbColumns - this.$target.children().length);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        if (methodName === 'selectCount') {
            return '' + this.$target.children().length;
        }
        return this._super(...arguments);
    },
    /**
     * Adds new columns which are clones of the last column or removes the
     * last x columns.
     *
     * @private
     * @param {integer} count - positif to add, negative to remove
     */
    _updateColumnCount: function (count) {
        if (!count) {
            return;
        }

        this.trigger_up('request_history_undo_record', {$target: this.$target});

        if (count > 0) {
            var $lastColumn = this.$target.children().last();
            for (var i = 0; i < count; i++) {
                this.trigger_up('clone_snippet', {$snippet: $lastColumn});
            }
        } else {
            var self = this;
            _.each(this.$target.children().slice(count), function (el) {
                self.trigger_up('remove_snippet', {$snippet: $(el)});
            });
        }

        this._resizeColumns();
        this.trigger_up('cover_update');
    },
    /**
     * Resizes the columns so that they are kept on one row.
     *
     * @private
     */
    _resizeColumns: function () {
        var $columns = this.$target.children();
        var colsLength = $columns.length;
        var colSize = Math.floor(12 / colsLength) || 1;
        var colOffset = Math.floor((12 - colSize * colsLength) / 2);
        var colClass = 'col-lg-' + colSize;
        _.each($columns, function (column) {
            var $column = $(column);
            $column.attr('class', $column.attr('class').replace(/\b(col|offset)-lg(-\d+)?\b/g, ''));
            $column.addClass(colClass);
        });
        if (colOffset) {
            $columns.first().addClass('offset-lg-' + colOffset);
        }
    },
});

options.registry.parallax = options.Class.extend({
    /**
     * @override
     */
    onFocus: function () {
        this.trigger_up('option_update', {
            optionNames: ['background', 'BackgroundPosition'],
            name: 'target',
            data: this.$target.find('> .s_parallax_bg'),
        });
        // Refresh the parallax animation on focus; at least useful because
        // there may have been changes in the page that influenced the parallax
        // rendering (new snippets, ...).
        // TODO make this automatic.
        this._refreshPublicWidgets();
    },
    /**
     * @override
     */
    onMove: function () {
        this._refreshPublicWidgets();
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
            this.$target.find('li').css('list-style', '');
        }
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    selectClass: async function () {
        await this._super.apply(this, arguments);

        this.trigger_up('widgets_stop_request', {
            $target: this.$target,
        });

        this.$target.find('.o_ul_toggle_self, .o_ul_toggle_next').remove();
        this.$target.find('li:has(>ul,>ol)').map(function () {
            // get if the li contain a text label
            var texts = _.filter(_.toArray(this.childNodes), a => (a.nodeType === 3));
            if (!texts.length || !texts.reduce((a, b) => (a.textContent + b.textContent)).match(/\S/)) {
                return;
            }
            $(this).children('ul,ol').addClass('o_close');
            return $(this).children(':not(ul,ol)')[0] || this;
        })
        .prepend('<a href="#" class="o_ul_toggle_self fa" />');
        var $li = this.$target.find('li:has(+li:not(>.o_ul_toggle_self)>ul, +li:not(>.o_ul_toggle_self)>ol)');
        $li.css('list-style', this.$target.hasClass('o_ul_folded') ? 'none' : '');
        $li.map((i, el) => ($(el).children()[0] || el))
            .prepend('<a href="#" class="o_ul_toggle_next fa" />');
        $li.removeClass('o_open').next().addClass('o_close');
        this.$target.find('li').removeClass('o_open');
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
        this.$target.find('.collapse').removeAttr('id');
        this._createIDs();
    },
    /**
     * @override
     */
    onMove: function () {
        this._createIDs();
        var $panel = this.$target.find('.collapse').removeData('bs.collapse');
        if ($panel.attr('aria-expanded') === 'true') {
            $panel.closest('.accordion').find('.collapse[aria-expanded="true"]')
                .filter((i, el) => (el !== $panel[0]))
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
        var $tablist = this.$target.closest('.accordion');
        var tablist_id = $tablist.attr('id');
        if (!tablist_id) {
            tablist_id = 'myCollapse' + time;
            $tablist.attr('id', tablist_id);
        }
        $tab.attr('data-parent', '#' + tablist_id);
        $tab.data('parent', '#' + tablist_id);

        // link to the collapse
        var $panel = this.$target.find('.collapse');
        var panel_id = $panel.attr('id');
        if (!panel_id) {
            while ($('#' + (panel_id = 'myCollapseTab' + time)).length) {
                time++;
            }
            $panel.attr('id', panel_id);
        }
        $tab.attr('data-target', '#' + panel_id);
        $tab.data('target', '#' + panel_id);
    },
});

options.registry.topMenuTransparency = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Handles the toggling between normal and overlay positions of the header.
     *
     * @see this.selectClass for params
     */
    transparent: function (previewMode, widgetValue, params) {
        var self = this;
        this.trigger_up('action_demand', {
            actionName: 'toggle_page_option',
            params: [{name: 'header_overlay'}],
            onSuccess: function () {
                self.trigger_up('action_demand', {
                    actionName: 'toggle_page_option',
                    params: [{name: 'header_color', value: ''}],
                });
            },
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        if (methodName === 'transparent') {
            return new Promise(resolve => {
                this.trigger_up('action_demand', {
                    actionName: 'get_page_option',
                    params: ['header_overlay'],
                    onSuccess: v => resolve(v ? 'true' : ''),
                });
            });
        }
        return this._super(...arguments);
    },
});

options.registry.topMenuColor = options.Class.extend({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeVisibility: async function () {
        const show = await this._super(...arguments);
        if (!show) {
            return false;
        }
        return new Promise(resolve => {
            this.trigger_up('action_demand', {
                actionName: 'get_page_option',
                params: ['header_overlay'],
                onSuccess: value => resolve(!!value),
            });
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onColorButtonClick: function () {
        this._super.apply(this, arguments);
        var bgs = this.$target.attr('class').match(/bg-(\w|-)+/g);
        var allowedBgs = this.classes.split(' ');
        var color = _.intersection(bgs, allowedBgs).join(' ');
        this.trigger_up('action_demand', {
            actionName: 'toggle_page_option',
            params: [{name: 'header_color', value: color}],
        });
    },
});

/**
 * Handles the edition of snippet's anchor name.
 */
options.registry.anchor = options.Class.extend({
    xmlDependencies: ['/website/static/src/xml/website.editor.xml'],
    isTopOption: true,

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    start: function () {
        // Generate anchor and copy it to clipboard on click, show the tooltip on success
        this.$button = this.$el.find('we-button');
        const clipboard = new ClipboardJS(this.$button[0], {text: () => this._getAnchorLink()});
        clipboard.on('success', () => {
            const anchor = decodeURIComponent(this._getAnchorLink());
            this.displayNotification({
              title: _t("Copied !"),
              message: _.str.sprintf(_t("The anchor has been copied to your clipboard.<br>Link: %s"), anchor),
              buttons: [{text: _t("edit"), click: () => this.openAnchorDialog()}],
            });
        });

        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    onClone: function () {
        this.$target.removeAttr('id data-anchor');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * @see this.selectClass for parameters
     */
    openAnchorDialog: function (previewMode, widgetValue, params) {
        var self = this;
        var buttons = [{
            text: _t("Save & copy"),
            classes: 'btn-primary',
            click: function () {
                var $input = this.$('.o_input_anchor_name');
                var anchorName = self._text2Anchor($input.val());
                if (self.$target[0].id === anchorName) {
                    // If the chosen anchor name is already the one used by the
                    // element, close the dialog and do nothing else
                    this.close();
                    return;
                }

                const alreadyExists = !!document.getElementById(anchorName);
                this.$('.o_anchor_already_exists').toggleClass('d-none', !alreadyExists);
                $input.toggleClass('is-invalid', alreadyExists);
                if (!alreadyExists) {
                    self._setAnchorName(anchorName);
                    this.close();
                    self.$button[0].click();
                }
            },
        }, {
            text: _t("Discard"),
            close: true,
        }];
        if (this.$target.attr('id')) {
            buttons.push({
                text: _t("Remove"),
                classes: 'btn-link ml-auto',
                icon: 'fa-trash',
                close: true,
                click: function () {
                    self._setAnchorName();
                },
            });
        }
        new Dialog(this, {
            title: _t("Link Anchor"),
            $content: $(qweb.render('website.dialog.anchorName', {
                currentAnchor: decodeURIComponent(this.$target.attr('id')),
            })),
            buttons: buttons,
        }).open();
    },
    /**
     * @private
     * @param {String} value
     */
    _setAnchorName: function (value) {
        if (value) {
            this.$target.attr({
                'id': value,
                'data-anchor': true,
            });
        } else {
            this.$target.removeAttr('id data-anchor');
        }
        this.$target.trigger('content_changed');
    },
    /**
     * Returns anchor text.
     *
     * @private
     * @returns {string}
     */
    _getAnchorLink: function () {
        if (!this.$target[0].id) {
            const $titles = this.$target.find('h1, h2, h3, h4, h5, h6');
            const title = $titles.length > 0 ? $titles[0].innerText : this.data.snippetName;
            const anchorName = this._text2Anchor(title);
            let n = '';
            while (document.getElementById(anchorName + n)) {
                n = (n || 1) + 1;
            }
            this._setAnchorName(anchorName + n);
        }
        return `#${this.$target[0].id}`;
    },
    /**
     * Creates a safe id/anchor from text.
     *
     * @private
     * @param {string} text
     * @returns {string}
     */
    _text2Anchor: function (text) {
        return encodeURIComponent(text.trim().replace(/\s+/g, '-'));
    },
});

/**
 * Allows edition of 'cover_properties' in website models which have such
 * fields (blogs, posts, events, ...).
 */
options.registry.CoverProperties = options.Class.extend({
    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        this.$image = this.$target.find('.o_record_cover_image');
        this.$filter = this.$target.find('.o_record_cover_filter');
    },
    /**
     * @override
     */
    start: function () {
        this.$filterValueOpts = this.$el.find('[data-filter-value]');
        this.$filterColorOpts = this.$el.find('[data-filter-color]');
        this.filterColorClasses = this.$filterColorOpts.map(function () {
            return $(this).data('filterColor');
        }).get().join(' ');

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Handles a background change.
     *
     * @see this.selectClass for parameters
     */
    background: async function (previewMode, widgetValue, params) {
        if (widgetValue === '') {
            this.$image.css('background-image', '');
            this.$target.removeClass('o_record_has_cover');
        } else {
            this.$image.css('background-image', `url('${widgetValue}')`);
            const $defaultSizeBtn = this.$el.find('.o_record_cover_opt_size_default');
            $defaultSizeBtn.click();
            $defaultSizeBtn.closest('we-select').click();
        }
    },
    /**
     * @see this.selectClass for parameters
     */
    filterValue: function (previewMode, widgetValue, params) {
        this.$filter.css('opacity', widgetValue || 0);
    },
    /**
     * @see this.selectClass for parameters
     */
    filterColor: function (previewMode, widgetValue, params) {
        this.$filter.removeClass(this.filterColorClasses);
        if (widgetValue) {
            this.$filter.addClass(widgetValue);
        }

        var $firstVisibleFilterOpt = this.$filterValueOpts.eq(1);
        if (parseFloat(this.$filter.css('opacity')) < parseFloat($firstVisibleFilterOpt.data('filterValue'))) {
            this.filterValue(previewMode, $firstVisibleFilterOpt.data('filterValue'), $firstVisibleFilterOpt);
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    updateUI: async function () {
        await this._super(...arguments);

        // Update saving dataset
        this.$target[0].dataset.coverClass = this.$el.find('[data-cover-opt-name="size"] we-button.active').data('selectClass') || '';
        this.$target[0].dataset.textSizeClass = this.$el.find('[data-cover-opt-name="text_size"] we-button.active').data('selectClass') || '';
        this.$target[0].dataset.textAlignClass = this.$el.find('[data-cover-opt-name="text_align"] we-button.active').data('selectClass') || '';
        this.$target[0].dataset.filterValue = this.$filterValueOpts.filter('.active').data('filterValue') || 0.0;
        this.$target[0].dataset.filterColor = this.$filterColorOpts.filter('.active').data('filterColor') || '';
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        switch (methodName) {
            case 'filterValue': {
                return parseFloat(this.$filter.css('opacity')).toFixed(1);
            }
            case 'filterColor': {
                const classes = this.filterColorClasses.split(' ');
                for (const className of classes) {
                    if (this.$filter.hasClass(className)) {
                        return className;
                    }
                }
                return '';
            }
            case 'background': {
                const background = this.$image.css('background-image');
                if (background && background !== 'none') {
                    return background.match(/^url\(["']?(.+?)["']?\)$/)[1];
                }
                return '';
            }
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _computeWidgetVisibility: function (widgetName, params) {
        const hasCover = this.$target.hasClass('o_record_has_cover');
        if (params.coverOptName) {
            var notAllowed = (this.$target.data(`use_${params.coverOptName}`) !== 'True');
            return (hasCover && !notAllowed);
        }
        return this._super(...arguments);
    },
});

/**
 * Allows snippets to be moved before the preceding element or after the following.
 */
options.registry.SnippetMove = options.Class.extend({
    /**
     * @override
     */
    start: function () {
        var $buttons = this.$el.find('we-button');
        var $overlayArea = this.$overlay.find('.o_overlay_move_options');
        $overlayArea.prepend($buttons[0]);
        $overlayArea.append($buttons[1]);

        return this._super(...arguments);
    },
    /**
     * @override
     */
    onFocus: function () {
        // TODO improve this: hack to hide options section if snippet move is
        // the only one.
        const $allOptions = this.$el.parent();
        if ($allOptions.find('we-customizeblock-option').length <= 1) {
            $allOptions.addClass('d-none');
        }
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Moves the snippet around.
     *
     * @see this.selectClass for parameters
     */
    moveSnippet: function (previewMode, widgetValue, params) {
        const isNavItem = this.$target[0].classList.contains('nav-item');
        const $tabPane = isNavItem ? $(this.$target.find('.nav-link')[0].hash) : null;
        switch (widgetValue) {
            case 'prev':
                this.$target.prev().before(this.$target);
                if (isNavItem) {
                    $tabPane.prev().before($tabPane);
                }
                break;
            case 'next':
                this.$target.next().after(this.$target);
                if (isNavItem) {
                    $tabPane.next().after($tabPane);
                }
                break;
        }
    },
});

const InputUserValueWidget = options.userValueWidgetsRegistry['we-input'];
const UrlPickerUserValueWidget = InputUserValueWidget.extend({
    custom_events: _.extend({}, InputUserValueWidget.prototype.custom_events || {}, {
        website_url_chosen: '_onWebsiteURLChosen',
    }),

    /**
     * @override
     */
    start: async function () {
        await this._super(...arguments);
        $(this.inputEl).addClass('text-left');
        wUtils.autocompleteWithPages(this, $(this.inputEl));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the autocomplete change the input value.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onWebsiteURLChosen: function (ev) {
        $(this.inputEl).trigger('input');
        this._onUserValueChange(ev);
    },
});

options.registry.ScrollButton = options.Class.extend({
    /**
     * @override
     */
    start: async function () {
        await this._super(...arguments);
        this.$button = this.$('.o_scroll_button');
    },
    /**
     * Removes button if the option is not displayed (for example in "fit
     * content" height).
     *
     * @override
     */
    updateUIVisibility: async function () {
        await this._super(...arguments);
        if (this.$button.length && this.el.offsetParent === null) {
            this.$button.detach();
        }
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Toggles the scroll down button.
     */
    toggleButton: function (previewMode, widgetValue, params) {
        if (widgetValue) {
            if (!this.$button.length) {
                const anchor = document.createElement('a');
                anchor.classList.add(
                    'o_scroll_button',
                    'rounded-circle',
                    'align-items-center',
                    'justify-content-center',
                    'mx-auto',
                    'bg-primary',
                );
                anchor.href = '#';
                anchor.contentEditable = "false";
                anchor.title = _t("Scroll down to next section");
                const arrow = document.createElement('i');
                arrow.classList.add('fa', 'fa-angle-down', 'fa-3x');
                anchor.appendChild(arrow);
                this.$button = $(anchor);
            }
            this.$target.append(this.$button);
        } else {
            this.$button.detach();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        switch (methodName) {
            case 'toggleButton':
                return !!this.$button.parent().length;
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _computeVisibility: function () {
        return this.$target.is('.o_full_screen_height, .o_half_screen_height');
    },
});

options.userValueWidgetsRegistry['we-urlpicker'] = UrlPickerUserValueWidget;
return {
    UrlPickerUserValueWidget: UrlPickerUserValueWidget,
};
});
