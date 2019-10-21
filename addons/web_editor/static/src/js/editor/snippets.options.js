odoo.define('web_editor.snippets.options', function (require) {
'use strict';

var core = require('web.core');
var ColorPaletteWidget = require('web_editor.ColorPalette').ColorPaletteWidget;
var Dialog = require('web.Dialog');
var rte = require('web_editor.rte');
var Widget = require('web.Widget');
var weWidgets = require('wysiwyg.widgets');

var qweb = core.qweb;
var _t = core._t;

const CSS_SHORTHANDS = {
    'border-width': ['border-top-width', 'border-right-width', 'border-bottom-width', 'border-left-width'],
    'border-radius': ['border-top-left-radius', 'border-top-right-radius', 'border-bottom-right-radius', 'border-bottom-left-radius'],
};

/**
 * Handles a set of options for one snippet. The registry returned by this
 * module contains the names of the specialized SnippetOption which can be
 * referenced thanks to the data-js key in the web_editor options template.
 */
var SnippetOption = Widget.extend({
    events: {
        'mouseenter we-button': '_onOptionPreview',
        'click we-button': '_onOptionSelection',
        'input we-input input': '_onOptionSelection',
        'blur we-input input': '_onOptionInputBlur',
        'mouseleave we-button': '_onOptionCancel',
    },

    /**
     * The option `$el` is supposed to be the associated DOM UI element.
     * The option controls another DOM element: the snippet it
     * customizes, which can be found at `$target`. Access to the whole edition
     * overlay is possible with `$overlay` (this is not recommended though).
     *
     * @constructor
     */
    init: function (parent, $target, $overlay, data, options) {
        this._super.apply(this, arguments);
        this.options = options;
        this.$target = $target;
        this.ownerDocument = this.$target[0].ownerDocument;
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
        this._updateUI();
        return this._super.apply(this, arguments);
    },
    /**
     * Indicates if the option should be displayed in the button group at the
     * top of the options panel, next to the clone/remove button.
     */
    isTopOption: function () {
        return false;
    },
    /**
     * Called when the parent edition overlay is covering the associated snippet
     * (the first time, this follows the call to the @see start method).
     *
     * @abstract
     */
    onFocus: function () {},
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
    onBlur: function () {},
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
     * Default option method which allows to handle an user input and set the
     * appropriate css style on the associated snippet.
     *
     * @param {boolean} previewMode - always false for this method
     * @param {Object} value - the cssProp to customize
     * @param {jQuery} $opt - the related DOMElement option
     */
    setStyle: function (previewMode, value, $opt) {
        let hasUserValue = false;
        const cssProps = CSS_SHORTHANDS[value] || [value];

        // Join all inputs controlling the same css property and split user
        // input into sub-properties (note this code handles the two at the same
        // time but should normally not be combined).
        const $weInputs = this.$el.find(`[data-set-style=${value}]`);
        const subValuesByInput = _.map($weInputs, weInput => {
            const value = weInput.querySelector('input').value;
            const defaultValue = weInput.dataset.defaultValue;
            if (!value) {
                return _.times(cssProps.length, () => defaultValue);
            }
            const unit = weInput.dataset.unit;
            const values = value.trim().split(/\s+/g).map(v => {
                v = parseFloat(v);
                if (isNaN(v)) {
                    return defaultValue;
                } else {
                    hasUserValue = true;
                    return (v + unit);
                }
            });
            while (values.length < cssProps.length) {
                switch (values.length) {
                    case 1:
                    case 2:
                        values.push(values[0]);
                        break;
                    case 3:
                        values.push(values[1]);
                        break;
                    default:
                        values.push(values[values.length - 1]);
                }
            }
            return values;
        });

        for (const cssProp of cssProps) {
            // Always reset the inline style first to not put inline style on an
            // element which already have this style through css stylesheets.
            this.$target[0].style.setProperty(cssProp, '');
        }
        const styles = window.getComputedStyle(this.$target[0]);
        cssProps.forEach((cssProp, i) => {
            const cssValue = subValuesByInput.map(inputSubValues => inputSubValues[i]).join(' ');
            if (styles[cssProp] !== cssValue) {
                this.$target[0].style.setProperty(cssProp, cssValue, 'important');
            }
        });

        var toggleClass = $opt[0].dataset.toggleClass;
        if (toggleClass) {
            this.$target.toggleClass(toggleClass, hasUserValue);
        }
    },
    /**
     * Default option method which allows to select one and only one class in
     * the option classes set and set it on the associated snippet. The common
     * case is having a sub-collapse with each item having a `data-select-class`
     * value allowing to choose the associated class.
     *
     * @param {boolean|string} previewMode
     *        - truthy if the option is enabled for preview or if leaving it (in
     *          that second case, the value is 'reset')
     *        - false if the option should be activated for good
     * @param {*} value - the class to activate ($opt.data('selectClass'))
     * @param {jQuery} $opt - the related DOMElement option
     */
    selectClass: function (previewMode, value, $opt) {
        var $group = $opt && $opt.parents('we-collapse-area, we-select').last();
        if (!$group || !$group.length) {
            $group = this.$el;
        }
        var $lis = $group.find('[data-select-class]');
        var classes = $lis.map(function () {
            return $(this).data('selectClass');
        }).get().join(' ');

        this.$target.removeClass(classes);
        if (value) {
            this.$target.addClass(value);
        }
    },
    /**
     * Default option method which allows to select one or multiple classes in
     * the option classes set and set it on the associated snippet. The common
     * case is having a sub-collapse with each item having a `data-toggle-class`
     * value allowing to toggle the associated class.
     *
     * @see this.selectClass
     */
    toggleClass: function (previewMode, value, $opt) {
        const $opts = this.$el.find('[data-toggle-class]').not('[data-set-style]');
        const classes = $opts.map(function () {
            return $(this).data('toggleClass');
        }).get().join(' ');
        const activeClasses = $opts.filter('.active, :has(.active)').map(function () {
            return $(this).data('toggleClass');
        }).get().join(' ');

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
     * of the UI item element.
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
        this._updateUI();
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
        var $actives = this.$el.find('we-button.active');
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
     * @param {jQuery} $opt - the related DOMElement option
     */
    _select: function (previewMode, $opt) {
        // Options can say they respond to strong choice
        if (previewMode && ($opt.data('noPreview') || $opt.closest('[data-no-preview="true"]').length)) {
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
        var el = $opt[0];
        var methods = [];
        do {
            methods.push([el, el.dataset]);
            el = el.parentNode;
        } while (this.$el.parent().has(el).length);

        // Call the found method in the right order (parents -> child)
        methods.reverse().forEach(data => {
            var $el = $(data[0]);
            var methods = data[1];

            let methodNames = Object.keys(methods);
            if (methodNames.includes('setStyle')) {
                methodNames = ['setStyle'];
            }

            methodNames.forEach(methodName => {
                if (!this[methodName]) {
                    return;
                }
                if (previewMode === true) {
                    this.__methodNames.push(methodName);
                }
                this[methodName](previewMode, methods[methodName], $el);
            });
        });
        this.__methodNames = _.uniq(this.__methodNames);

        if (!previewMode) {
            this._updateUI();
        }

        this.$target.trigger('content_changed');
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

        // --- TOGGLE CLASS ---

        this.$el.find('[data-toggle-class]')
            .removeClass('active')
            .filter(function () {
                var className = $(this).data('toggleClass');
                return !className || self.$target.hasClass(className);
            })
            .addClass('active');

        // --- SELECT CLASS ---

        // Get submenus which are not inside submenus
        var $submenus = this.$el.find('we-collapse-area, we-select')
            .not('we-collapse-area *, we-select *');

        // Add unique active class for each submenu active item
        _.each($submenus, function (submenu) {
            var $elements = $(submenu).find('[data-select-class]');
            _processSelectClassElements($elements);
        });

        // Add unique active class for out-of-submenu active item
        var $externalElements = this.$el.find('[data-select-class]')
            .not('we-collapse-area *, we-select *');
        _processSelectClassElements($externalElements);

        function _processSelectClassElements($elements) {
            var maxNbClasses = -1;
            $elements.removeClass('active')
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

        // --- INPUT VALUE --- (note: important to be done last because of active removal)

        let styles;
        const seenSetStyles = [];
        this.el.querySelectorAll('[data-set-style]').forEach(el => {
            const cssProp = el.dataset.setStyle;
            if (seenSetStyles.includes(cssProp)) {
                return;
            }
            seenSetStyles.push(cssProp);

            const $els = this.$el.find(`[data-set-style="${cssProp}"]`);
            $els.removeClass('active');
            const $inputs = $els.find('> input');
            if (_.any($inputs, input => input === document.activeElement)) {
                return;
            }

            styles = styles || window.getComputedStyle(this.$target[0]);
            const cssProps = CSS_SHORTHANDS[cssProp] || [cssProp];

            const valuesByProp = cssProps.map(cssProp => {
                const cssValue = styles[cssProp];

                return cssValue.split(/\s+/).map((v, i) => {
                    const unit = $els[i].dataset.unit;
                    return v.endsWith(unit) ? parseFloat(v) : ''; // TODO convert to the right unit (+ ms finishes by s)
                });
            });
            _.each($els, (el, i) => {
                const values = valuesByProp.map(propValues => propValues[i]);

                const EPS = 0.0001;
                if (values.length === 4 && Math.abs(values[3] - values[1]) < EPS) {
                    values.pop();
                }
                if (values.length === 3 && Math.abs(values[2] - values[0]) < EPS) {
                    values.pop();
                }
                if (values.length === 2 && Math.abs(values[1] - values[0]) < EPS) {
                    values.pop();
                }
                if (values.length === 1 && values[0] === parseFloat(el.dataset.defaultValue)) { // FIXME
                    values.pop();
                }
                $inputs[i].value = (values.length ? values.join(' ') : '');
            });
        });
    },
    /**
     * @private
     */
    _updateUI: function () {
        this._setActive();

        this.el.querySelectorAll('we-select').forEach(selectEl => {
            const activeEl = selectEl.querySelector('we-button.active');
            const valueEl = selectEl.querySelector('we-toggler');
            if (valueEl) {
                valueEl.textContent = activeEl ? activeEl.textContent : "/";
            }
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onOptionInputBlur: function (ev) {
        // Sometimes, an input is focusout for internal reason (like an undo
        // recording) then focused again manually in the same JS stack
        // execution. In that case, the blur should not trigger an option
        // selection as the user did not leave the input. We thus defer the blur
        // handling to then check that the target is indeed still blurred before
        // executing the actual option selection.
        setTimeout(() => {
            if (ev.currentTarget === document.activeElement) {
                return;
            }
            this._onOptionSelection(ev);
        });
    },
    /**
     * Called when a option link is entered or an option input content is being
     * modified -> activates the related option in preview mode.
     *
     * @private
     * @param {Event} ev
     */
    _onOptionPreview: function (ev) {
        var $opt = $(ev.target).closest('we-button, we-input');
        if (!$opt.length) {
            return;
        }

        if (!$opt.is(':hasData')) {
            return;
        }
        this.__click = false;
        this._select(true, $opt);
        this.$target.trigger('snippet-option-preview', [this]);
    },
    /**
     * Called when an option link is clicked or an option input content is
     * validated -> activates the related option.
     *
     * @private
     * @param {Event} ev
     */
    _onOptionSelection: function (ev) {
        var $opt = $(ev.target).closest('we-button, we-input');
        if (ev.isDefaultPrevented() || !$opt.length || !$opt.is(':hasData')) {
            return;
        }

        ev.preventDefault();
        this.__click = true;
        this._select(false, $opt);
        this.$target.trigger('snippet-option-change', [this]);
    },
    /**
     * Called when an option link/menu is left -> reactivate the options that
     * were activated before previews.
     *
     * @private
     */
    _onOptionCancel: function () {
        if (this.__click) {
            return;
        }
        this._reset();
    },

    //--------------------------------------------------------------------------
    // Static
    //--------------------------------------------------------------------------

    /**
     * Build the correct DOM for a we-checkbox element.
     *
     * @static
     * @param {HTMLElement} checkboxEl
     */
    buildCheckboxElement: function (checkboxEl) {
        var titleEl = SnippetOption.prototype.stringToTitle(checkboxEl);

        var buttonEl = document.createElement('we-button');
        buttonEl.classList.add('o_we_checkbox_wrapper');
        checkboxEl.classList.forEach(className => buttonEl.classList.add(className));
        checkboxEl.setAttribute('class', '');
        for (const key in checkboxEl.dataset) {
            buttonEl.dataset[key] = checkboxEl.dataset[key];
            delete checkboxEl.dataset[key];
        }

        checkboxEl.parentNode.insertBefore(buttonEl, checkboxEl);
        buttonEl.appendChild(titleEl);
        buttonEl.appendChild(checkboxEl);
    },
    /**
     * Build the correct DOM for a we-group element.
     *
     * @static
     * @param {HTMLElement} groupEl
     */
    buildGroupElement: function (groupEl) {
        var titleEl = SnippetOption.prototype.stringToTitle(groupEl);

        if (groupEl.firstChild) {
            groupEl.insertBefore(titleEl, groupEl.firstChild);
        } else {
            groupEl.appendChild(titleEl);
        }
    },
    /**
     * Build the correct DOM for a we-input element.
     *
     * @static
     * @param {HTMLElement} inputWrapperEl
     */
    buildInputElement: function (inputWrapperEl) {
        var titleEl = SnippetOption.prototype.stringToTitle(inputWrapperEl);

        var inputEl = document.createElement('input');
        inputEl.setAttribute('type', 'text');

        var unit = inputWrapperEl.dataset.unit || 'px';
        inputWrapperEl.dataset.unit = unit;
        var unitEl = document.createElement('span');
        unitEl.textContent = unit;

        var defaultValue = inputWrapperEl.dataset.defaultValue || ('0' + unit);
        inputWrapperEl.dataset.defaultValue = defaultValue;
        inputEl.setAttribute('placeholder', defaultValue.replace(unit, ''));

        inputWrapperEl.appendChild(titleEl);
        inputWrapperEl.appendChild(inputEl);
        inputWrapperEl.appendChild(unitEl);
    },
    /**
     * Build the correct DOM for a we-select element.
     *
     * @static
     * @param {HTMLElement} el
     */
    buildSelectElement: function (selectEl) {
        var titleEl = SnippetOption.prototype.stringToTitle(selectEl);

        var menuTogglerEl = document.createElement('we-toggler');

        var menuEl = document.createElement('we-select-menu');
        while (selectEl.firstChild) {
            menuEl.appendChild(selectEl.firstChild);
        }

        selectEl.appendChild(titleEl);
        selectEl.appendChild(menuTogglerEl);
        selectEl.appendChild(menuEl);
    },
    /**
     * @static
     * @param {HTMLElement} el
     */
    stringToTitle: function (el) {
        var titleEl = document.createElement('we-title');
        titleEl.textContent = el.getAttribute('string');
        el.removeAttribute('string');
        return titleEl;
    },
});

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

/**
 * The registry object contains the list of available options.
 */
var registry = {};

registry.sizing = SnippetOption.extend({
    /**
     * @override
     */
    start: function () {
        var self = this;
        var def = this._super.apply(this, arguments);

        this.$handles = this.$overlay.find('.o_handle');

        var resizeValues = this._getSize();
        this.$handles.on('mousedown', function (ev) {
            ev.preventDefault();

            var $handle = $(ev.currentTarget);

            var compass = false;
            var XY = false;
            if ($handle.hasClass('n')) {
                compass = 'n';
                XY = 'Y';
            } else if ($handle.hasClass('s')) {
                compass = 's';
                XY = 'Y';
            } else if ($handle.hasClass('e')) {
                compass = 'e';
                XY = 'X';
            } else if ($handle.hasClass('w')) {
                compass = 'w';
                XY = 'X';
            }

            var resize = resizeValues[compass];
            if (!resize) {
                return;
            }

            var current = 0;
            var cssProperty = resize[2];
            var cssPropertyValue = parseInt(self.$target.css(cssProperty));
            _.each(resize[0], function (val, key) {
                if (self.$target.hasClass(val)) {
                    current = key;
                } else if (resize[1][key] === cssPropertyValue) {
                    current = key;
                }
            });
            var begin = current;
            var beginClass = self.$target.attr('class');
            var regClass = new RegExp('\\s*' + resize[0][begin].replace(/[-]*[0-9]+/, '[-]*[0-9]+'), 'g');

            var cursor = $handle.css('cursor') + '-important';
            var $body = $(this.ownerDocument.body);
            $body.addClass(cursor);

            var xy = ev['page' + XY];
            var bodyMouseMove = function (ev) {
                ev.preventDefault();

                var dd = ev['page' + XY] - xy + resize[1][begin];
                var next = current + (current + 1 === resize[1].length ? 0 : 1);
                var prev = current ? (current - 1) : 0;

                var change = false;
                if (dd > (2 * resize[1][next] + resize[1][current]) / 3) {
                    self.$target.attr('class', (self.$target.attr('class') || '').replace(regClass, ''));
                    self.$target.addClass(resize[0][next]);
                    current = next;
                    change = true;
                }
                if (prev !== current && dd < (2 * resize[1][prev] + resize[1][current]) / 3) {
                    self.$target.attr('class', (self.$target.attr('class') || '').replace(regClass, ''));
                    self.$target.addClass(resize[0][prev]);
                    current = prev;
                    change = true;
                }

                if (change) {
                    self._onResize(compass, beginClass, current);
                    self.trigger_up('cover_update');
                    $handle.addClass('o_active');
                }
            };
            var bodyMouseUp = function () {
                $body.off('mousemove', bodyMouseMove);
                $body.off('mouseup', bodyMouseUp);
                $body.removeClass(cursor);
                $handle.removeClass('o_active');

                // Highlights the previews for a while
                var $handlers = self.$overlay.find('.o_handle');
                $handlers.addClass('o_active').delay(300).queue(function () {
                    $handlers.removeClass('o_active').dequeue();
                });

                if (begin === current) {
                    return;
                }
                setTimeout(function () {
                    self.trigger_up('request_history_undo_record', {
                        $target: self.$target,
                        event: 'resize_' + XY,
                    });
                }, 0);
            };
            $body.on('mousemove', bodyMouseMove);
            $body.on('mouseup', bodyMouseUp);
        });

        return def;
    },
    /**
     * @override
     */
    onFocus: function () {
        var resizeValues = this._getSize();
        _.each(resizeValues, (value, key) => {
            this.$handles.filter('.' + key).toggleClass('readonly', !value);
        });

        this._onResize();
    },
    /**
     * @override
     */
    onBlur: function () {
        this.$handles.addClass('readonly');
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    setTarget: function () {
        this._super.apply(this, arguments);
        this._onResize();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns an object mapping one or several cardinal direction (n, e, s, w)
     * to an Array containing:
     * 1) A list of classes to toggle when using this cardinal direction
     * 2) A list of values these classes are supposed to set on a given CSS prop
     * 3) The mentioned CSS prop
     *
     * Note: this object must also be saved in this.grid before being returned.
     *
     * @abstract
     * @private
     * @returns {Object}
     */
    _getSize: function () {},
    /**
     * Called when the snippet is being resized and its classes changes.
     *
     * @private
     * @param {string} [compass] - resize direction ('n', 's', 'e' or 'w')
     * @param {string} [beginClass] - attributes class at the beginning
     * @param {integer} [current] - current increment in this.grid
     */
    _onResize: function (compass, beginClass, current) {
        var self = this;

        // Adapt the resize handles according to the classes and dimensions
        var resizeValues = this._getSize();
        var $handles = this.$overlay.find('.o_handle');
        _.each(resizeValues, function (resizeValue, direction) {
            var classes = resizeValue[0];
            var values = resizeValue[1];
            var cssProperty = resizeValue[2];

            var $handle = $handles.filter('.' + direction);

            var current = 0;
            var cssPropertyValue = parseInt(self.$target.css(cssProperty));
            _.each(classes, function (className, key) {
                if (self.$target.hasClass(className)) {
                    current = key;
                } else if (values[key] === cssPropertyValue) {
                    current = key;
                }
            });

            $handle.toggleClass('o_handle_start', current === 0);
            $handle.toggleClass('o_handle_end', current === classes.length - 1);
        });

        // Adapt the handles to fit the left, top and bottom sizes
        var ml = this.$target.css('margin-left');
        this.$overlay.find('.o_handle.w').css({
            width: ml,
            left: '-' + ml,
        });
        this.$overlay.find('.o_handle.e').css({
            width: 0,
        });
        _.each(this.$overlay.find(".o_handle.n, .o_handle.s"), function (handle) {
            var $handle = $(handle);
            var direction = $handle.hasClass('n') ? 'top': 'bottom';
            $handle.height(self.$target.css('padding-' + direction));
        });
    },
});

/**
 * Handles the edition of padding-top and padding-bottom.
 */
registry['sizing_y'] = registry.sizing.extend({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getSize: function () {
        var nClass = 'pt';
        var nProp = 'padding-top';
        var sClass = 'pb';
        var sProp = 'padding-bottom';
        if (this.$target.is('hr')) {
            nClass = 'mt';
            nProp = 'margin-top';
            sClass = 'mb';
            sProp = 'margin-bottom';
        }

        var grid = [];
        for (var i = 0; i <= (256 / 8); i++) {
            grid.push(i * 8);
        }
        grid.splice(1, 0, 4);
        this.grid = {
            n: [grid.map(v => nClass + v), grid, nProp],
            s: [grid.map(v => sClass + v), grid, sProp],
        };
        return this.grid;
    },
});

/**
 * Handles the edition of snippet's background color classes.
 */
registry.colorpicker = SnippetOption.extend({
    xmlDependencies: ['/web_editor/static/src/xml/snippets.xml'],
    custom_events: {
        color_picked: '_onColorPicked',
        custom_color_picked: '_onCustomColor',
        color_hover: '_onColorHovered',
        color_leave: '_onColorLeft',
        color_reset: '_onColorReset',
    },

    /**
     * @override
     */
    start: function () {
        const options = {
            $target: this.$target,
        };
        const proms = [this._super(...arguments)];
        if (this.data.paletteExclude) {
            options.excluded = this.data.paletteExclude.replace(/ /g, '').split(',');
        }
        if (this.data.colorPrefix) {
            options.colorPrefix = this.data.colorPrefix;
        }
        this.colorPalette = new ColorPaletteWidget(this, options);
        proms.push(this.colorPalette.appendTo(this.$el.find('we-collapse')));

        return Promise.all(proms);
    },

    onFocus: function () {
        this.colorPalette.reloadColorPalette();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Change the color of the targeted background
     *
     * @private
     * @param {string} cssColor
     * @param {boolean} isClass
     */
    _changeTargetColor: function (cssColor, isClass) {
        this.$target.removeClass(this.colorPalette.getClasses());
        if (isClass) {
            this.$target.addClass(cssColor);
        } else {
            this.$target.css('background-color', cssColor);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a color button is clicked -> confirm the preview.
     *
     * @private
     * @param {Event} ev
     */
    _onColorPicked: function () {
        this.$target.closest('.o_editable').trigger('content_changed');
        this.$target.trigger('background-color-event', false);
    },
    /**
     * Called when a custom color is selected
     * @param {*} ev
     */
    _onCustomColor: function (ev) {
        this._changeTargetColor(ev.data.cssColor);
        this._onColorPicked();
    },
    /**
     * Called when a color button is entered -> preview the background color.
     *
     * @private
     * @param {Event} ev
     */
    _onColorHovered: function (ev) {
        this._changeTargetColor(ev.data.cssColor, ev.data.isClass);
        this.$target.trigger('background-color-event', true);
    },
    /**
     * Called when a color button is left -> cancel the preview.
     *
     * @private
     * @param {Event} ev
     */
    _onColorLeft: function (ev) {
        this._changeTargetColor(ev.data.cssColor, ev.data.isClass);
        this.$target.trigger('background-color-event', 'reset');
    },
    /**
     * Called when the color reset button is clicked -> remove all background
     * color classes.
     *
     * @private
     */
    _onColorReset: function () {
        this._targetColorChange('');
        this.$target.trigger('content_changed');
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
        // Build option UI controls
        var titleEl = this.el.querySelector('we-title');
        this.removeBgEl = document.createElement('we-button');
        this.removeBgEl.classList.add('fa', 'fa-fw', 'fa-times');
        this.removeBgEl.dataset.background = '';
        this.removeBgEl.dataset.noPreview = 'true';
        titleEl.appendChild(this.removeBgEl);

        const editBgEl = document.createElement('we-button');
        editBgEl.dataset.chooseImage = 'true';
        editBgEl.dataset.noPreview = 'true';
        const iconEl = document.createElement('i');
        iconEl.classList.add('fa', 'fa-fw', 'fa-pencil-square-o');
        this.editBgTextEl = document.createElement('span');
        editBgEl.appendChild(this.editBgTextEl);
        editBgEl.appendChild(iconEl);
        this.$el.find('we-group')[0].appendChild(editBgEl);

        var res = this._super.apply(this, arguments);

        // Initialize background and events
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
    background: function (previewMode, value, $opt) {
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
    selectClass: function (previewMode, value, $opt) {
        this.background(previewMode, '', $opt);
        this._super(previewMode, value ? (value + ' oe_img_bg') : value, $opt);
    },
    /**
     * Opens a media dialog to add a custom background image.
     *
     * @see this.selectClass for parameters
     */
    chooseImage: function (previewMode, value, $opt) {
        var options = this._getMediaDialogOptions();
        var media = this._getEditableMedia();

        var _editor = new weWidgets.MediaDialog(this, options, media).open();
        _editor.on('save', this, data => {
            this._onSaveMediaDialog(data);
            this.$target.trigger('content_changed');
        });
        _editor.on('closed', this, () => {
            if (media.classList.contains('o_we_fake_image')) {
                media.parentNode.removeChild(media);
            }
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
        if (this.$target.is('.parallax, .s_parallax_bg')) {
            return;
        }
        this.$target.off('.background-option')
            .on('background-color-event.background-option', this._onBackgroundColorUpdate.bind(this));
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
     * Returns a media element the media dialog will be able to edit to use
     * the result as the snippet's background somehow.
     *
     * @private
     * @returns {HTMLElement}
     */
    _getEditableMedia: function () {
        var $image = $('<img/>', {
            class: 'd-none o_we_fake_image',
        }).appendTo(this.$target);
        return $image[0];
    },
    /**
     * Returns the options to be given to the MediaDialog instance when choosing
     * a snippet's background.
     *
     * @private
     * @returns {Object}
     */
    _getMediaDialogOptions: function () {
        var $editable = this.$target.closest('.o_editable');
        return {
            noDocuments: true,
            noIcons: true,
            noVideos: true,
            firstFilters: ['background'],
            res_model: $editable.data('oe-model'),
            res_id: $editable.data('oe-id'),
        };
    },
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
        var srcValueWrapper = /url\(['"]*|['"]*\)|^none$/g;
        return value && value.replace(srcValueWrapper, '') || '';
    },
    /**
     * @override
     */
    _updateUI: function () {
        this._super.apply(this, arguments);
        var src = this._getSrcFromCssValue();
        this.removeBgEl.classList.toggle('d-none', !src);
        if (src) {
            var split = src.split('/');
            this.editBgTextEl.textContent = split[split.length - 1];
        } else {
            this.editBgTextEl.textContent = _t("Choose a picture or a video");
        }
    },
    /**
     * Sets the given value as custom background image.
     *
     * @private
     * @param {string} value
     */
    _setCustomBackground: function (value) {
        this.__customImageSrc = value;
        this.background(false, this.__customImageSrc);
        this.$target.toggleClass('oe_custom_bg', !!value);
        this._updateUI();
        this.$target.trigger('snippet-option-change', [this]);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called on background-color update (useful to remove the background to be
     * able to see the chosen color).
     *
     * @private
     * @param {Event} ev
     * @param {boolean|string} previewMode
     * @returns {boolean} true if the color has been applied (removing the
     *                    background)
     */
    _onBackgroundColorUpdate: function (ev, previewMode) {
        ev.stopPropagation();
        if (ev.currentTarget !== ev.target) {
            return false;
        }
        if (previewMode === false) {
            this.__customImageSrc = undefined;
        }
        this.background(previewMode);
        return true;
    },
    /**
     * Called on media dialog save (when choosing a snippet's background) ->
     * sets the resulting media as the snippet's background somehow.
     *
     * @private
     * @param {Object} data
     */
    _onSaveMediaDialog: function (data) {
        this._setCustomBackground(data.src);
    },
});

/**
 * Handles the edition of snippet's background image position.
 */
registry['background_position'] = SnippetOption.extend({
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
        this.$el.toggleClass('d-none', this.$target.css('background-image') === 'none');
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Opens a Dialog to edit the snippet's backgroung image position.
     *
     * @see this.selectClass for parameters
     */
    backgroundPosition: function (previewMode, value, $opt) {
        var self = this;

        this.previousState = [this.$target.attr('class'), this.$target.css('background-size'), this.$target.css('background-position')];

        this.bgPos = self.$target.css('background-position').split(' ');
        this.bgSize = self.$target.css('background-size').split(' ');

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
            var value = ((self.$target.hasClass('o_bg_img_opt_contain')) ? 'contain' : ((self.$target.hasClass('o_bg_img_opt_custom')) ? 'custom' : 'cover'));
            self.modal.$('> label > input[value=' + value + ']').prop('checked', true);

            if (self.$target.hasClass('o_bg_img_opt_repeat')) {
                self.modal.$('#o_bg_img_opt_contain_repeat').prop('checked', true);
                self.modal.$('#o_bg_img_opt_custom_repeat').val('o_bg_img_opt_repeat');
            } else if (self.$target.hasClass('o_bg_img_opt_repeat_x')) {
                self.modal.$('#o_bg_img_opt_custom_repeat').val('o_bg_img_opt_repeat_x');
            } else if (self.$target.hasClass('o_bg_img_opt_repeat_y')) {
                self.modal.$('#o_bg_img_opt_custom_repeat').val('o_bg_img_opt_repeat_y');
            }

            if (self.bgPos.length > 1) {
                self.bgPos = {
                    x: self.bgPos[0],
                    y: self.bgPos[1],
                };
                self.modal.$('#o_bg_img_opt_custom_pos_x').val(self.bgPos.x.replace('%', ''));
                self.modal.$('#o_bg_img_opt_custom_pos_y').val(self.bgPos.y.replace('%', ''));
            }
            if (self.bgSize.length > 1) {
                self.modal.$('#o_bg_img_opt_custom_size_x').val(self.bgSize[0].replace('%', ''));
                self.modal.$('#o_bg_img_opt_custom_size_y').val(self.bgSize[1].replace('%', ''));
            }

            // Focus Point
            self.$focus = self.modal.$('.o_focus_point');
            self._updatePosInformation();

            var imgURL = /\(['"]?([^'"]+)['"]?\)/g.exec(self.$target.css('background-image'));
            imgURL = (imgURL && imgURL[1]) || '';
            var $img = $('<img/>', {class: 'img img-fluid', src: imgURL});
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
            self.bgPos = {
                x: clipValue(posX / $img.width() * 100).toFixed(2) + '%',
                y: clipValue(posY / $img.height() * 100).toFixed(2) + '%',
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
        if (this.previousState) {
            this.$target.addClass(this.previousState[0]).css({
                'background-size': this.previousState[1],
                'background-position': this.previousState[2],
            });
        }
    },
    /**
     * Updates the visual representation of the chosen background position.
     *
     * @private
     */
    _updatePosInformation: function () {
        this.modal.$('.o_bg_img_opt_ui_info .o_x').text(this.bgPos.x);
        this.modal.$('.o_bg_img_opt_ui_info .o_y').text(this.bgPos.y);
        this.$focus.css({
            left: this.bgPos.x,
            top: this.bgPos.y,
        });
    },
    /**
     * Updates the target element to match the chosen options.
     *
     * @private
     */
    _saveChanges: function () {
        this._clean();

        var bgImgSize = this.modal.$('> :not(label):not(.o_hidden)').data('value') || 'cover';
        switch (bgImgSize) {
            case 'cover':
                this.$target.css('background-position', this.bgPos.x + ' ' + this.bgPos.y);
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
                                'background-size': (sizeX ? sizeX + '%' : 'auto') + ' ' + (sizeY ? sizeY + '%' : 'auto'),
                                'background-position': (posX ? posX + '%' : 'auto') + ' ' + (posY ? posY + '%' : 'auto'),
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
        this.trigger_up('getRecordInfo', _.extend(this.options, {
            callback: function (recordInfo) {
                _.defaults(self.options, recordInfo);
            },
        }));

        this.Model = this.$target.data('oe-many2one-model');
        this.ID = +this.$target.data('oe-many2one-id');

        // create search button and bind search bar
        this.$btn = $(qweb.render('web_editor.many2one.button'))
            .prependTo(this.$el);

        this.$ul = this.$btn.find('ul');
        this.$search = this.$ul.find('li:first');
        this.$search.find('input').on('mousedown click mouseup keyup keydown', function (e) {
            e.stopPropagation();
        });

        // move menu item
        setTimeout(function () {
            self.$btn.find('a').on('click', function (e) {
                self._clear();
            });
        }, 0);

        // bind search input
        this.$search.find('input')
            .focus()
            .on('keyup', function (e) {
                self.$overlay.removeClass('o_keypress');
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
     * @returns {Promise}
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
                context: this.options.context,
            },
        }).then(function (result) {
            self.$search.siblings().remove();
            self.$search.after(qweb.render('web_editor.many2one.search', {contacts: result}));
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
                .filter('[data-oe-model="' + self.$target.data('oe-model') + '"]')
                .filter('[data-oe-id="' + self.$target.data('oe-id') + '"]')
                .filter('[data-oe-field="' + self.$target.data('oe-field') + '"]')
                .filter('[data-oe-contact-options!="' + self.$target.data('oe-contact-options') + '"]')
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
                            context: self.options.context,
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
    CSS_SHORTHANDS: CSS_SHORTHANDS,
};
});
