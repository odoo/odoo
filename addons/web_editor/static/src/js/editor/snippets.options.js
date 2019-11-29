odoo.define('web_editor.snippets.options', function (require) {
'use strict';

var core = require('web.core');
var ColorPaletteWidget = require('web_editor.ColorPalette').ColorPaletteWidget;
var Widget = require('web.Widget');
var weWidgets = require('wysiwyg.widgets');

var qweb = core.qweb;
var _t = core._t;

/**
 * window.getComputedStyle cannot work properly with CSS shortcuts (like
 * 'border-width' which is a shortcut for the top + right + bottom + left border
 * widths. If an options wants to customize such a shortcut, it should be listed
 * here with the non-shortcuts property it stands for, in order.
 *
 * @type {Object<string[]>}
 */
const CSS_SHORTHANDS = {
    'border-width': ['border-top-width', 'border-right-width', 'border-bottom-width', 'border-left-width'],
    'border-radius': ['border-top-left-radius', 'border-top-right-radius', 'border-bottom-right-radius', 'border-bottom-left-radius'],
};
/**
 * Key-value mapping to list converters from an unit A to an unit B.
 * - The key is a string in the format '$1-$2' where $1 is the CSS symbol of
 *   unit A and $2 is the CSS symbol of unit B.
 * - The value is a function that converts the received value (expressed in
 *   unit A) to another value expressed in unit B. Two other parameters is
 *   received: the css property on which the unit applies and the jQuery element
 *   on which that css property may change.
 */
const CSS_UNITS_CONVERSION = {
    's-ms': () => 1000,
    'ms-s': () => 0.001,
    'rem-px': () => _computePxByRem(),
    'px-rem': () => _computePxByRem(true),
};

/**
 * Computes the number of "px" needed to make a "rem" unit. Subsequent calls
 * returns the cached computed value.
 *
 * @param {boolean} [toRem=false]
 * @returns {float} - number of px by rem if 'toRem' is false
 *                  - the inverse otherwise
 */
function _computePxByRem(toRem) {
    if (_computePxByRem.PX_BY_REM === undefined) {
        const htmlStyle = window.getComputedStyle(document.documentElement);
        _computePxByRem.PX_BY_REM = parseFloat(htmlStyle['font-size']);
    }
    return toRem ? (1 / _computePxByRem.PX_BY_REM) : _computePxByRem.PX_BY_REM;
}

/**
 * Handles a set of options for one snippet. The registry returned by this
 * module contains the names of the specialized SnippetOption which can be
 * referenced thanks to the data-js key in the web_editor options template.
 */
var SnippetOption = Widget.extend({
    events: {
        'mouseenter we-button': '_onOptionPreview',
        'click we-button': '_onOptionSelection',
        'mouseleave we-button': '_onOptionCancel',

        'input we-input input': '_onOptionPreview',
        'blur we-input input': '_onOptionInputBlur',
        'click we-input': '_onOptionInputClick',
        'keydown we-input input': '_onOptionInputKeydown',
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
        this.$target = $target;
        this.$overlay = $overlay;
        this.data = data;
        this.options = options;
        this.ownerDocument = this.$target[0].ownerDocument;
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
     *
     * @returns {boolean}
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
     * appropriate data attribute on the associated snippet.
     *
     * @param {boolean} previewMode - never 'reset' for this method (@see this.selectClass)
     * @param {Object} dataName - the data name to customize
     * @param {jQuery} $opt - the related DOMElement option
     */
    setDataAttribute: function (previewMode, dataName, $opt) {
        let hasUserValue = false;
        const weInput = $opt[0];
        const inputValue = weInput.querySelector('input').value.trim();
        const inputUnit = weInput.dataset.unit;
        const saveUnit = weInput.dataset.saveUnit;
        const defaultValue = weInput.dataset.defaultValue;

        let value;
        if (inputValue) {
            const numValue = parseFloat(inputValue);
            if (!isNaN(numValue)) {
                hasUserValue = true;
                value = this._convertNumericToUnit(numValue, inputUnit, saveUnit);
            }
        }
        if (value === undefined) {
            value = this._convertValueToUnit(defaultValue, saveUnit);
        }
        this.$target[0].dataset[dataName] = isNaN(value) ? defaultValue : parseFloat(value.toFixed(3));

        var extraClass = weInput.dataset.extraClass;
        if (extraClass) {
            this.$target.toggleClass(extraClass, hasUserValue);
        }
    },
    /**
     * Default option method which allows to handle an user input and set the
     * appropriate css style on the associated snippet.
     *
     * @param {boolean} previewMode - never 'reset' for this method (@see this.selectClass)
     * @param {Object} mainCssProp - the cssProp to customize
     * @param {jQuery} $opt - the related DOMElement option
     */
    setStyle: function (previewMode, mainCssProp, $opt) {
        let hasUserValue = false;
        const cssProps = CSS_SHORTHANDS[mainCssProp] || [mainCssProp];

        // Join all inputs controlling the same css property and split user
        // input into sub-properties (note this code handles the two at the same
        // time but should normally not be combined).
        const $weInputs = this.$el.find(`[data-set-style=${mainCssProp}]`);
        const subValuesByInput = _.map($weInputs, weInput => {
            const inputValue = weInput.querySelector('input').value.trim();
            const inputUnit = weInput.dataset.unit;
            const saveUnit = weInput.dataset.saveUnit;
            const defaultValue = weInput.dataset.defaultValue;
            let convertedDefaultValue = this._convertValueToUnit(defaultValue, saveUnit, mainCssProp);
            convertedDefaultValue = isNaN(convertedDefaultValue) ? defaultValue : (parseFloat(convertedDefaultValue.toFixed(3)) + saveUnit);

            const values = inputValue.split(/\s+/g).map(v => {
                const numValue = parseFloat(v);
                if (isNaN(numValue)) {
                    return convertedDefaultValue;
                } else {
                    hasUserValue = true;
                    const value = this._convertNumericToUnit(numValue, inputUnit, saveUnit, mainCssProp);
                    return parseFloat(value.toFixed(3)) + saveUnit;
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

        var extraClass = $opt[0].dataset.extraClass;
        if (extraClass) {
            this.$target.toggleClass(extraClass, hasUserValue);
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
        var $group = $opt && $opt.parents('we-select').last();
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
     * Converts the given (value + unit) string to a numeric value expressed in
     * the given css unit.
     *
     * e.g. fct('400ms', 's') -> 0.4
     *
     * @param {string} value
     * @param {string} unitTo
     * @param {string} [cssProp]
     * @returns {number}
     */
    _convertValueToUnit: function (value, unitTo, cssProp) {
        const m = value.trim().match(/^([0-9.]+)(\w*)$/);
        if (!m) {
            return NaN;
        }
        const numValue = parseFloat(m[1]);
        const valueUnit = m[2];
        return this._convertNumericToUnit(numValue, valueUnit, unitTo, cssProp);
    },
    /**
     * Converts the given numeric value expressed in the given css unit into
     * the corresponding numeric value expressed in the other given css unit.
     *
     * e.g. fct(400, 'ms', 's') -> 0.4
     *
     * @param {number} value
     * @param {string} unitFrom
     * @param {string} unitTo
     * @param {string} [cssProp]
     * @returns {number}
     */
    _convertNumericToUnit: function (value, unitFrom, unitTo, cssProp) {
        if (Math.abs(value) < Number.EPSILON || unitFrom === unitTo) {
            return value;
        }
        const converter = CSS_UNITS_CONVERSION[`${unitFrom}-${unitTo}`];
        if (converter === undefined) {
            throw new Error(`Cannot convert ${unitFrom} into ${unitTo} !`);
        }
        return value * converter(cssProp, this.$target);
    },
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

            const isInput = $el.is('we-input');

            Object.keys(methods).forEach(methodName => {
                if (!this[methodName]) {
                    return;
                }
                if (previewMode === true && !isInput) {
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
        var $submenus = this.$el.find('we-select')
            .not('we-select *');

        // Add unique active class for each submenu active item
        _.each($submenus, function (submenu) {
            var $elements = $(submenu).find('[data-select-class]');
            _processSelectClassElements($elements);
        });

        // Add unique active class for out-of-submenu active item
        var $externalElements = this.$el.find('[data-select-class]')
            .not('we-select *');
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

        // --- SET DATA ATTRIBUTE --- (note: important to be done last because of active removal)

        this.el.querySelectorAll('[data-set-data-attribute]').forEach(el => {
            el.classList.remove('active');
            const inputEl = el.querySelector('input');
            if (inputEl === document.activeElement) {
                return;
            }

            const inputUnit = el.dataset.unit;
            const saveUnit = el.dataset.saveUnit;
            const defaultValue = el.dataset.defaultValue;
            const convertedDefaultValue = this._convertValueToUnit(defaultValue, inputUnit);

            let value = this.$target[0].dataset[el.dataset.setDataAttribute];
            let numValue = parseFloat(value);
            if (!isNaN(numValue)) {
                numValue = this._convertNumericToUnit(numValue, saveUnit, inputUnit);
            }
            if (isNaN(numValue) || Math.abs(numValue - convertedDefaultValue) < Number.EPSILON) {
                value = '';
            } else {
                value = parseFloat(numValue.toFixed(3));
            }
            inputEl.value = value;
        });

        // --- SET STYLE --- (note: important to be done last because of active removal)

        let styles;
        const seenSetStyles = [];
        this.el.querySelectorAll('[data-set-style]').forEach(el => {
            const mainCssProp = el.dataset.setStyle;
            if (seenSetStyles.includes(mainCssProp)) {
                return;
            }
            seenSetStyles.push(mainCssProp);

            const $els = this.$el.find(`[data-set-style="${mainCssProp}"]`);
            $els.removeClass('active');
            const $inputs = $els.find('> input');
            if (_.any($inputs, input => input === document.activeElement)) {
                return;
            }

            styles = styles || window.getComputedStyle(this.$target[0]);
            const cssProps = CSS_SHORTHANDS[mainCssProp] || [mainCssProp];

            const valuesByProp = cssProps.map(cssProp => {
                const cssValue = styles[cssProp];
                if (!cssValue) {
                    return [];
                }

                return cssValue.split(/\s+/).map((v, i) => {
                    const inputUnit = $els[i].dataset.unit;
                    const numValue = this._convertValueToUnit(v, inputUnit, mainCssProp);
                    return isNaN(numValue) ? v : numValue;
                });
            });
            _.each($els, (el, i) => {
                let values = valuesByProp.map(propValues => propValues[i]);

                if (values.length === 4 && Math.abs(values[3] - values[1]) < Number.EPSILON) {
                    values.pop();
                }
                if (values.length === 3 && Math.abs(values[2] - values[0]) < Number.EPSILON) {
                    values.pop();
                }
                if (values.length === 2 && Math.abs(values[1] - values[0]) < Number.EPSILON) {
                    values.pop();
                }

                const inputUnit = el.dataset.unit;
                const defaultValue = el.dataset.defaultValue;
                const convertedDefaultValue = this._convertValueToUnit(defaultValue, inputUnit, mainCssProp);
                if (values.length === 1 && Math.abs(values[0] - convertedDefaultValue) < Number.EPSILON) {
                    values.pop();
                }

                values = values.filter(v => isFinite(v));
                values = values.map(v => parseFloat(v.toFixed(3)));
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
     * @private
     * @param {Event} ev
     */
    _onOptionInputClick: function (ev) {
        const inputEl = ev.currentTarget.querySelector('input');
        if (inputEl) {
            inputEl.select();
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onOptionInputKeydown: function (ev) {
        const input = ev.currentTarget;
        let value = parseFloat(input.value || input.placeholder);
        if (isNaN(value)) {
            return;
        }

        let step = parseFloat(input.parentNode.dataset.step);
        if (isNaN(step)) {
            step = 1.0;
        }
        switch (ev.which) {
            case $.ui.keyCode.UP:
                value += step;
                break;
            case $.ui.keyCode.DOWN:
                value -= step;
                break;
            default:
                return;
        }

        input.value = parseFloat(value.toFixed(3));
        $(input).trigger('input');
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
     * Build the correct DOM for an element according to the given options.
     *
     * @static
     * @param {string} tagName
     * @param {string} [title]
     * @param {Object} [options]
     * @param {string[]} [options.classes]
     * @param {Object} [options.dataAttributes]
     * @returns {HTMLElement}
     */
    buildElement: function (tagName, title, options) {
        const el = document.createElement(tagName);

        if (title) {
            const titleEl = SnippetOption.prototype.buildTitleElement(title);
            el.appendChild(titleEl);
        }

        if (options && options.classes) {
            el.classList.add(...options.classes);
        }
        if (options && options.dataAttributes) {
            for (const key in options.dataAttributes) {
                el.dataset[key] = options.dataAttributes[key];
            }
        }

        return el;
    },
    /**
     * Build the correct DOM for a we-checkbox element.
     *
     * @static
     * @param {string} [title]
     * @param {Object} [options] - @see this.buildElement
     * @returns {HTMLElement}
     */
    buildCheckboxElement: function (title, options) {
        const buttonEl = SnippetOption.prototype.buildElement('we-button', title, options);
        buttonEl.classList.add('o_we_checkbox_wrapper');

        const checkboxEl = document.createElement('we-checkbox');
        buttonEl.appendChild(checkboxEl);

        return buttonEl;
    },
    /**
     * Build the correct DOM for a we-row element.
     *
     * @static
     * @param {string} [title]
     * @param {Object} [options] - @see this.buildElement
     * @param {HTMLElement[]} [options.childNodes]
     * @returns {HTMLElement}
     */
    buildRowElement: function (title, options) {
        const groupEl = SnippetOption.prototype.buildElement('we-row', title, options);

        const rowEl = document.createElement('div');
        groupEl.appendChild(rowEl);

        if (options && options.childNodes) {
            options.childNodes.forEach(node => rowEl.appendChild(node));
        }

        return groupEl;
    },
    /**
     * Build the correct DOM for a we-input element.
     *
     * @static
     * @param {string} [title]
     * @param {Object} [options] - @see this.buildElement
     */
    buildInputElement: function (title, options) {
        const inputWrapperEl = SnippetOption.prototype.buildElement('we-input', title, options);

        var unit = inputWrapperEl.dataset.unit;
        if (unit === undefined) {
            unit = 'px';
        }
        inputWrapperEl.dataset.unit = unit;
        if (inputWrapperEl.dataset.saveUnit === undefined) {
            inputWrapperEl.dataset.saveUnit = unit;
        }

        var defaultValue = inputWrapperEl.dataset.defaultValue;
        if (defaultValue === undefined) {
            defaultValue = ('0' + unit);
        }
        inputWrapperEl.dataset.defaultValue = defaultValue;

        var inputEl = document.createElement('input');
        inputEl.setAttribute('type', 'text');
        inputEl.setAttribute('placeholder', defaultValue.replace(unit, ''));
        inputWrapperEl.appendChild(inputEl);

        var unitEl = document.createElement('span');
        unitEl.textContent = unit;
        inputWrapperEl.appendChild(unitEl);

        return inputWrapperEl;
    },
    /**
     * Build the correct DOM for a we-select element.
     *
     * @static
     * @param {string} [title]
     * @param {Object} [options] - @see this.buildElement
     * @param {HTMLElement[]} [options.childNodes]
     * @param {HTMLElement} [options.valueEl]
     * @returns {HTMLElement}
     */
    buildSelectElement: function (title, options) {
        const selectEl = SnippetOption.prototype.buildElement('we-select', title, options);

        if (options && options.valueEl) {
            selectEl.appendChild(options.valueEl);
        }

        const menuTogglerEl = document.createElement('we-toggler');
        selectEl.appendChild(menuTogglerEl);

        var menuEl = document.createElement('we-select-menu');
        if (options && options.childNodes) {
            options.childNodes.forEach(node => menuEl.appendChild(node));
        }
        selectEl.appendChild(menuEl);

        return selectEl;
    },
    /**
     * @static
     * @param {string} title
     * @returns {HTMLElement}
     */
    buildTitleElement: function (title) {
        const titleEl = document.createElement('we-title');
        titleEl.textContent = title;
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
            var direction = $handle.hasClass('n') ? 'top' : 'bottom';
            $handle.height(self.$target.css('padding-' + direction));
        });
        this.$target.trigger('content_changed');
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
        'color_picked': '_onColorPicked',
        'custom_color_picked': '_onCustomColor',
        'color_hover': '_onColorHovered',
        'color_leave': '_onColorLeft',
        'color_reset': '_onColorReset',
    },

    /**
     * @override
     */
    start: async function () {
        const _super = this._super.bind(this);
        const args = arguments;

        // Pre-instanciate the color palette widget
        const options = {
            selectedColor: this.$target.css('background-color'),
            targetClasses: [...this.$target[0].classList],
        };
        if (this.data.paletteExclude) {
            options.excluded = this.data.paletteExclude.replace(/ /g, '').split(',');
        }
        if (this.data.colorPrefix) {
            options.colorPrefix = this.data.colorPrefix;
        }
        this.colorPalette = new ColorPaletteWidget(this, options);
        await this.colorPalette.appendTo(document.createDocumentFragment());

        // Build the select element with a custom span to hold the color preview
        this.colorPreviewEl = document.createElement('span');
        const selectEl = this.buildSelectElement(this.data.string, {
            classes: ['o_we_so_color_palette'],
            childNodes: [this.colorPalette.el],
            valueEl: this.colorPreviewEl,
        });

        // Replace the colorpicker UI with the select element
        this.$el.empty().append(selectEl);
        return _super(...args);
    },
    /**
     * @override
     */
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
        this.$target[0].classList.remove(...this.colorPalette.getClasses());
        if (isClass) {
            this.$target.addClass(cssColor);
        } else {
            this.$target.css('background-color', cssColor);
        }
    },
    /**
     * @override
     */
    _updateUI: function () {
        this._super.apply(this, arguments);
        this.colorPreviewEl.style.backgroundColor = this.$target.css('background-color');
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
        this._updateUI();
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
        this._changeTargetColor('');
        this._updateUI();
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
        const editBgEl = document.createElement('we-button');
        editBgEl.dataset.chooseImage = 'true';
        editBgEl.dataset.noPreview = 'true';
        const iconEl = document.createElement('i');
        iconEl.classList.add('fa', 'fa-fw', 'fa-edit');
        this.editBgTextEl = document.createElement('span');
        editBgEl.appendChild(this.editBgTextEl);
        editBgEl.appendChild(iconEl);

        this.removeBgEl = document.createElement('we-button');
        this.removeBgEl.classList.add('fa', 'fa-fw', 'fa-times');
        this.removeBgEl.title = _t("Remove the background");
        this.removeBgEl.dataset.background = '';
        this.removeBgEl.dataset.noPreview = 'true';

        this.$el.append(this.buildRowElement(this.data.string, {
            childNodes: [editBgEl, this.removeBgEl],
        }));

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
     * @private
     * @returns {string}
     */
    _getDefaultTextContent: function () {
        return _t("Choose a picture");
    },
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
            this.editBgTextEl.textContent = this._getDefaultTextContent();
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
 * Handles the edition of snippets' background image position.
 */
registry.BackgroundPosition = SnippetOption.extend({
    xmlDependencies: ['/web_editor/static/src/xml/editor.xml'],

    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);

        this._initOverlay();
        this.img = document.createElement('img');
        this.img.src = this._getSrcFromCssValue();

        this.$target.on('snippet-option-change', () => {
            // Hides option if the bg image is removed in favor of a bg color
            this._updateUI();
            // this.img is used to compute dragging speed
            this.img.src = this._getSrcFromCssValue();
        });

        // Resize overlay content on window resize because background images
        // change size, and on carousel slide because they sometimes take up
        // more space and move elements around them.
        $(window).on('resize.bgposition', () => this._dimensionOverlay());
    },
    /**
     * @override
     */
    destroy: function () {
        this._toggleBgOverlay(false);
        $(window).off('.bgposition');
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    onFocus: function () {
        this._updateUI();
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Sets the background type (cover/repeat pattern).
     *
     * @see this.selectClass for params
     */
    backgroundType: function (previewMode, value, $opt) {
        this.$target.toggleClass('o_bg_img_opt_repeat', value === 'repeat-pattern');
        this.$target.css('background-position', '');
        this.$target.css('background-size', '');
    },
    /**
     * Saves current background position and enables overlay.
     *
     * @see this.selectClass for params
     */
    backgroundPositionOverlay: function (previewMode, value, $opt) {
        const position = this.$target.css('background-position').split(' ').map(v => parseInt(v));
        // Convert % values to pixels (because mouse movement is in pixels)
        const delta = this._getBackgroundDelta();
        this.originalPosition = {
            left: position[0] / 100 * delta.x || 0,
            top: position[1] / 100 * delta.y || 0,
        };
        this.currentPosition = _.clone(this.originalPosition);

        this._toggleBgOverlay(true);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Initializes the overlay, binds events to the buttons, inserts it in
     * the DOM.
     *
     * @private
     */
    _initOverlay: function () {
        this.$backgroundOverlay = $(qweb.render('web_editor.background_position_overlay'));
        this.$overlayContent = this.$backgroundOverlay.find('.o_we_overlay_content');
        this.$overlayBackground = this.$overlayContent.find('.o_overlay_background');

        this.$backgroundOverlay.on('click', '.o_btn_apply', () => {
            this.$target.css('background-position', this.$bgDragger.css('background-position'));
            this._toggleBgOverlay(false);
        });
        this.$backgroundOverlay.on('click', '.o_btn_discard', () => {
            this._toggleBgOverlay(false);
        });

        this.$backgroundOverlay.insertAfter(this.$overlay);
    },
    /**
     * Sets the overlay in the right place so that the draggable background
     * renders over the target, and size the background item like the target.
     *
     * @private
     */
    _dimensionOverlay: function () {
        if (!this.$backgroundOverlay.is('.oe_active')) {
            return;
        }
        // TODO: change #wrapwrap after web_editor rework.
        const $wrapwrap = $('#wrapwrap');
        const targetOffset = this.$target.offset();

        this.$backgroundOverlay.css({
            width: $wrapwrap.innerWidth(),
            height: $wrapwrap.innerHeight(),
        });

        this.$overlayContent.offset(targetOffset);

        this.$bgDragger.css({
            width: `${this.$target.innerWidth()}px`,
            height: `${this.$target.innerHeight()}px`,
        });
    },
    /**
     * Toggles the overlay's display and renders a background clone inside of it.
     *
     * @private
     * @param {boolean} activate toggle the overlay on (true) or off (false)
     */
    _toggleBgOverlay: function (activate) {
        if (this.$backgroundOverlay.is('.oe_active') === activate) {
            return;
        }

        if (!activate) {
            this.$backgroundOverlay.removeClass('oe_active');
            this.trigger_up('unblock_preview_overlays');
            this.trigger_up('activate_snippet', {$snippet: this.$target});

            $(document).off('click.bgposition');
            return;
        }

        this.trigger_up('hide_overlay');
        this.trigger_up('activate_snippet', {
            $snippet: this.$target,
            previewMode: true,
        });
        this.trigger_up('block_preview_overlays');

        // Create empty clone of $target with same display size, make it draggable and give it a tooltip.
        this.$bgDragger = this.$target.clone().empty();
        this.$bgDragger.on('mousedown', this._onDragBackgroundStart.bind(this));
        this.$bgDragger.tooltip({
            title: 'Click and drag the background to adjust its position!',
            trigger: 'manual',
            container: this.$backgroundOverlay
        });

        // Replace content of overlayBackground, activate the overlay and give it the right dimensions.
        this.$overlayBackground.empty().append(this.$bgDragger);
        this.$backgroundOverlay.addClass('oe_active');
        this._dimensionOverlay();
        this.$bgDragger.tooltip('show');

        // Needs to be deferred or the click event that activated the overlay deactivates it as well.
        // This is caused by the click event which we are currently handling bubbling up to the document.
        window.setTimeout(() => $(document).on('click.bgposition', this._onDocumentClicked.bind(this)), 0);
    },
    /**
     * Disables background position if no background image, disables size inputs
     * in cover mode, and activates the proper select option.
     *
     * @override
     */
    _setActive: function () {
        this.$el.toggleClass('d-none', this.$target.css('background-image') === 'none');
        this.$el.find('we-input').toggleClass('d-none', this.$target.css('background-repeat') !== 'repeat');
        this.$el.find('[data-background-type]').removeClass('active')
            .filter(`[data-background-type=${this.$target.css('background-repeat') === 'repeat' ? 'repeat-pattern' : 'cover'}]`).addClass('active');

        this._super.apply(this, arguments);
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
     * Returns the difference between the target's size and the background's
     * rendered size. Background position values in % are a percentage of this.
     *
     * @private
     */
    _getBackgroundDelta: function () {
        const bgSize = this.$target.css('background-size');
        if (bgSize !== 'cover') {
            let [width, height] = bgSize.split(' ');
            if (width === 'auto' && (height === 'auto' || !height)) {
                return {
                    x: this.$target.outerWidth() - this.img.naturalWidth,
                    y: this.$target.outerHeight() - this.img.naturalHeight,
                };
            }
            // At least one of width or height is not auto, so we can use it to calculate the other if it's not set
            [width, height] = [parseInt(width), parseInt(height)];
            return {
                x: this.$target.outerWidth() - (width || (height * this.img.naturalWidth / this.img.naturalHeight)),
                y: this.$target.outerHeight() - (height || (width * this.img.naturalHeight / this.img.naturalWidth)),
            };
        }

        const renderRatio = Math.max(
            this.$target.outerWidth() / this.img.naturalWidth,
            this.$target.outerHeight() / this.img.naturalHeight
        );

        return {
            x: this.$target.outerWidth() - Math.round(renderRatio * this.img.naturalWidth),
            y: this.$target.outerHeight() - Math.round(renderRatio * this.img.naturalHeight),
        };
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Drags the overlay's background image, copied to target on "Apply".
     *
     * @private
     */
    _onDragBackgroundStart: function (ev) {
        ev.preventDefault();
        this.$bgDragger.addClass('o_we_grabbing');
        const $document = $(this.ownerDocument);
        $document.on('mousemove.bgposition', this._onDragBackgroundMove.bind(this));
        $document.one('mouseup', () => {
            this.$bgDragger.removeClass('o_we_grabbing');
            $document.off('mousemove.bgposition');
        });
    },
    /**
     * Drags the overlay's background image, copied to target on "Apply".
     *
     * @private
     */
    _onDragBackgroundMove: function (ev) {
        ev.preventDefault();

        const delta = this._getBackgroundDelta();
        this.currentPosition.left = clamp(this.currentPosition.left + ev.originalEvent.movementX, [0, delta.x]);
        this.currentPosition.top = clamp(this.currentPosition.top + ev.originalEvent.movementY, [0, delta.y]);

        const percentPosition = {
            left: this.currentPosition.left / delta.x * 100,
            top: this.currentPosition.top / delta.y * 100,
        };
        // In cover mode, one delta will be 0 and dividing by it will yield Infinity.
        // Defaulting to originalPosition in that case (can't be dragged)
        percentPosition.left = isFinite(percentPosition.left) ? percentPosition.left : this.originalPosition.left;
        percentPosition.top = isFinite(percentPosition.top) ? percentPosition.top : this.originalPosition.top;

        this.$bgDragger.css('background-position', `${percentPosition.left}% ${percentPosition.top}%`);

        function clamp(val, bounds) {
            // We sort the bounds because when one dimension of the rendered background is
            // larger than the container, delta is negative, and we want to use it as lower bound
            bounds = bounds.sort();
            return Math.max(bounds[0], Math.min(val, bounds[1]));
        }
    },
    /**
     * Deactivates the overlay if the user clicks outside of it.
     *
     * @private
     */
    _onDocumentClicked: function (ev) {
        if (!ev.target.closest('.o_we_background_position_overlay')) {
            this._toggleBgOverlay(false);
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
    CSS_UNITS_CONVERSION: CSS_UNITS_CONVERSION,
};
});
