odoo.define('web_editor.snippets.options', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var Widget = require('web.Widget');
var weContext = require('web_editor.context');
var widget = require('web_editor.widget');

var qweb = core.qweb;
var _t = core._t;

/**
 * Handles a set of options for one snippet. The registry returned by this
 * module contains the names of the specialized SnippetOption which can be
 * referenced thanks to the data-js key in the web_editor options template.
 */
var SnippetOption = Widget.extend({
    events: {
        'mouseenter a': '_onLinkEnter',
        'click a': '_onLinkClick',
        'mouseleave': '_onMouseleave',
        'mouseleave ul': '_onMouseleave',
    },
    /**
     * When editing a snippet, its options are shown alongside the ones of its
     * parent snippets. The parent options are only shown if the following flag
     * is set to false (default).
     */
    preventChildPropagation: false,

    /**
     * The option `$el` is supposed to be the associated <li/> element in the
     * options dropdown. The option controls another DOM element: the snippet it
     * customizes, which can be found at `$target`. Access to the whole edition
     * overlay is possible with `$overlay` (this is not recommended though).
     *
     * @constructor
     */
    init: function (parent, $target, $overlay, data) {
        this._super.apply(this, arguments);
        this.$target = $target;
        this.$overlay = $overlay;
        this.data = data;
        this.__methodNames = [];
    },
    /**
     * Called when the option is initialized (i.e. the parent edition overlay is
     * shown for the first time).
     *
     * @override
     */
    start: function () {
        this._setActive();
        return this._super.apply(this, arguments);
    },
    /**
     * Called when the parent edition overlay is covering the associated snippet
     * (the first time, this follows the call to the @see start method).
     *
     * @abstract
     */
    onFocus : function () {},
    /**
     * Called when the parent edition overlay is covering the associated snippet
     * for the first time, when it is a new snippet dropped from the d&d snippet
     * menu. Note: this is called after the start and onFocus methods.
     *
     * @abstract
     */
    onBuilt: function () {},
    /**
     * Called when the parent edition overlay is removed from the associated
     * snippet (another snippet enters edition for example).
     *
     * @abstract
     */
    onBlur : function () {},
    /**
     * Called when the associated snippet is the result of the cloning of
     * another snippet (so `this.$target` is a cloned element).
     *
     * @abstract
     * @param {Object} options
     * @param {boolean} options.isCurrent
     *        true if the associated snippet is a clone of the main element that
     *        was cloned (so not a clone of a child of this main element that
     *        was cloned)
     */
    onClone: function (options) {},
    /**
     * Called when the associated snippet is moved to another DOM location.
     *
     * @abstract
     */
    onMove: function () {},
    /**
     * Called when the associated snippet is about to be removed from the DOM.
     *
     * @abstract
     */
    onRemove: function () {},
    /**
     * Called when the template which contains the associated snippet is about
     * to be saved.
     *
     * @abstract
     */
    cleanForSave: function () {},

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Default option method which allows to select one and only one class in
     * the option classes set and set it on the associated snippet. The common
     * case is having a subdropdown with each <li/> having a `data-select-class`
     * value allowing to choose the associated class.
     *
     * @param {boolean|string} previewMode
     *        - truthy if the option is enabled for preview or if leaving it (in
     *          that second case, the value is 'reset')
     *        - false if the option should be activated for good
     * @param {*} value - the class to activate ($li.data('selectClass'))
     * @param {jQuery} $li - the related DOMElement option
     */
    selectClass: function (previewMode, value, $li) {
        var $lis = this.$el.find('[data-select-class]').addBack('[data-select-class]');
        var classes = $lis.map(function () {return $(this).data('selectClass');}).get().join(' ');

        this.$target.removeClass(classes);
        if (value) {
            this.$target.addClass(value);
        }
    },
    /**
     * Default option method which allows to select one or multiple classes in
     * the option classes set and set it on the associated snippet. The common
     * case is having a subdropdown with each <li/> having a `data-toggle-class`
     * value allowing to toggle the associated class.
     *
     * @see this.selectClass
     */
    toggleClass: function (previewMode, value, $li) {
        var $lis = this.$el.find('[data-toggle-class]').addBack('[data-toggle-class]');
        var classes = $lis.map(function () {return $(this).data('toggleClass');}).get().join(' ');
        var activeClasses = $lis.filter('.active, :has(.active)').map(function () {return $(this).data('toggleClass');}).get().join(' ');

        this.$target.removeClass(classes).addClass(activeClasses);
        if (value && previewMode !== 'reset') {
            this.$target.toggleClass(value);
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Override the helper method to search inside the $target element instead
     * of the dropdown <li/> element.
     *
     * @override
     */
    $: function () {
        return this.$target.find.apply(this.$target, arguments);
    },
    /**
     * Sometimes, options may need to notify other options, even in parent
     * editors. This can be done thanks to the 'option_update' event, which
     * will then be handled by this function.
     *
     * @param {string} name - an identifier for a type of update
     * @param {*} data
     */
    notify: function (name, data) {
        if (name === 'target') {
            this.setTarget(data);
        }
    },
    /**
     * Sometimes, an option is binded on an element but should in fact apply on
     * another one. For example, elements which contain slides: we want all the
     * per-slide options to be in the main menu of the whole snippet. This
     * function allows to set the option's target.
     *
     * @param {jQuery} $target - the new target element
     */
    setTarget: function ($target) {
        this.$target = $target;
        this._setActive();
        this.$target.trigger('snippet-option-change', [this]);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Reactivate the options that were activated before previews.
     */
    _reset: function () {
        var self = this;
        var $actives = this.$el.find('.active').addBack('.active');
        _.each($actives, function (activeElement) {
            var $activeElement = $(activeElement);
            self.__methodNames = _.without.apply(_, [self.__methodNames].concat(_.keys($activeElement.data())));
            self._select('reset', $activeElement);
        });
        _.each(this.__methodNames, function (methodName) {
            self[methodName]('reset');
        });
        this.__methodNames = [];
    },
    /**
     * Activates the option associated to the given DOM element.
     *
     * @private
     * @param {boolean|string} previewMode
     *        - truthy if the option is enabled for preview or if leaving it (in
     *          that second case, the value is 'reset')
     *        - false if the option should be activated for good
     * @param {jQuery} $li - the related DOMElement option
     */
    _select: function (previewMode, $li) {
        var self = this;

        // Options can say they respond to strong choice
        if (previewMode && ($li.data('noPreview') || $li.parent().data('noPreview'))) {
            return;
        }
        // If it is not preview mode, the user selected the option for good
        // (so record the action)
        if (!previewMode) {
            this._reset();
            this.trigger_up('request_history_undo_record', {$target: this.$target});
        }

        // Search for methods (data-...) (i.e. data-toggle-class) on the
        // selected (sub)option and its parents
        var el = $li[0];
        var methods = [];
        do {
            methods.push([el, el.dataset]);
            el = el.parentNode;
        } while (this.$el.parent().has(el).length);

        // Call the found method in the right order (parents -> child)
        _.each(methods.reverse(), function (data) {
            var $el = $(data[0]);
            var methods = data[1];

            _.each(methods, function (value, methodName) {
                if (self[methodName]) {
                    if (previewMode === true) {
                        self.__methodNames.push(methodName);
                    }
                    self[methodName](previewMode, value, $el);
                }
            });
        });
        this.__methodNames = _.uniq(this.__methodNames);

        if (!previewMode) {
            this._setActive();
        }
    },
    /**
     * Tweaks the option DOM elements to show the selected value according to
     * the state of the $target the option customizes.
     *
     * @todo should be extendable in a more easy way
     * @private
     */
    _setActive: function () {
        var self = this;
        this.$el.find('[data-toggle-class]')
            .addBack('[data-toggle-class]')
            .removeClass('active')
            .filter(function () {
                var className = $(this).data('toggleClass');
                return !className || self.$target.hasClass(className);
            })
            .addClass('active');

        _processSelectClassElements(this.$el);
        _.each(this.$el.find('.dropdown-menu'), function (group) {
            _processSelectClassElements($(group).children());
        });

        function _processSelectClassElements($elements) {
            var maxNbClasses = -1;
            $elements.filter('[data-select-class]')
                .removeClass('active')
                .filter(function () {
                    var className = $(this).data('selectClass');
                    var nbClasses = className ? className.split(' ').length : 0;
                    if (nbClasses >= maxNbClasses && (!className || self.$target.hasClass(className))) {
                        maxNbClasses = nbClasses;
                        return true;
                    }
                    return false;
                })
                .last()
                .addClass('active');
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a option link is entered -> activates the related option in
     * preview mode.
     *
     * @private
     * @param {Event} ev
     */
    _onLinkEnter: function (ev) {
        var $li = $(ev.currentTarget).parent();
        if ($li.is('.dropdown-submenu')) {
            var $menu = $li.children('.dropdown-menu');
            if ($menu.length) {
                var menuRightPosition = $li.offset().left + $li.outerWidth() + $menu.outerWidth();
                $menu.toggleClass('o_open_to_left', menuRightPosition > $(window).outerWidth());
            }
        }

        if (!$li.is(':hasData')) {
            return;
        }
        this.__click = false;
        this._select(true, $li);
        this.$target.trigger('snippet-option-preview', [this]);
    },
    /**
     * Called when an option link is clicked -> activates the related option.
     *
     * @private
     * @param {Event} ev
     */
    _onLinkClick: function (ev) {
        var $li = $(ev.currentTarget).parent(':hasData');
        if (!$li.length) {
            return;
        }
        ev.preventDefault();
        this.__click = true;
        this._select(false, $li);
        this.$target.trigger('snippet-option-change', [this]);
    },
    /**
     * Called when an option link/menu is left -> reactivate the options that
     * were activated before previews.
     *
     * @private
     */
    _onMouseleave: function () {
        if (this.__click) {
            return;
        }
        this._reset();
    },
});

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

/**
 * The registry object contains the list of available options.
 */
var registry = {};

registry.marginAndResize = SnippetOption.extend({
    preventChildPropagation: true,

    /**
     * @override
     */
    start: function () {
        var self = this;
        this._super();

        var resize_values = this._getSize();
        if (resize_values.n) this.$overlay.find('.oe_handle.n').removeClass('readonly');
        if (resize_values.s) this.$overlay.find('.oe_handle.s').removeClass('readonly');
        if (resize_values.e) this.$overlay.find('.oe_handle.e').removeClass('readonly');
        if (resize_values.w) this.$overlay.find('.oe_handle.w').removeClass('readonly');
        if (resize_values.size) this.$overlay.find('.oe_handle.size').removeClass('readonly');

        var $auto_size = this.$overlay.find('.oe_handle.size .auto_size');
        var $fixed_size = this.$overlay.find('.oe_handle.size .size');

        var auto_sized = isNaN(parseInt(self.$target.prop('style').height));
        $fixed_size.toggleClass('active', !auto_sized);
        $auto_size.toggleClass('active', auto_sized);

        $fixed_size.add(this.$overlay.find('.oe_handle:not(.size)')).on('mousedown', function (event) {
            event.preventDefault();

            var $handle = $(this);

            var resize_values = self._getSize();
            var compass = false;
            var XY = false;
            if ($handle.hasClass('n')) {
                compass = 'n';
                XY = 'Y';
            }
            else if ($handle.hasClass('s')) {
                compass = 's';
                XY = 'Y';
            }
            else if ($handle.hasClass('e')) {
                compass = 'e';
                XY = 'X';
            }
            else if ($handle.hasClass('w')) {
                compass = 'w';
                XY = 'X';
            }
            else if ($handle.hasClass('size')) {
                compass = 'size';
                XY = 'Y';
            }

            var resize = resize_values[compass];
            if (!resize) return;


            if (compass === 'size') {
                var offset = self.$target.offset().top;
            } else {
                var xy = event['page'+XY];
                var current = resize[2] || 0;
                var margin_dir = {s:'bottom', n: 'top', w: 'left', e: 'right'}[compass];
                var real_margin = parseInt(self.$target.css('margin-'+margin_dir));
                _.each(resize[0], function (val, key) {
                    if (self.$target.hasClass(val)) {
                        current = key;
                    } else if (resize[1][key] === real_margin) {
                        current = key;
                    }
                });
                var begin = current;
                var beginClass = self.$target.attr('class');
                var regClass = new RegExp('\\s*' + resize[0][begin].replace(/[-]*[0-9]+/, '[-]*[0-9]+'), 'g');
            }

            var cursor = $handle.css('cursor')+'-important';
            var $body = $(document.body);
            $body.addClass(cursor);

            var body_mousemove = function (event) {
                event.preventDefault();
                if (compass === 'size') {
                    var dy = event.pageY-offset;
                    dy = dy - dy%resize;
                    if (dy <= 0) dy = resize;
                    self.$target.css('height', dy+'px');
                    self.$target.css('overflow', 'hidden');
                    self._onResize(compass, null, dy);
                    self.trigger_up('cover_update');
                    return;
                }
                var dd = event['page'+XY] - xy + resize[1][begin];
                var next = current+1 === resize[1].length ? current : (current+1);
                var prev = current ? (current-1) : 0;

                var change = false;
                if (dd > (2*resize[1][next] + resize[1][current])/3) {
                    self.$target.attr('class', (self.$target.attr('class')||'').replace(regClass, ''));
                    self.$target.addClass(resize[0][next]);
                    current = next;
                    change = true;
                }
                if (prev !== current && dd < (2*resize[1][prev] + resize[1][current])/3) {
                    self.$target.attr('class', (self.$target.attr('class')||'').replace(regClass, ''));
                    self.$target.addClass(resize[0][prev]);
                    current = prev;
                    change = true;
                }

                if (change) {
                    self._onResize(compass, beginClass, current);
                    self.trigger_up('cover_update');
                    self._adaptMarginsPreviews();
                    $handle.addClass('oe_handle_change');
                }
            };

            var body_mouseup = function () {
                $body.unbind('mousemove', body_mousemove);
                $body.unbind('mouseup', body_mouseup);
                $body.removeClass(cursor);
                setTimeout(function () {
                    if (begin !== current) {
                        self.trigger_up('request_history_undo_record', {
                            $target: self.$target,
                            event: 'resize_' + XY,
                        });
                    }
                },0);
                $handle.removeClass('oe_handle_change');

                if (compass === 'size') {
                    $fixed_size.addClass('active');
                    $auto_size.removeClass('active');
                } else {
                    self._highlightMarginsPreviews();
                }
            };
            $body.mousemove(body_mousemove);
            $body.mouseup(body_mouseup);
        });
        $auto_size.on('click', function () {
            self.$target.css('height', '');
            self.$target.css('overflow', '');
            self.trigger_up('request_history_undo_record', {
                $target: self.$target,
                event: 'resize_Y',
            });
            self.trigger_up('cover_update');

            $fixed_size.removeClass('active');
            $auto_size.addClass('active');

            return false;
        });
    },
    /**
     * @override
     */
    onFocus : function () {
        this._updateCursor();
        this._adaptMarginsPreviews();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adapts the margin handles to fit the left, top and bottom margins.
     *
     * @private
     */
    _adaptMarginsPreviews: function () {
        var self = this;
        var ml = this.$target.css('margin-left');
        _.each(this.$overlay.find(".oe_handle.n, .oe_handle.s"), function (handle) {
            var $handle = $(handle);
            var direction = $handle.hasClass('n') ? 'top': 'bottom';
            $handle.height(self.$target.css('margin-' + direction));
        });
        this.$overlay.find(".oe_handle.w").css({
            width: ml,
            left: '-' + ml,
        });
    },
    /**
     * Returns an object whose keys indicate the different editable dimensions.
     *
     * @private
     * @returns {Object}
     */
    _getSize: function () {
        this.grid = {};
        return this.grid;
    },
    /**
     * Highlights the margins previews for a while.
     *
     * @private
     */
    _highlightMarginsPreviews: function () {
        var $handlers = this.$overlay.find(".oe_handle.n, .oe_handle.s, .oe_handle.w");
        $handlers.addClass('oe_handle_active').delay(300).queue(function () {
            $handlers.removeClass('oe_handle_active').dequeue();
        });
    },
    /**
     * Called when the snippet is being resized and its classes changes.
     *
     * @private
     * @param {string} compass - resize direction ('n', 's', 'e' or 'w')
     * @param {?} beginClass - attributes class at the beginning
     * @param {?} current - curent increment in this.grid
     */
    _onResize: function (compass, beginClass, current) {
        this._updateCursor();
    },
    /**
     * Adapts the resize handles according to the classes and dimensions.
     *
     * @private
     */
    _updateCursor : function () {
        var _class = this.$target.attr('class') || '';
        var $handle_s = this.$overlay.find('.oe_handle.s');
        var $handle_n = this.$overlay.find('.oe_handle.n');
        var $handle_w = this.$overlay.find('.oe_handle.w');

        var col = _class.match(/col-md-([0-9-]+)/i);
        col = col ? +col[1] : 0;

        var offset = _class.match(/col-md-offset-([0-9-]+)/i);
        offset = offset ? +offset[1] : 0;

        var overlay_class = this.$overlay.attr('class').replace(/(^|\s+)block-[^\s]*/gi, '');
        if (col+offset >= 12) overlay_class+= ' block-e-right';
        if (col === 1) overlay_class+= ' block-w-right block-e-left';
        if (offset === 0) overlay_class+= ' block-w-left';
        $handle_w.toggleClass('oe_handle_centered', offset > 0).toggleClass('o_handle_edited', offset >= 1 );

        var mb = _class.match(/mb([0-9-]+)/i);
        mb = mb ? +mb[1] : parseInt(this.$target.css('margin-bottom'));
        if (mb >= 128) overlay_class+= ' block-s-bottom';
        else if (!mb) overlay_class+= ' block-s-top';
        $handle_s.toggleClass('oe_handle_centered', mb >= 32).toggleClass('o_handle_edited', mb > 0 );

        var mt = _class.match(/mt([0-9-]+)/i);
        mt = mt ? +mt[1] : parseInt(this.$target.css('margin-top'));
        if (mt >= 128) overlay_class+= ' block-n-top';
        else if (!mt) overlay_class+= ' block-n-bottom';
        $handle_n.toggleClass('oe_handle_centered', mt >= 32).toggleClass('o_handle_edited', mt > 0 );

        this.$overlay.attr('class', overlay_class);
    },
});

/**
 * Handles the edition of margin-top and margin-bottom.
 */
registry['margin-y'] = registry.marginAndResize.extend({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getSize: function () {
        this.grid = this._super();
        var grid = [0,4,8,16,32,48,64,92,128];
        this.grid = {
            // list of class (Array), grid (Array), default value (INT)
            n: [_.map(grid, function (v) {return 'mt'+v;}), grid],
            s: [_.map(grid, function (v) {return 'mb'+v;}), grid],
            // INT if the user can resize the snippet (resizing per INT px)
            size: null
        };
        return this.grid;
    },
});

/**
 * Handles the edition of snippet's height.
 */
registry.resize = registry.marginAndResize.extend({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getSize: function () {
        this.grid = this._super();
        this.grid.size = 8;
        return this.grid;
    },
});

/**
 * Handles the edition of snippet's background color classes.
 */
registry.colorpicker = SnippetOption.extend({
    xmlDependencies: ['/web_editor/static/src/xml/snippets.xml'],
    events: _.extend({}, SnippetOption.prototype.events || {}, {
        'click .colorpicker button': '_onColorButtonClick',
        'mouseenter .colorpicker button': '_onColorButtonEnter',
        'mouseleave .colorpicker button': '_onColorButtonLeave',
        'click .note-color-reset': '_onColorResetButtonClick',
    }),

    /**
     * @override
     */
    start: function () {
        var self = this;
        var res = this._super.apply(this, arguments);

        if (!this.$el.find('.colorpicker').length) {
            var $pt = $(qweb.render('web_editor.snippet.option.colorpicker'));
            var $clpicker = $(qweb.render('web_editor.colorpicker'));

            // Retrieve excluded palettes list
            var excluded = [];
            if (this.data.paletteExclude) {
                excluded = this.data.paletteExclude.replace(/ /g, '').split(',');
            }
            // Apply a custom title if specified
            if (this.data.paletteTitle) {
                $pt.find('.note-palette-title').text(this.data.paletteTitle);
            }

            var $toggles = $pt.find('.o_colorpicker_section_menu');
            var $tabs = $pt.find('.o_colorpicker_section_tabs');

            // Remove excluded palettes
            _.each(excluded, function (exc) {
                $clpicker.find('[data-name="' + exc + '"]').remove();
            });

            var $sections = $clpicker.find('.o_colorpicker_section');

            if ($sections.length > 1) { // Multi-palette layout
                $sections.each(function () {
                    var $section = $(this);
                    var id = 'o_palette_' + $section.data('name') + _.uniqueId();

                    var $li = $('<li/>')
                                .append($('<a/>', {href: '#' + id})
                                    .append($('<i/>', {'class': $section.data('iconClass') || '', html: $section.data('iconContent') || ''})));
                    $toggles.append($li);

                    $tabs.append($section.addClass('tab-pane').attr('id', id));
                });

                // If a default palette is defined, make it active
                if (this.data.paletteDefault) {
                    var $palette_def = $tabs.find('div[data-name="' + self.data.paletteDefault + '"]');
                    var pos = $tabs.find('> div').index($palette_def);

                    $toggles.children('li').eq(pos).addClass('active');
                    $palette_def.addClass('active');
                } else {
                    $toggles.find('li').first().addClass('active');
                    $tabs.find('div').first().addClass('active');
                }

                $toggles.on('click mouseover', '> li > a', function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    $(this).tab('show');
                });
            } else if ($sections.length === 1) { // Unique palette layout
                $tabs.addClass('o_unique_palette').append($sections.addClass('tab-pane active'));
            } else {
                $toggles.parent().empty().append($clpicker);
            }

            this.$el.find('li').append($pt);
        }
        if (this.$el.data('area')) {
            this.$target = this.$target.find(this.$el.data('area'));
            this.$el.removeData('area').removeAttr('area');
        }

        var classes = [];
        this.$el.find('.colorpicker button').each(function () {
            var $color = $(this);
            if (!$color.data('color')) {
                return;
            }

            var className = 'bg-' + $color.data('color');
            $color.addClass(className);
            if (self.$target.hasClass(className)) {
                self.color = className;
                $color.addClass('selected');
            }
            classes.push(className);
        });
        this.classes = classes.join(' ');

        return res;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Called when a color button is clicked -> confirm the preview.
     *
     * @private
     * @param {Event} ev
     */
    _onColorButtonClick: function (ev) {
        this.$el.find('.colorpicker button.selected').removeClass('selected');
        $(ev.currentTarget).addClass('selected');
        this.$target.closest('.o_editable').trigger('content_changed');
        this.$target.trigger('background-color-event', ev.type);
    },
    /**
     * Called when a color button is entered -> preview the background color.
     *
     * @private
     * @param {Event} ev
     */
    _onColorButtonEnter: function (ev) {
        this.$target.removeClass(this.classes);
        var color = $(ev.currentTarget).data('color');
        if (color) {
            this.$target.addClass('bg-' + color);
        }
        this.$target.trigger('background-color-event', ev.type);
    },
    /**
     * Called when a color button is left -> cancel the preview.
     *
     * @private
     * @param {Event} ev
     */
    _onColorButtonLeave: function (ev) {
        this.$target.removeClass(this.classes);
        var $selected = this.$el.find('.colorpicker button.selected');
        var color = $selected.length && $selected.data('color');
        if (color) {
            this.$target.addClass('bg-' + color);
        }
        this.$target.trigger('background-color-event', ev.type);
    },
    /**
     * Called when the color reset button is clicked -> remove all background
     * color classes.
     *
     * @private
     */
    _onColorResetButtonClick: function () {
        this.$target.removeClass(this.classes);
        this.$target.trigger('content_changed');
        this.$el.find('.colorpicker button.selected').removeClass('selected');
    },
});

/**
 * Handles the edition of snippet's background image.
 */
registry.background = SnippetOption.extend({
    /**
     * @override
     */
    start: function () {
        var res = this._super.apply(this, arguments);
        this.bindBackgroundEvents();
        this.__customImageSrc = this._getSrcFromCssValue();
        return res;
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Handles a background change.
     *
     * @see this.selectClass for parameters
     */
    background: function (previewMode, value, $li) {
        if (previewMode === 'reset' && value === undefined) {
            // No background has been selected and we want to reset back to the
            // original custom image
            this._setCustomBackground(this.__customImageSrc);
            return;
        }

        if (value && value.length) {
            this.$target.css('background-image', 'url(\'' + value + '\')');
            this.$target.removeClass('oe_custom_bg').addClass('oe_img_bg');
        } else {
            this.$target.css('background-image', '');
            this.$target.removeClass('oe_img_bg oe_custom_bg');
        }
    },
    /**
     * @override
     */
    selectClass: function (previewMode, value, $li) {
        this.background(previewMode, '', $li);
        this._super(previewMode, value ? (value + ' oe_img_bg') : value, $li);
    },
    /**
     * Opens a media dialog to add a custom background image.
     *
     * @see this.selectClass for parameters
     */
    chooseImage: function (previewMode, value, $li) {
        // Put fake image in the DOM, edit it and use it as background-image
        var $image = $('<img/>', {class: 'hidden', src: value}).appendTo(this.$target);

        var $editable = this.$target.closest('.o_editable');
        var options = {
            res_model: $editable.data('oe-model'),
            res_id: $editable.data('oe-id'),
        };
        var _editor = new widget.MediaDialog(this, options, null, $image[0]).open();
        _editor.opened(function () {
            _editor.$('[href="#editor-media-video"], [href="#editor-media-icon"]').addClass('hidden');
        });

        _editor.on('save', this, function () {
            this._setCustomBackground($image.attr('src'));
        });
        _editor.on('closed', this, function () {
            $image.remove();
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Attaches events so that when a background-color is set, the background
     * image is removed.
     */
    bindBackgroundEvents: function () {
        this.$target.off('.background-option')
            .on('background-color-event.background-option', (function (e, type) {
                e.stopPropagation();
                if (e.currentTarget !== e.target) return;
                this.$el.find('li[data-background=""] > a').trigger(type);
            }).bind(this));
    },
    /**
     * @override
     */
    setTarget: function () {
        this._super.apply(this, arguments);
        // TODO should be automatic for all options as equal to the start method
        this.bindBackgroundEvents();
        this.__customImageSrc = this._getSrcFromCssValue();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns the src value from a css value related to a background image
     * (e.g. "url('blabla')" => "blabla" / "none" => "").
     *
     * @private
     * @param {string} value
     * @returns {string}
     */
    _getSrcFromCssValue: function (value) {
        if (value === undefined) {
            value = this.$target.css('background-image');
        }
        return value.replace(/url\(['"]*|['"]*\)|^none$/g, '');
    },
    /**
     * @override
     */
    _setActive: function () {
        this._super.apply(this, arguments);

        var src = this._getSrcFromCssValue();
        this.$el.find('li[data-background]')
            .removeClass('active')
            .filter(function () {
                var bgOption = $(this).data('background');
                return (bgOption === '' && src === '' || bgOption !== '' && src.indexOf(bgOption) >= 0);
            })
            .addClass('active');

        this.$el.find('li[data-choose-image]').toggleClass('active', this.$target.hasClass('oe_custom_bg'));
    },
    /**
     * Sets the given value as custom background image.
     *
     * @private
     * @param {string} value
     */
    _setCustomBackground: function (value) {
        this.__customImageSrc = this._getSrcFromCssValue(value);
        this.background(false, this.__customImageSrc);
        this.$target.addClass('oe_custom_bg');
        this._setActive();
        this.$target.trigger('snippet-option-change', [this]);
    },
});

/**
 * Handles the edition of snippet's background image position.
 */
registry.background_position = SnippetOption.extend({
    xmlDependencies: ['/web_editor/static/src/xml/editor.xml'],

    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);
        var self = this;
        this.$target.on('snippet-option-change', function () {
            self.onFocus();
        });
    },
    /**
     * @override
     */
    onFocus: function () {
        this.$el.toggleClass('hidden', this.$target.css('background-image') === 'none');
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Opens a Dialog to edit the snippet's backgroung image position.
     *
     * @see this.selectClass for parameters
     */
    backgroundPosition: function (previewMode, value, $li) {
        var self = this;

        this.previous_state = [this.$target.attr('class'), this.$target.css('background-size'), this.$target.css('background-position')];

        this.bg_pos = self.$target.css('background-position').split(' ');
        this.bg_siz = self.$target.css('background-size').split(' ');

        this.modal = new Dialog(null, {
            title: _t("Background Image Sizing"),
            $content: $(qweb.render('web_editor.dialog.background_position')),
            buttons: [
                {text: _t("Ok"), classes: 'btn-primary', close: true, click: _.bind(this._saveChanges, this)},
                {text: _t("Discard"), close: true, click: _.bind(this._discardChanges, this)},
            ],
        }).open();

        this.modal.opened().then(function () {
            // Fetch data form $target
            var value = ((self.$target.hasClass('o_bg_img_opt_contain'))? 'contain' : ((self.$target.hasClass('o_bg_img_opt_custom'))? 'custom' : 'cover'));
            self.modal.$('> label > input[value=' + value + ']').prop('checked', true);

            if (self.$target.hasClass('o_bg_img_opt_repeat')) {
                self.modal.$('#o_bg_img_opt_contain_repeat').prop('checked', true);
                self.modal.$('#o_bg_img_opt_custom_repeat').val('o_bg_img_opt_repeat');
            } else if (self.$target.hasClass('o_bg_img_opt_repeat_x')) {
                self.modal.$('#o_bg_img_opt_custom_repeat').val('o_bg_img_opt_repeat_x');
            } else if (self.$target.hasClass('o_bg_img_opt_repeat_y')) {
                self.modal.$('#o_bg_img_opt_custom_repeat').val('o_bg_img_opt_repeat_y');
            }

            if (self.bg_pos.length > 1) {
                self.bg_pos = {
                    x: self.bg_pos[0],
                    y: self.bg_pos[1],
                };
                self.modal.$('#o_bg_img_opt_custom_pos_x').val(self.bg_pos.x.replace('%', ''));
                self.modal.$('#o_bg_img_opt_custom_pos_y').val(self.bg_pos.y.replace('%', ''));
            }
            if (self.bg_siz.length > 1) {
                self.modal.$('#o_bg_img_opt_custom_size_x').val(self.bg_siz[0].replace('%', ''));
                self.modal.$('#o_bg_img_opt_custom_size_y').val(self.bg_siz[1].replace('%', ''));
            }

            // Focus Point
            self.$focus  = self.modal.$('.o_focus_point');
            self._updatePosInformation();

            var img_url = /\(['"]?([^'"]+)['"]?\)/g.exec(self.$target.css('background-image'));
            img_url = (img_url && img_url[1]) || '';
            var $img = $('<img/>', {class: 'img img-responsive', src: img_url});
            $img.on('load', function () {
                self._bindImageEvents($img);
            });
            $img.prependTo(self.modal.$('.o_bg_img_opt_object'));

            // Bind events
            self.modal.$el.on('change', '> label > input', function (e) {
                self.modal.$('> .o_bg_img_opt').addClass('o_hidden')
                                               .filter('[data-value=' + e.target.value + ']')
                                               .removeClass('o_hidden');
            });
            self.modal.$el.on('change', 'input, select', function (e) {
                self._saveChanges();
            });
            self.modal.$('> label > input:checked').trigger('change');
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Bind events on the given image so that the users can adapt the focus
     * point.
     *
     * @private
     * @param {jQuery} $img
     */
    _bindImageEvents: function ($img) {
        var self = this;

        var mousedown = false;
        $img.on('mousedown', function (e) {
            mousedown = true;
        });
        $img.on('mousemove', function (e) {
            if (mousedown) {
                _update(e);
            }
        });
        $img.on('mouseup', function (e) {
            self.$focus.addClass('o_with_transition');
            _update(e);
            setTimeout(function () {
                self.$focus.removeClass('o_with_transition');
            }, 200);
            mousedown = false;
        });

        function _update(e) {
            var posX = e.pageX - $(e.target).offset().left;
            var posY = e.pageY - $(e.target).offset().top;
            self.bg_pos = {
                x: clipValue(posX/$img.width()*100).toFixed(2) + '%',
                y: clipValue(posY/$img.height()*100).toFixed(2) + '%',
            };
            self._updatePosInformation();
            self._saveChanges();

            function clipValue(value) {
                return Math.max(0, Math.min(value, 100));
            }
        }
    },
    /**
     * Removes all option-related classes and style on the target element.
     *
     * @private
     */
    _clean: function () {
        this.$target.removeClass('o_bg_img_opt_contain o_bg_img_opt_custom o_bg_img_opt_repeat o_bg_img_opt_repeat_x o_bg_img_opt_repeat_y')
                    .css({
                        'background-size': '',
                        'background-position': '',
                    });
    },
    /**
     * Restores the target style before last edition made with the option.
     *
     * @private
     */
    _discardChanges: function () {
        this._clean();
        if (this.previous_state) {
            this.$target.addClass(this.previous_state[0]).css({
                'background-size': this.previous_state[1],
                'background-position': this.previous_state[2],
            });
        }
    },
    /**
     * Updates the visual representation of the chosen background position.
     *
     * @private
     */
    _updatePosInformation: function () {
        this.modal.$('.o_bg_img_opt_ui_info .o_x').text(this.bg_pos.x);
        this.modal.$('.o_bg_img_opt_ui_info .o_y').text(this.bg_pos.y);
        this.$focus.css({
            left: this.bg_pos.x,
            top: this.bg_pos.y,
        });
    },
    /**
     * Updates the target element to match the chosen options.
     *
     * @private
     */
    _saveChanges: function () {
        this._clean();

        var bg_img_size = this.modal.$('> :not(label):not(.o_hidden)').data('value') || 'cover';
        switch (bg_img_size) {
            case 'cover':
                this.$target.css('background-position', this.bg_pos.x + ' ' + this.bg_pos.y);
                break;
            case 'contain':
                this.$target.addClass('o_bg_img_opt_contain');
                this.$target.toggleClass('o_bg_img_opt_repeat', this.modal.$('#o_bg_img_opt_contain_repeat').prop('checked'));
                break;
            case 'custom':
                this.$target.addClass('o_bg_img_opt_custom');
                var sizeX = this.modal.$('#o_bg_img_opt_custom_size_x').val();
                var sizeY = this.modal.$('#o_bg_img_opt_custom_size_y').val();
                var posX = this.modal.$('#o_bg_img_opt_custom_pos_x').val();
                var posY = this.modal.$('#o_bg_img_opt_custom_pos_y').val();
                this.$target.addClass(this.modal.$('#o_bg_img_opt_custom_repeat').val())
                            .css({
                                'background-size': ((sizeX)? sizeX + '%' : 'auto') + ' ' + ((sizeY)? sizeY + '%' : 'auto'),
                                'background-position': ((posX)? posX + '%' : 'auto') + ' ' + ((posY)? posY + '%' : 'auto'),
                            });
                break;
        }
    },
});

/**
 * Allows to replace a text value with the name of a database record.
 * @todo replace this mechanism with real backend m2o field ?
 */
registry.many2one = SnippetOption.extend({
    xmlDependencies: ['/web_editor/static/src/xml/snippets.xml'],
    /**
     * @override
     */
    start: function () {
        var self = this;

        this.Model = this.$target.data('oe-many2one-model');
        this.ID = +this.$target.data('oe-many2one-id');

        // create search button and bind search bar
        this.$btn = $(qweb.render('web_editor.many2one.button'))
            .insertAfter(this.$overlay.find('.oe_options'));

        this.$ul = this.$btn.find('ul');
        this.$search = this.$ul.find('li:first');
        this.$search.find('input').on('mousedown click mouseup keyup keydown', function (e) {
            e.stopPropagation();
        });

        // move menu item
        setTimeout(function () {
            if (self.$overlay.find('.oe_options').hasClass('hidden')) {
                self.$btn.css('height', '0').find('> a').addClass('hidden');
                self.$ul.show().css({
                    'top': '-24px', 'margin': '0', 'padding': '2px 0', 'position': 'relative'
                });
            } else {
                self.$btn.find('a').on('click', function (e) {
                    self._clear();
                });
            }
        },0);

        // bind search input
        this.$search.find('input')
            .focus()
            .on('keyup', function (e) {
                self._findExisting($(this).val());
            });

        // bind result
        this.$ul.on('click', 'li:not(:first) a', function (e) {
            self._selectRecord($(e.currentTarget));
        });

        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    onFocus: function () {
        this.$target.attr('contentEditable', 'false');
        this._clear();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Removes the input value and suggestions.
     *
     * @private
     */
    _clear: function () {
        var self = this;
        this.$search.siblings().remove();
        self.$search.find('input').val('');
        setTimeout(function () {
            self.$search.find('input').focus();
        }, 0);
    },
    /**
     * Find existing record with the given name and suggest them.
     *
     * @private
     * @param {string} name
     * @returns {Deferred}
     */
    _findExisting: function (name) {
        var self = this;
        var domain = [];
        if (!name || !name.length) {
            self.$search.siblings().remove();
            return;
        }
        if (isNaN(+name)) {
            if (this.Model !== 'res.partner') {
                domain.push(['name', 'ilike', name]);
            } else {
                domain.push('|', ['name', 'ilike', name], ['email', 'ilike', name]);
            }
        } else {
            domain.push(['id', '=', name]);
        }

        return this._rpc({
            model: this.Model,
            method: 'search_read',
            args: [domain, this.Model === 'res.partner' ? ['name', 'display_name', 'city', 'country_id'] : ['name', 'display_name']],
            kwargs: {
                order: [{name: 'name', asc: false}],
                limit: 5,
                context: weContext.get(),
            },
        }).then(function (result) {
            self.$search.siblings().remove();
            self.$search.after(qweb.render('web_editor.many2one.search',{contacts:result}));
        });
    },
    /**
     * Selects the given suggestion and displays it the proper way.
     *
     * @private
     * @param {jQuery} $li
     */
    _selectRecord: function ($li) {
        var self = this;

        this.ID = +$li.data('id');
        this.$target.attr('data-oe-many2one-id', this.ID).data('oe-many2one-id', this.ID);

        this.trigger_up('request_history_undo_record', {$target: this.$target});
        this.$target.trigger('content_changed');

        if (self.$target.data('oe-type') === 'contact') {
            $('[data-oe-contact-options]')
                .filter('[data-oe-model="'+self.$target.data('oe-model')+'"]')
                .filter('[data-oe-id="'+self.$target.data('oe-id')+'"]')
                .filter('[data-oe-field="'+self.$target.data('oe-field')+'"]')
                .filter('[data-oe-contact-options!="'+self.$target.data('oe-contact-options')+'"]')
                .add(self.$target)
                .attr('data-oe-many2one-id', self.ID).data('oe-many2one-id', self.ID)
                .each(function () {
                    var $node = $(this);
                    var options = $node.data('oe-contact-options');
                    self._rpc({
                        model: 'ir.qweb.field.contact',
                        method: 'get_record_to_html',
                        args: [[self.ID]],
                        kwargs: {
                            options: options,
                            context: weContext.get(),
                        },
                    }).then(function (html) {
                        $node.html(html);
                    });
                });
        } else {
            self.$target.html($li.data('name'));
        }

        _.defer(function () {
            self.trigger_up('deactivate_snippet');
        });
    }
});

return {
    Class: SnippetOption,
    registry: registry,
};
});
