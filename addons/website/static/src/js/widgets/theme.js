odoo.define('website.theme', function (require) {
'use strict';

var config = require('web.config');
var core = require('web.core');
var ColorpickerDialog = require('web.colorpicker');
var Dialog = require('web.Dialog');
var weContext = require('web_editor.context');
var widgets = require('web_editor.widget');
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
            title: _t("Customize this theme"),
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
                args: ['website.theme_customize', weContext.get()],
            }).then(function (data) {
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

                switch (item.tagName) {
                    case 'OPT':
                        var colorPalette = $item.data('colorPalette');
                        var icon = $item.data('icon');

                        // Build the options template
                        var $multiChoiceLabel = $(core.qweb.render('website.theme_customize_modal_option', {
                            name: optionsName,
                            id: $item.attr('id') || _.uniqueId('o_theme_customize_input_id_'),

                            string: $item.attr('string'),
                            icon: icon,
                            color: $item.data('color'),
                            font: $item.data('font'),

                            colorPalette: colorPalette,

                            xmlid: $item.data('xmlid'),
                            enable: $item.data('enable'),
                            disable: $item.data('disable'),
                            reload: $item.data('reload'),
                        }));

                        if ($container.hasClass('form-row')) {
                            var $col = $('<div/>', {class: (icon ? 'col-4' : (colorPalette ? 'col-12' : 'col-6'))});
                            $col.append($multiChoiceLabel);
                            $container.append($col);
                        } else {
                            $container.append($multiChoiceLabel);
                        }
                        break;

                    case 'MORE':
                        var collapseID = _.uniqueId('collapse-');

                        var $col = $('<div/>', {
                            class: 'col-12',
                        }).appendTo($container);

                        var string = $item.attr('string');
                        if (string) {
                            var $button = $('<button/>', {
                                'type': 'button',
                                class: 'btn btn-primary d-block mx-auto mt-3 collapsed',
                                'data-toggle': 'collapse',
                                'data-target': "#" + collapseID,
                                text: string,
                            });
                            $col.append($button);
                        }

                        var $collapse = $('<div/>',{
                            id: collapseID,
                            class: 'collapse form-row justify-content-between mt-3',
                            'data-depends': $item.data('depends'),
                        });
                        $col.append($collapse);

                        _processItems($item.children(), $collapse);
                        break;

                    case 'LIST':
                        var $listContainer = $('<div/>', {class: 'py-1 px-2 o_theme_customize_option_list'});
                        var $col = $('<div/>', {
                            class: 'col-6 mt-2',
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
            Dialog.alert(this, error.data.message)
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
        var $inputBodyCustomImage = $inputs.filter('[data-xmlid*="website.' + bodyCustomImageXMLID + '"]');
        if (!$inputBodyCustomImage.length) {
            return $.when();
        }

        var def = $.Deferred();
        var $image = $('<img/>');
        var editor = new widgets.MediaDialog(this, {onlyImages: true, firstFilters: ['background']}, null, $image[0]);

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
                        weContext.get(),
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
        var $disable = this.$inputs.filter('[data-xmlid]:not(:checked)');

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

        // Mark the collapsed section as visible if their dependencies are met
        var $collapsedElements = this.$('[data-depends]');
        _.each($collapsedElements, function (collapsed) {
            var $collapsed = $(collapsed);
            var enabled = true;
            if (self._getInputs($collapsed.data('depends')).not(':checked').length) {
                enabled = false;
            }

            if ($collapsed.is('.collapse')) {
                $collapsed.collapse(enabled ? 'show' : 'hide');
            } else {
                $collapsed.toggleClass('d-none', !enabled);
            }
        });
    },
    /**
     * @private
     */
    _updateStyle: function (enable, disable, reload) {
        if (reload || config.debug === 'assets') {
            window.location.href = $.param.querystring('/website/theme_customize_reload', {
                href: window.location.href,
                enable: enable.join(','),
                disable: disable.join(','),
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

        // If it was enabled, enable/disable the related input (see data-enable, data-disable)
        // and retain the ones that actually changed
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

        // Look at all options to see if they are enabled or disabled
        var $enable = this.$inputs.filter('[data-xmlid]:checked');
        var $disable = this.$inputs.filter('[data-xmlid]:not(:checked)');

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
            defaultColor: $color.find('span').css('background-color'),
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
                    bundles: false,
                    bundles_restriction: [],
                },
            }).then(function (data) {
                var files = data.scss[0][1];
                var file = _.find(files, function (file) {
                    switch (colorType) {
                        case 'theme':
                            return file.url === '/website/static/src/scss/options/colors/user_theme_color_palette.scss';
                        case 'typo':
                            return file.url === '/website/static/src/scss/options/colors/user_color_palette_typo.scss';
                    }
                    return file.url === '/website/static/src/scss/options/colors/user_color_palette_' + colorName + '.scss';
                });

                var colors = {};
                colors[colorName] = ev.data.hex;
                if (colorName === 'primary') {
                    colors['secondary'] = 'null';
                    colors['gamma'] = 'null';
                    colors['delta'] = 'null';
                    colors['epsilon'] = 'null';
                }

                var updatedFileContent = file.arch;
                _.each(colors, function (colorValue, colorName) {
                    updatedFileContent = updatedFileContent.replace(new RegExp(colorName + ': (?:null|#[a-fA-F0-9]{6}),'), colorName + ': ' + colorValue + ',');
                });

                return self._rpc({
                    route: '/web_editor/save_scss',
                    params: {
                        url: file.url,
                        bundle_xmlid: 'web.assets_common',
                        content: updatedFileContent,
                    },
                });
            }).then(function () {
                self.$('#' + $color.closest('.o_theme_customize_color_previews').data('depends')).click();
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
        var def;
        if ((window.location.hash || '').indexOf('theme=true') > 0) {
            var tab = window.location.hash.match(/tab=(\d+)/);
            def = this._openThemeCustomizeDialog(tab ? tab[1] : false);
            window.location.hash = '';
        }
        return $.when(this._super.apply(this, arguments), def);
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