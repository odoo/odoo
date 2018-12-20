odoo.define('website.theme', function (require) {
'use strict';

var config = require('web.config');
var core = require('web.core');
var Dialog = require('web.Dialog');
var weWidgets = require('wysiwyg.widgets');
var ColorpickerDialog = require('wysiwyg.widgets.ColorpickerDialog');
var websiteNavbarData = require('website.navbar');

var _t = core._t;

var templateDef = null;

var ThemeCustomizeDialog = Dialog.extend({
    xmlDependencies: (Dialog.prototype.xmlDependencies || [])
        .concat(['/website/static/src/xml/website.editor.xml']),

    template: 'website.theme_customize',
    events: {
        'change .o_theme_customize_option_input': '_onChange',
        'click .checked .o_theme_customize_option_input[type="radio"]': '_onChange',
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
        return $.when(this._super.apply(this, arguments), templateDef);
    },
    /**
     * @override
     */
    start: function () {
        var self = this;

        this.$modal.addClass('o_theme_customize_modal');

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

        return $.when(this._super.apply(this, arguments), loadDef);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _chooseBodyCustomImage: function () {
        var self = this;
        var def = $.Deferred();
        var $image = $('<img/>');
        var editor = new weWidgets.MediaDialog(this, {
            onlyImages: true,
            firstFilters: ['background'],
        }, $image[0]);

        editor.on('save', this, function (media) { // TODO use scss customization instead (like for user colors)
            var src = $(media).attr('src');
            self._rpc({
                model: 'ir.model.data',
                method: 'get_object_reference',
                args: ['website', this.CUSTOM_BODY_IMAGE_XML_ID],
            }).then(function (data) {
                return self._rpc({
                    model: 'ir.ui.view',
                    method: 'save',
                    args: [
                        data[1],
                        '#wrapwrap { background-image: url("' + src + '"); }',
                        '//style',
                    ],
                });
            }).always(def.resolve.bind(def));
        });
        editor.on('cancel', this, function () {
            def.resolve();
        });

        editor.open();

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
            _processItems($content.children(), $optionsContainer);
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

        function _processItems($items, $container) {
            var optionsName = _.uniqueId('option-');
            var alone = ($items.length === 1);

            _.each($items, function (item) {
                var $item = $(item);
                var $col;

                switch (item.tagName) {
                    case 'OPT':
                        var widgetName = $item.data('widget');

                        var xmlid = $item.data('xmlid');

                        var renderingOptions = _.extend({
                            string: $item.attr('string') || data.names[xmlid.split(',')[0].trim()],
                            icon: $item.data('icon'),
                            font: $item.data('font'),
                        }, $item.data());

                        // Build the options template
                        var $option = $(core.qweb.render('website.theme_customize_modal_option', _.extend({
                            alone: alone,
                            name: xmlid === undefined ? _.uniqueId('option-') : optionsName,
                            id: $item.attr('id') || _.uniqueId('o_theme_customize_input_id_'),
                            checked: xmlid === undefined || xmlid && (!_.difference(self._getXMLIDs($item), data.enabled).length),
                            widget: widgetName,
                        }, renderingOptions)));
                        $option.find('input')
                            .addClass('o_theme_customize_option_input')
                            .attr({
                                'data-xmlid': xmlid,
                                'data-enable': $item.data('enable'),
                                'data-disable': $item.data('disable'),
                                'data-reload': $item.data('reload'),
                            });

                        if (widgetName) {
                            var $widget = $(core.qweb.render('website.theme_customize_widget_' + widgetName, renderingOptions));
                            $option.find('label').append($widget);
                        }

                        var $final;
                        if ($container.hasClass('form-row')) {
                            $final = $('<div/>', {
                                class: _.str.sprintf('col-%s', $item.data('col') || 6),
                            });
                            $final.append($option);
                        } else {
                            $final = $option;
                        }
                        $final.attr('data-depends', $item.data('depends'));
                        $container.append($final);
                        break;

                    case 'LIST':
                        var $listContainer = $('<div/>', {class: 'py-1 px-2 o_theme_customize_option_list'});
                        $col = $('<div/>', {
                            class: _.str.sprintf('col-%s mt-2', $item.data('col') || 6),
                            'data-depends': $item.data('depends'),
                        }).append($('<h6/>', {text: $item.attr('string')}), $listContainer);
                        $container.append($col);
                        _processItems($item.children(), $listContainer);
                        break;

                    default:
                        _processItems($item.children(), $container);
                        break;
                }
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
     */
    _makeSCSSCusto: function (url, values) {
        var self = this;
        return this._rpc({ // TODO improve to be more efficient
            route: '/web_editor/get_assets_editor_resources',
            params: {
                'key': 'website.layout',
                'get_views': false,
                'get_scss': true,
                'get_js': false,
                'bundles': false,
                'bundles_restriction': [],
                'only_user_custom_files': false,
            },
        }).then(function (data) {
            var file = _.find(data.scss[0][1], function (file) {
                return file.url === url;
            });

            var updatedFileContent = file.arch;
            _.each(values, function (value, name) {
                var pattern = _.str.sprintf("'%s': %%s,\n", name);
                var regex = new RegExp(_.str.sprintf(pattern, ".+"));
                var replacement = _.str.sprintf(pattern, value);
                if (regex.test(updatedFileContent)) {
                    updatedFileContent = updatedFileContent
                        .replace(regex, replacement);
                } else {
                    updatedFileContent = updatedFileContent
                        .replace(/( *)(.*hook.*)/, _.str.sprintf('$1%s$1$2', replacement));
                }
            });

            return self._rpc({
                route: '/web_editor/save_scss_or_js',
                params: {
                    'url': file.url,
                    'bundle_xmlid': 'web.assets_common',
                    'content': updatedFileContent,
                    'file_type': 'scss',
                },
            });
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

        var def = $.Deferred();

        var colorpicker = new ColorpickerDialog(this, {
            defaultColor: $color.css('background-color'),
        });
        var chosenColor = undefined;
        colorpicker.on('colorpicker:saved', this, function (ev) {
            ev.stopPropagation();
            chosenColor = ev.data.cssColor;
        });
        colorpicker.on('closed', this, function (ev) {
            if (chosenColor === undefined) {
                def.resolve();
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

            self._makeSCSSCusto(url, colors).always(def.resolve.bind(def));
        });
        colorpicker.open();

        return def;
    },
    /**
     * @private
     */
    _processChange: function ($inputs) {
        var self = this;
        var defs = [];

        // Handle body image changes
        var $bodyImageInputs = $inputs.filter('[data-xmlid*="website.' + this.CUSTOM_BODY_IMAGE_XML_ID + '"]:checked');
        defs = defs.concat(_.map($bodyImageInputs, function () {
            return self._chooseBodyCustomImage();
        }));

        // Handle color changes
        var $colors = $inputs.closest('.o_theme_customize_option').find('.o_theme_customize_color');
        defs = defs.concat(_.map($colors, function (colorElement) {
            return self._pickColor($(colorElement));
        }));

        return $.when.apply($, defs);
    },
    /**
     * @private
     */
    _setActive: function () {
        var self = this;

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
            var nbDependencies = depends ? depends.split(',').length : 0;
            var enabled = self._getInputs(depends).filter(':checked').length === nbDependencies;
            $hidden.toggleClass('d-none', !enabled);
        });
    },
    /**
     * @private
     */
    _updateStyle: function (enable, disable, reload) {
        var $loading = $('<i/>', {class: 'fa fa-refresh fa-spin'});
        this.$modal.find('.modal-title').append($loading);

        if (reload || config.debug === 'assets') {
            window.location.href = $.param.querystring('/website/theme_customize_reload', {
                href: window.location.href,
                enable: (enable || []).join(','),
                disable: (disable || []).join(','),
                tab: this.$('.nav-link.active').parent().index(),
            });
            return $.Deferred();
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
            var defs = _.map(bundles, function (bundleContent, bundleName) {
                var linkSelector = 'link[href*="' + bundleName + '"]';
                var $links = $(linkSelector);
                $allLinks = $allLinks.add($links);
                var $newLinks = $(bundleContent).filter(linkSelector);

                var linksLoaded = $.Deferred();
                var nbLoaded = 0;
                $newLinks.on('load', function (e) {
                    if (++nbLoaded >= $newLinks.length) {
                        linksLoaded.resolve();
                    }
                });
                $newLinks.on('error', function (e) {
                    linksLoaded.reject();
                    window.location.hash = 'theme=true';
                    window.location.reload();
                });
                $links.last().after($newLinks);
                return linksLoaded;
            });

            return $.when.apply($, defs).always(function () {
                $loading.remove();
                $allLinks.remove();
            });
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
            self.$inputs.prop('disabled', false);
        });
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
     * @returns {Deferred}
     */
    _openThemeCustomizeDialog: function (tab) {
        return new ThemeCustomizeDialog(this, {tab: tab}).open();
    },
});

websiteNavbarData.websiteNavbarRegistry.add(ThemeCustomizeMenu, '#theme_customize');

return ThemeCustomizeDialog;
});
