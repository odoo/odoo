odoo.define('website.theme', function (require) {
'use strict';

var config = require('web.config');
var core = require('web.core');
var ColorpickerDialog = require('wysiwyg.widgets.ColorpickerDialog');
var Dialog = require('web.Dialog');
var weWidgets = require('wysiwyg.widgets');
var websiteNavbarData = require('website.navbar');

var _t = core._t;

var templateDef = null;

var ThemeCustomizeDialog = Dialog.extend({
    xmlDependencies: (Dialog.prototype.xmlDependencies || [])
        .concat(['/website/static/src/xml/website.editor.xml']),

    template: 'website.theme_customize',
    events: {
        'change [data-xmlid], [data-enable], [data-disable]': '_onChange',
        'click .checked [data-xmlid], .checked [data-enable], .checked [data-disable]': '_onChange',
        'click .o_theme_customize_color': '_onColorClick',
    },

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
        this._generateDialogHTML();
        this.$modal.addClass('o_theme_customize_modal');

        // Enable the first option tab or the given default tab
        var $tabs = this.$('[data-toggle="tab"]');
        this.opened().then(function () {
            $tabs.eq(self.defaultTab).tab('show');

            var $colorPreview = self.$('.o_theme_customize_color_previews:visible');
            var $primary = $colorPreview.find('.o_theme_customize_color[data-color="primary"]');
            var $alpha = $colorPreview.find('.o_theme_customize_color[data-color="alpha"]');
            var $secondary = $colorPreview.find('.o_theme_customize_color[data-color="secondary"]');
            var $beta = $colorPreview.find('.o_theme_customize_color[data-color="beta"]');
            var sameAlphaPrimary = $primary.find('.o_color_preview').css('background-color') === $alpha.find('.o_color_preview').css('background-color');
            var sameBetaSecondary = $secondary.find('.o_color_preview').css('background-color') === $beta.find('.o_color_preview').css('background-color');
            if (!sameAlphaPrimary) {
                $alpha.find('.o_color_name').text(_t("Extra Color"));
                $primary.removeClass('d-none').addClass('d-flex');
            }
            if (!sameBetaSecondary) {
                $beta.find('.o_color_name').text(_t("Extra Color"));
                $secondary.removeClass('d-none').addClass('d-flex');
            }
            if (!sameAlphaPrimary && sameBetaSecondary) {
                $beta.insertBefore($alpha);
            } else if (sameAlphaPrimary && !sameBetaSecondary) {
                $secondary.insertAfter($alpha);
            }
        });

        // Hide the tab navigation if only one tab
        if ($tabs.length <= 1) {
            $tabs.closest('.nav').addClass('d-none');
        }

        this.$inputs = this.$('[data-xmlid], [data-enable], [data-disable]');

        return $.when(
            this._super.apply(this, arguments),
            this._loadViews()
        );
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _generateDialogHTML: function () {
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

        function _processItems($items, $container) {
            var optionsName = _.uniqueId('option-');

            _.each($items, function (item) {
                var $item = $(item);
                var $col;

                switch (item.tagName) {
                    case 'OPT':
                        var widgetName = $item.data('widget');

                        // Build the options template
                        var $option = $(core.qweb.render('website.theme_customize_modal_option', {
                            name: optionsName,
                            id: $item.attr('id') || _.uniqueId('o_theme_customize_input_id_'),

                            string: $item.attr('string'),
                            icon: $item.data('icon'),
                            font: $item.data('font'),

                            xmlid: $item.data('xmlid'),
                            enable: $item.data('enable'),
                            disable: $item.data('disable'),
                            reload: $item.data('reload'),

                            widget: widgetName,
                        }));

                        if (widgetName) {
                            var $widget = $(core.qweb.render('website.theme_customize_' + widgetName));
                            $option.append($widget);
                        }

                        if ($container.hasClass('form-row')) {
                            $col = $('<div/>', {
                                class: _.str.sprintf('col-%s', $item.data('col') || 6),
                            });
                            $col.append($option);
                            $container.append($col);
                        } else {
                            $container.append($option);
                        }
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
                }
            });
        }
    },
    /**
     * @private
     */
    _loadViews: function () {
        var self = this;
        return this._rpc({
            route: '/website/theme_customize_get',
            params: {
                xml_ids: this._getXMLIDs(this.$inputs),
            },
        }).done(function (data) {
            self.$inputs.prop('checked', false);
            _.each(self.$inputs.filter('[data-xmlid]:not([data-xmlid=""])'), function (input) {
                var $input = $(input);
                if (!_.difference(self._getXMLIDs($input), data[0]).length) {
                    $input.prop('checked', true);
                }
            });
            _.each(self.$inputs.filter('[data-xmlid=""]'), function (input) {
                var $input = $(input);
                if (!self.$inputs.filter('[name="' + $input.attr('name') + '"]:checked').length) {
                    $input.prop('checked', true);
                }
            });
            self._setActive();
        }).fail(function (d, error) {
            Dialog.alert(this, error.data.message);
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
    _processChange: function ($inputs) {
        var self = this;
        this.$modal.addClass('o_theme_customize_loading');

        var bodyCustomImageXMLID = 'option_custom_body_image';
        var $inputBodyCustomImage = $inputs.filter('[data-xmlid*="website.' + bodyCustomImageXMLID + '"]:checked');
        if (!$inputBodyCustomImage.length) {
            return $.when();
        }

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
                args: ['website', bodyCustomImageXMLID],
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
            }).then(function () {
                def.resolve();
            });
        });
        editor.on('cancel', this, function () {
            def.resolve();
        });

        editor.open();

        return def;
    },
    /**
     * @private
     */
    _setActive: function () {
        var self = this;

        // Look at all options to see if they are enabled or disabled
        var $enable = this.$inputs.filter('[data-xmlid]:checked');

        // Mark the labels as checked accordingly
        this.$('label').removeClass('checked');
        $enable.closest('label').addClass('checked');

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
            $set.prop('checked', checked).closest('label').toggleClass('checked', checked);
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
        if (reload || config.debug === 'assets') {
            window.location.href = $.param.querystring('/website/theme_customize_reload', {
                href: window.location.href,
                enable: (enable || []).join(','),
                disable: (disable || []).join(','),
                tab: this.$('.nav-link.active').parent().index(),
            });
            return $.Deferred();
        }

        var self = this;
        return this._rpc({
            route: '/website/theme_customize',
            params: {
                enable: enable,
                disable: disable,
                get_bundle: true,
            },
        }).then(function (bundles) {
            var defs = _.map(bundles, function (bundleContent, bundleName) {
                var linkSelector = 'link[href*="' + bundleName + '"]';
                var $links = $(linkSelector);
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
                return linksLoaded.then(function () {
                    $links.remove();
                });
            });

            return $.when.apply($, defs).then(function () {
                self.$modal.removeClass('o_theme_customize_loading');
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
            self._updateStyle(
                self._getXMLIDs($enable),
                self._getXMLIDs($disable),
                $option.data('reload') && window.location.href.match(new RegExp($option.data('reload')))
            );
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onColorClick: function (ev) {
        var self = this;
        var $color = $(ev.currentTarget);
        var colorName = $color.data('color');
        var colorType = $color.data('colorType');

        var colorpicker = new ColorpickerDialog(this, {
            defaultColor: $color.find('.o_color_preview').css('background-color'),
        });
        colorpicker.on('colorpicker:saved', this, function (ev) {
            ev.stopPropagation();

            // TODO improve to be more efficient
            self._rpc({
                route: '/web_editor/get_assets_editor_resources',
                params: {
                    key: 'website.layout',
                    get_views: false,
                    get_scss: true,
                    get_js: false,
                    bundles: false,
                    bundles_restriction: [],
                    only_user_custom_files: false,
                },
            }).then(function (data) {
                var files = data.scss[0][1];
                var file = _.find(files, function (file) {
                    var baseURL = '/website/static/src/scss/options/colors/';
                    return file.url === _.str.sprintf('%suser_%scolor_palette.scss', baseURL, (colorType ? (colorType + '_') : ''));
                });

                var colors = {};
                colors[colorName] = ev.data.cssColor;
                if (colorName === 'alpha') {
                    colors['beta'] = 'null';
                    colors['gamma'] = 'null';
                    colors['delta'] = 'null';
                    colors['epsilon'] = 'null';
                }

                var updatedFileContent = file.arch;
                _.each(colors, function (colorValue, colorName) {
                    var pattern = _.str.sprintf("'%s': %%s,\n", colorName);
                    var regex = new RegExp(_.str.sprintf(pattern, ".+"));
                    var replacement = _.str.sprintf(pattern, colorValue);
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
                        url: file.url,
                        bundle_xmlid: 'web.assets_common',
                        content: updatedFileContent,
                        file_type: 'scss',
                    },
                });
            }).then(function () {
                return self._updateStyle();
            });
        });
        colorpicker.open();
    },
});

var ThemeCustomizeMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    actions: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.prototype.actions || {}, {
        customize_theme: '_openThemeCustomizeDialog',
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
