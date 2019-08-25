odoo.define('website.theme', function (require) {
'use strict';

var config = require('web.config');
var core = require('web.core');
var Dialog = require('web.Dialog');
var Widget = require('web.Widget');
var weWidgets = require('wysiwyg.widgets');
var ColorpickerDialog = require('web.ColorpickerDialog');
var websiteNavbarData = require('website.navbar');

var _t = core._t;

var templateDef = null;

var QuickEdit = Widget.extend({
    xmlDependencies: ['/website/static/src/xml/website.editor.xml'],
    template: 'website.theme_customize_active_input',
    events: {
        'keydown input': '_onInputKeydown',
        'click .btn-secondary': '_onResetClick',
        'focusout': '_onFocusOut',
    },

    /**
     * @constructor
     */
    init: function (parent, value, unit) {
        this._super.apply(this, arguments);
        this.value = value;
        this.unit = unit;
        this._onFocusOut = _.debounce(this._onFocusOut, 100);
    },
    /**
     * @override
     */
    start: function () {
        this.$input = this.$('input');
        this.$input.select();
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} [value]
     */
    _save: function (value) {
        if (value === undefined) {
            value = parseFloat(this.$input.val());
            value = isNaN(value) ? 'null' : (value + this.unit);
        }
        this.trigger_up('QuickEdit:save', {
            value: value,
        });
        this.destroy();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onInputKeydown: function (ev) {
        var inputValue = this.$input.val();
        var value = 0;
        if (inputValue !== '') {
            value = parseFloat(this.$input.val());
            if (isNaN(value)) {
                return;
            }
        }
        switch (ev.which) {
            case $.ui.keyCode.UP:
                this.$input.val(value + 1);
                break;
            case $.ui.keyCode.DOWN:
                this.$input.val(value - 1);
                break;
            case $.ui.keyCode.ENTER:
                // Do not listen to change events, we want the user to be able
                // to confirm in all cases.
                this._save();
                break;
        }
    },
    /**
     * @private
     */
    _onFocusOut: function () {
        if (!this.$el.has(document.activeElement).length) {
            this._save();
        }
    },
    /**
     * @private
     */
    _onResetClick: function () {
        this._save('null');
    },
});

var ThemeCustomizeDialog = Dialog.extend({
    xmlDependencies: (Dialog.prototype.xmlDependencies || [])
        .concat(['/website/static/src/xml/website.editor.xml']),

    template: 'website.theme_customize',
    events: {
        'change .o_theme_customize_option_input': '_onChange',
        'click .checked .o_theme_customize_option_input[type="radio"]': '_onChange',
        'click .o_theme_customize_add_google_font': '_onAddGoogleFontClick',
        'click .o_theme_customize_delete_google_font': '_onDeleteGoogleFontClick',
    },

    CUSTOM_BODY_IMAGE_XML_ID: 'option_custom_body_image',

    /**
     * @constructor
     */
    init: function (parent, options) {
        options = options || {};
        this._super(parent, _.extend({
            title: _t("Customize Theme"),
            buttons: [],
        }, options));

        this.defaultTab = options.tab || 0;
        this.fontVariables = [];
    },
    /**
     * @override
     */
    willStart: function () {
        if (templateDef === null) {
            templateDef = this._rpc({
                model: 'ir.ui.view',
                method: 'read_template',
                args: ['website.theme_customize'],
            }).then(function (data) {
                if (!/^<templates>/.test(data)) {
                    data = _.str.sprintf('<templates>%s</templates>', data);
                }
                return core.qweb.add_template(data);
            });
        }
        return Promise.all([this._super.apply(this, arguments), templateDef]);
    },
    /**
     * @override
     */
    start: function () {
        var self = this;

        this.PX_BY_REM = parseFloat($(document.documentElement).css('font-size'));

        this.$modal.addClass('o_theme_customize_modal');

        this.style = window.getComputedStyle(document.documentElement);
        this.nbFonts = parseInt(this.style.getPropertyValue('--number-of-fonts'));
        var googleFontsProperty = this.style.getPropertyValue('--google-fonts').trim();
        this.googleFonts = googleFontsProperty ? googleFontsProperty.split(/\s*,\s*/g) : [];

        var $tabs;
        var loadDef = this._loadViews().then(function (data) {
            self._generateDialogHTML(data);
            $tabs = self.$('[data-toggle="tab"]');

            // Hide the tab navigation if only one tab
            if ($tabs.length <= 1) {
                $tabs.closest('.nav').addClass('d-none');
            }
        });

        // Enable the first option tab or the given default tab
        this.opened().then(function () {
            $tabs.eq(self.defaultTab).tab('show');

            // Hack to hide primary/secondary if they are equal to alpha/beta
            // (this is the case with default values but not in some themes).
            var $primary = self.$('.o_theme_customize_color[data-color="primary"]');
            var $alpha = self.$('.o_theme_customize_color[data-color="alpha"]');
            var $secondary = self.$('.o_theme_customize_color[data-color="secondary"]');
            var $beta = self.$('.o_theme_customize_color[data-color="beta"]');

            var sameAlphaPrimary = $primary.css('background-color') === $alpha.css('background-color');
            var sameBetaSecondary = $secondary.css('background-color') === $beta.css('background-color');

            if (!sameAlphaPrimary) {
                $alpha.prev().text(_t("Extra Color"));
            }
            if (!sameBetaSecondary) {
                $beta.prev().text(_t("Extra Color"));
            }

            $primary = $primary.closest('.o_theme_customize_option');
            $alpha = $alpha.closest('.o_theme_customize_option');
            $secondary = $secondary.closest('.o_theme_customize_option');
            $beta = $beta.closest('.o_theme_customize_option');

            $primary.toggleClass('d-none', sameAlphaPrimary);
            $secondary.toggleClass('d-none', sameBetaSecondary);

            if (!sameAlphaPrimary && sameBetaSecondary) {
                $beta.insertBefore($alpha);
            } else if (sameAlphaPrimary && !sameBetaSecondary) {
                $secondary.insertAfter($alpha);
            }
        });

        return Promise.all([this._super.apply(this, arguments), loadDef]);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _chooseBodyCustomImage: function () {
        var self = this;
        var def = new Promise(function (resolve, reject) {
            var $image = $('<img/>');
            var editor = new weWidgets.MediaDialog(self, {
                mediaWidth: 1920,
                onlyImages: true,
                firstFilters: ['background'],
            }, $image[0]);

            editor.on('save', self, function (media) { // TODO use scss customization instead (like for user colors)
                self._rpc({
                    model: 'ir.model.data',
                    method: 'get_object_reference',
                    args: ['website', self.CUSTOM_BODY_IMAGE_XML_ID],
                }).then(function (data) {
                    return self._rpc({
                        model: 'ir.ui.view',
                        method: 'save',
                        args: [
                            data[1],
                            '#wrapwrap { background-image: url("' + media.src + '"); }',
                            '//style',
                        ],
                    });
                }).then(resolve).guardedCatch(resolve);
            });
            editor.on('cancel', self, function () {
                resolve();
            });

            editor.open();
        });

        return def;
    },
    /**
     * @private
     * @param {Object} data - @see this._loadViews
     */
    _generateDialogHTML: function (data) {
        var self = this;
        var $contents = this.$el.children('content');
        if ($contents.length === 0) {
            return;
        }

        $contents.remove();
        this.$el.append(core.qweb.render('website.theme_customize_modal_layout'));
        var $navLinksContainer = this.$('.nav');
        var $navContents = this.$('.tab-content');

        _.each($contents, function (content) {
            var $content = $(content);

            var contentID = _.uniqueId('content-');

            // Build the nav tab for the content
            $navLinksContainer.append($('<li/>', {
                class: 'nav-item mb-1',
            }).append($('<a/>', {
                href: '#' + contentID,
                class: 'nav-link',
                'data-toggle': 'tab',
                text: $content.attr('string'),
            })));

            // Build the tab pane for the content
            var $navContent = $(core.qweb.render('website.theme_customize_modal_content', {
                id: contentID,
                title: $content.attr('title'),
            }));
            $navContents.append($navContent);
            var $optionsContainer = $navContent.find('.o_options_container');

            // Process content items
            _processItems($content.children(), $optionsContainer, false);
        });

        this.$('[title]').tooltip();

        this.$inputs = self.$('.o_theme_customize_option_input');
        // Enable data-xmlid="" inputs if none of their neighbors were enabled
        _.each(this.$inputs.filter('[data-xmlid=""]'), function (input) {
            var $input = $(input);
            var $neighbors = self.$inputs.filter('[name="' + $input.attr('name') + '"]').not($input);
            if ($neighbors.length && !$neighbors.filter(':checked').length) {
                $input.prop('checked', true);
            }
        });
        this._setActive();
        this._updateValues();

        function _processItems($items, $container, isSelectionContainer) {
            var optionsName = _.uniqueId('option-');
            var alone = ($items.length === 1);

            _.each($items, function (item) {
                var $item = $(item);
                var $element;

                switch (item.tagName) {
                    case 'OPT':
                        var widgetName = $item.data('widget');

                        var xmlid = $item.data('xmlid');

                        var renderingOptions = _.extend({
                            string: $item.attr('string') || xmlid && data.names[xmlid.split(',')[0].trim()],
                            icon: $item.data('icon'),
                            font: $item.data('font'),
                        }, $item.data());

                        var checked;
                        if (widgetName === 'auto') {
                            var propValue = self.style.getPropertyValue('--' + $item.data('variable')).trim();
                            checked = (propValue === $item.attr('data-value'));
                        } else {
                            checked = (xmlid === undefined || xmlid && !_.difference(self._getXMLIDs($item), data.enabled).length);
                        }

                        // Build the options template
                        $element = $(core.qweb.render('website.theme_customize_modal_option', _.extend({
                            alone: alone,
                            name: xmlid === undefined && widgetName !== 'auto' ? _.uniqueId('option-') : optionsName,
                            id: $item.attr('id') || _.uniqueId('o_theme_customize_input_id_'),
                            checked: checked,
                            widget: widgetName,
                        }, renderingOptions)));
                        $element.find('input')
                            .addClass('o_theme_customize_option_input')
                            .attr({
                                'data-xmlid': xmlid,
                                'data-enable': $item.data('enable'),
                                'data-disable': $item.data('disable'),
                                'data-reload': $item.data('reload'),
                            });

                        if (widgetName) {
                            var $widget = $(core.qweb.render('website.theme_customize_widget_' + widgetName, renderingOptions));
                            $element.find('label').append($widget);
                        }

                        if (isSelectionContainer) {
                            $element.removeClass("my-1 flex-grow-0").addClass("dropdown-item p-0");
                            $element.find('label')
                                .addClass('justify-content-start')
                                .attr('data-font-id', $item.data('font'));
                        }
                        break;

                    case 'LIST':
                        $element = $('<div/>', {class: 'py-1 px-2 o_theme_customize_option_list'});
                        _processItems($item.children(), $element, false);
                        break;

                    case 'SELECTION':
                        $element = $(core.qweb.render('website.theme_customize_dropdown_option'));
                        _processItems($item.children(), $element.find('.o_theme_customize_selection'), true);
                        break;

                    case 'FONTSELECTION':
                        var $options = $();
                        var variable = $item.data('variable');
                        self.fontVariables.push(variable);
                        _.times(self.nbFonts, function (font) {
                            $options = $options.add($('<opt/>', {
                                'data-widget': 'auto',
                                'data-variable': variable,
                                'data-value': font + 1,
                                'data-font': font + 1,
                            }));
                        });
                        $element = $(core.qweb.render('website.theme_customize_dropdown_option'));
                        var $selection = $element.find('.o_theme_customize_selection');
                        _processItems($options, $selection, true);

                        if (self.googleFonts.length) {
                            var $googleFontItems = $selection.children().slice(-self.googleFonts.length);
                            _.each($googleFontItems, function (el, index) {
                                $(el).append(core.qweb.render('website.theme_customize_delete_font', {
                                    'index': index,
                                }));
                            });
                        }
                        $selection.append($(core.qweb.render('website.theme_customize_add_google_font_option', {
                            'variable': variable,
                        })));
                        break;

                    default:
                        _processItems($item.children(), $container, false);
                        return;
                }

                if ($container.hasClass('form-row')) {
                    var $col = $('<div/>', {
                        class: _.str.sprintf('col-%s', $item.data('col') || 6),
                    });

                    if (item.tagName === 'LIST') {
                        $col.addClass('mt-2');
                        $col.append($('<h6/>', {text: $item.attr('string')}));
                    }

                    $col.append($element);
                    $element = $col;
                }

                $element.attr('data-depends', $item.data('depends'));
                $container.append($element);
            });
        }
    },
    /**
     * @private
     */
    _loadViews: function () {
        return this._rpc({
            route: '/website/theme_customize_get',
            params: {
                'xml_ids': this._getXMLIDs(this.$inputs || this.$('[data-xmlid]')),
            },
        });
    },
    /**
     * @private
     */
    _getInputs: function (string) {
        if (!string) {
            return $();
        }
        return this.$inputs.filter('#' + string.replace(/\s*,\s*/g, ', #'));
    },
    /**
     * @private
     */
    _getXMLIDs: function ($inputs) {
        var xmlIDs = [];
        _.each($inputs, function (input) {
            var $input = $(input);
            var xmlID = $input.data('xmlid');
            if (xmlID) {
                xmlIDs = xmlIDs.concat(xmlID.split(/\s*,\s*/));
            }
        });
        return xmlIDs;
    },
    /**
     * @private
     * @param {object} [values]
     *        When a new set of google fonts are saved, other variables
     *        potentially have to be adapted.
     */
    _makeGoogleFontsCusto: function (values) {
        values = values ? _.clone(values) : {};
        if (this.googleFonts.length) {
            values['google-fonts'] = "('" + this.googleFonts.join("', '") + "')";
        } else {
            values['google-fonts'] = 'null';
        }
        return this._makeSCSSCusto('/website/static/src/scss/options/user_values.scss', values).then(function () {
            window.location.hash = 'theme=true';
            window.location.reload();
        });
    },
    /**
     * @private
     */
    _makeSCSSCusto: function (url, values) {
        return this._rpc({
            route: '/website/make_scss_custo',
            params: {
                'url': url,
                'values': values,
            },
        });
    },
    /**
     * @private
     */
    _pickColor: function (colorElement) {
        var self = this;
        var $color = $(colorElement);
        var colorName = $color.data('color');
        var colorType = $color.data('colorType');

        return new Promise(function (resolve, reject) {
            var colorpicker = new ColorpickerDialog(self, {
                defaultColor: $color.css('background-color'),
            });
            var chosenColor = undefined;
            colorpicker.on('colorpicker:saved', self, function (ev) {
                ev.stopPropagation();
                chosenColor = ev.data.cssColor;
            });
            colorpicker.on('closed', self, function (ev) {
                if (chosenColor === undefined) {
                    resolve();
                    return;
                }

                var baseURL = '/website/static/src/scss/options/colors/';
                var url = _.str.sprintf('%suser_%scolor_palette.scss', baseURL, (colorType ? (colorType + '_') : ''));

                var colors = {};
                colors[colorName] = chosenColor;
                if (colorName === 'alpha') {
                    colors['beta'] = 'null';
                    colors['gamma'] = 'null';
                    colors['delta'] = 'null';
                    colors['epsilon'] = 'null';
                }

                self._makeSCSSCusto(url, colors).then(resolve).guardedCatch(resolve);
            });
            colorpicker.open();
        });
    },
    /**
     * @private
     */
    _processChange: function ($inputs) {
        var self = this;
        var defs = [];

        var $options = $inputs.closest('.o_theme_customize_option');

        // Handle body image changes
        var $bodyImageInputs = $inputs.filter('[data-xmlid*="website.' + this.CUSTOM_BODY_IMAGE_XML_ID + '"]:checked');
        defs = defs.concat(_.map($bodyImageInputs, function () {
            return self._chooseBodyCustomImage();
        }));

        // Handle color changes
        var $colors = $options.find('.o_theme_customize_color');
        defs = defs.concat(_.map($colors, function (colorElement) {
            return self._pickColor($(colorElement));
        }));

        // Handle input changes
        var $inputsData = $options.find('.o_theme_customize_input');
        defs = defs.concat(_.map($inputsData, function (inputData, i) {
            return self._quickEdit($(inputData));
        }));

        // Handle auto changes
        var $autoWidgetOptions = $options.has('.o_theme_customize_auto');
        if ($autoWidgetOptions.length > 1) {
            $autoWidgetOptions = $autoWidgetOptions.has('input:checked');
        }
        var $autosData = $autoWidgetOptions.find('.o_theme_customize_auto');
        defs = defs.concat(_.map($autosData, function (autoData) {
            return self._setAuto($(autoData));
        }));

        return Promise.all(defs);
    },
    /**
     * @private
     */
    _quickEdit: function ($inputData) {
        var self = this;
        var text = $inputData.text().trim();
        var value = parseFloat(text) || '';
        var unit = text.match(/([^\s\d]+)$/)[1];

        return new Promise(function (resolve, reject) {
            var qEdit = new QuickEdit(self, value, unit);
            qEdit.on('QuickEdit:save', self, function (ev) {
                ev.stopPropagation();

                var value = ev.data.value;
                // Convert back to rem if needed
                if ($inputData.data('unit') === 'rem' && unit === 'px' && value !== 'null') {
                    value = parseFloat(value) / self.PX_BY_REM + 'rem';
                }

                var values = {};
                values[$inputData.data('variable')] = value;
                self._makeSCSSCusto('/website/static/src/scss/options/user_values.scss', values)
                    .then(resolve)
                    .guardedCatch(resolve);
            });
            qEdit.appendTo($inputData.closest('.o_theme_customize_option'));
        });
    },
    /**
     * @private
     */
    _setAuto: function ($autoData) {
        var self = this;
        var values = {};
        var isChecked = $autoData.siblings('.o_theme_customize_option_input').prop('checked');
        values[$autoData.data('variable')] = isChecked ? $autoData.data('value') : 'null';

        return new Promise(function (resolve, reject) {
            self._makeSCSSCusto('/website/static/src/scss/options/user_values.scss', values)
                .then(resolve)
                .guardedCatch(resolve);
        });
    },
    /**
     * @private
     */
    _setActive: function () {
        var self = this;

        // First enforce that all input groups have only one element checked as
        // it is supposed to be (it might not be the case on initialization, for
        // exemple if we had data-xmlid="A" and data-xmlid="A,B" and if A and B
        // are active, the 2 related inputs would be checked).
        var $radioXMLInputs = this.$inputs.filter('[type="radio"][data-xmlid]');
        var optionNames = _.uniq(_.map($radioXMLInputs, function (option) {
            return option.name;
        }));
        _.each(optionNames, function (optionName) {
            var $inputs = $radioXMLInputs.filter('[name="' + optionName + '"]:checked');
            if ($inputs.length > 1) {
                $inputs.prop('checked', false);

                var maxNbXMLIDs = -1;
                var $maxInput = null;
                _.each($inputs, function (input) {
                    var $input = $(input);
                    var xmlID = $input.data('xmlid');
                    var nbXMLIDs = xmlID ? xmlID.split(',').length : 0;
                    if (nbXMLIDs >= maxNbXMLIDs) {
                        maxNbXMLIDs = nbXMLIDs;
                        $maxInput = $input;
                    }
                });
                $maxInput.prop('checked', true);
            }
        });

        // Look at all options to see if they are enabled or disabled
        var $enable = this.$inputs.filter(':checked');

        // Mark the labels as checked accordingly
        this.$('label').removeClass('checked');
        $enable.closest('label:not(.o_switch)').addClass('checked');

        // Mark the option sets as checked if all their option are checked/unchecked
        var $sets = this.$inputs.filter('[data-enable], [data-disable]').not('[data-xmlid]');
        _.each($sets, function (set) {
            var $set = $(set);
            var checked = true;
            if (self._getInputs($set.data('enable')).not(':checked').length) {
                checked = false;
            }
            if (self._getInputs($set.data('disable')).filter(':checked').length) {
                checked = false;
            }
            $set.prop('checked', checked).closest('label:not(.o_switch)').toggleClass('checked', checked);
        });

        // Make the hidden sections visible if their dependencies are met
        _.each(this.$('[data-depends]'), function (hidden) {
            var $hidden = $(hidden);
            var depends = $hidden.data('depends');
            var dependencies = depends ? depends.split(/\s*,\s*/g) : [];
            var enabled = _.all(dependencies, function (dep) {
                var toBeChecked = (dep[0] !== '!');
                if (!toBeChecked) {
                    dep = dep.substr(1);
                }
                return self._getInputs(dep).is(':checked') === toBeChecked;
            });
            $hidden.toggleClass('d-none', !enabled);
        });
    },
    /**
     * @private
     */
    _updateStyle: function (enable, disable, reload) {
        var self = this;

        var $loading = $('<i/>', {class: 'fa fa-refresh fa-spin'});
        this.$modal.find('.modal-title').append($loading);

        if (reload || config.isDebug('assets')) {
            window.location.href = $.param.querystring('/website/theme_customize_reload', {
                href: window.location.href,
                enable: (enable || []).join(','),
                disable: (disable || []).join(','),
                tab: this.$('.nav-link.active').parent().index(),
            });
            return Promise.resolve();
        }

        return this._rpc({
            route: '/website/theme_customize',
            params: {
                'enable': enable,
                'disable': disable,
                'get_bundle': true,
            },
        }).then(function (bundles) {
            var $allLinks = $();
            var defs = _.map(bundles, function (bundleURLs, bundleName) {
                var $links = $('link[href*="' + bundleName + '"]');
                $allLinks = $allLinks.add($links);
                var $newLinks = $();
                _.each(bundleURLs, function (url) {
                    $newLinks = $newLinks.add($('<link/>', {
                        type: 'text/css',
                        rel: 'stylesheet',
                        href: url,
                    }));
                });

                var linksLoaded = new Promise(function (resolve, reject) {
                    var nbLoaded = 0;
                    $newLinks.on('load', function () {
                        if (++nbLoaded >= $newLinks.length) {
                            resolve();
                        }
                    });
                    $newLinks.on('error', function () {
                        reject();
                        window.location.hash = 'theme=true';
                        window.location.reload();
                    });
                });
                $links.last().after($newLinks);
                return linksLoaded;
            });
            return Promise.all(defs).then(function () {
                $loading.remove();
                $allLinks.remove();
            }).guardedCatch(function () {
                $loading.remove();
                $allLinks.remove();
            });
        }).then(function () {
            // Some public widgets may depend on the variables that were
            // customized, so we have to restart them.
            self.trigger_up('widgets_start_request');
        });
    },
    /**
     * @private
     */
    _updateValues: function () {
        var self = this;
        // Put user values
        _.each(this.$('.o_theme_customize_color'), function (el) {
            var $el = $(el);
            var value = self.style.getPropertyValue('--' + $el.data('color')).trim();
            $el.css('background-color', value);
        });
        _.each(this.$('.o_theme_customize_input'), function (el) {
            var $el = $(el);
            var value = self.style.getPropertyValue('--' + $el.data('variable')).trim();

            // Convert rem values to px values
            if (_.str.endsWith(value, 'rem')) {
                value = parseFloat(value) * self.PX_BY_REM + 'px';
            }

            var $span = $el.find('span');
            $span.removeClass().text('');
            switch (value) {
                case '':
                case 'false':
                case 'true':
                    // When null or a boolean value, shows an icon which tells
                    // the user that there is no numeric/text value
                    $span.addClass('fa fa-ban text-danger');
                    break;
                default:
                    $span.text(value);
            }
        });
        _.each(this.$('.o_theme_customize_dropdown'), function (dropdown) {
            var $dropdown = $(dropdown);
            $dropdown.find('.dropdown-item.active').removeClass('active');
            var $checked = $dropdown.find('label.checked');
            $checked.closest('.dropdown-item').addClass('active');

            var classes = 'btn btn-light dropdown-toggle w-100 o_text_overflow o_theme_customize_dropdown_btn';
            if ($checked.data('font-id')) {
                classes += _.str.sprintf(' o_theme_customize_option_font_%s', $checked.data('font-id'));
            }
            var $btn = $('<button/>', {
                type: 'button',
                class: classes,
                'data-toggle': 'dropdown',
                html: $dropdown.find('label.checked > span').text() || '&#8203;',
            });
            $dropdown.find('.o_theme_customize_dropdown_btn').remove();
            $dropdown.prepend($btn);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onChange: function (ev) {
        var self = this;

        // Checkout the option that changed
        var $option = $(ev.currentTarget);
        if ($option.is(':disabled')) {
            return;
        }
        this.$inputs.prop('disabled', true);

        var $options = $option;
        var checked = $option.is(':checked');

        // If it was enabled, enable/disable the related input (see data-enable,
        // data-disable) and retain the ones that actually changed
        if (checked) {
            var $inputs;
            // Input to enable
            $inputs = this._getInputs($option.data('enable'));
            $options = $options.add($inputs.filter(':not(:checked)'));
            $inputs.prop('checked', true);
            // Input to disable
            $inputs = this._getInputs($option.data('disable'));
            $options = $options.add($inputs.filter(':checked'));
            $inputs.prop('checked', false);
        }
        var optionNames = _.uniq(_.map($options, function (option) {
            return option.name;
        }));
        $options = this.$inputs.filter(function (i, input) {
            return _.contains(optionNames, input.name);
        });

        // Look at all options to see if they are enabled or disabled
        var $enable = $options.filter('[data-xmlid]:checked');
        var $disable = $options.filter('[data-xmlid]:not(:checked)');

        this._setActive();

        // Update the style according to the whole set of options
        self._processChange($options).then(function () {
            return self._updateStyle(
                self._getXMLIDs($enable),
                self._getXMLIDs($disable),
                $option.data('reload') && window.location.href.match(new RegExp($option.data('reload')))
            );
        }).then(function () {
            self._updateValues();
            self.$inputs.prop('disabled', false);
        });
    },
    /**
     * @private
     */
    _onAddGoogleFontClick: function (ev) {
        var self = this;
        var variable = $(ev.currentTarget).data('variable');
        new Dialog(this, {
            title: _t("Add a Google Font"),
            $content: $(core.qweb.render('website.dialog.addGoogleFont')),
            buttons: [
                {
                    text: _t("Save"),
                    classes: 'btn-primary',
                    click: function () {
                        var $input = this.$('.o_input_google_font');
                        var m = $input.val().match(/\bfamily=([\w+]+)/);
                        if (!m) {
                            $input.addClass('is-invalid');
                            return;
                        }
                        var font = m[1].replace(/\+/g, ' ');
                        self.googleFonts.push(font);
                        var values = {};
                        values[variable] = self.nbFonts + 1;
                        return self._makeGoogleFontsCusto(values);
                    },
                },
                {
                    text: _t("Discard"),
                    close: true,
                },
            ],
        }).open();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onDeleteGoogleFontClick: function (ev) {
        var self = this;
        ev.preventDefault();

        var nbBaseFonts = this.nbFonts - this.googleFonts.length;

        // Remove Google font
        var googleFontIndex = $(ev.currentTarget).data('fontIndex');
        this.googleFonts.splice(googleFontIndex, 1);

        // Adapt font variable indexes to the removal
        var values = {};
        _.each(this.fontVariables, function (variable) {
            var value = parseInt(self.style.getPropertyValue('--' + variable));
            var googleFontValue = nbBaseFonts + 1 + googleFontIndex;
            if (value === googleFontValue) {
                // If an element is using the google font being removed, reset
                // it to the first base font.
                values[variable] = 1;
            } else if (value > googleFontValue) {
                // If an element is using a google font whose index is higher
                // than the one of the font being removed, that index must be
                // lowered by 1 so that the font is unchanged.
                values[variable] = value - 1;
            }
        });

        return this._makeGoogleFontsCusto(values);
    },
});

var ThemeCustomizeMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    actions: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.prototype.actions || {}, {
        'customize_theme': '_openThemeCustomizeDialog',
    }),

    /**
     * Automatically opens the theme customization dialog if the corresponding
     * hash is in the page URL.
     *
     * @override
     */
    start: function () {
        if ((window.location.hash || '').indexOf('theme=true') > 0) {
            var tab = window.location.hash.match(/tab=(\d+)/);
            this._openThemeCustomizeDialog(tab ? tab[1] : false);
            window.location.hash = '';
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Instantiates and opens the theme customization dialog.
     *
     * @private
     * @param {string} tab
     * @returns {Promise}
     */
    _openThemeCustomizeDialog: function (tab) {
        return new ThemeCustomizeDialog(this, {tab: tab}).open();
    },
});

websiteNavbarData.websiteNavbarRegistry.add(ThemeCustomizeMenu, '#theme_customize');

return ThemeCustomizeDialog;
});
