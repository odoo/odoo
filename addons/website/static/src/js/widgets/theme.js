odoo.define('website.theme', function (require) {
'use strict';

var config = require('web.config');
var core = require('web.core');
var Dialog = require('web.Dialog');
var weContext = require('web_editor.context');
var websiteNavbarData = require('website.navbar');

var _t = core._t;

var templateDef = null;

var ThemeCustomizeDialog = Dialog.extend({
    template: 'website.theme_customize',
    events: {
        'change [data-xmlid], [data-enable], [data-disable]': '_onChange',
    },

    /**
     * @constructor
     */
    init: function (parent, options) {
        this._super(parent, _.extend({
            title: _t("Customize this theme"),
        }, options || {}));
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

        this.$modal.addClass('o_theme_customize_modal');

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
     * @abstract
     * @private
     */
    _processChange: function ($inputs, event) {},
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
    },
    /**
     * @private
     */
    _updateStyle: function (enable, disable, reload) {
        this.$modal.addClass('loading');

        if (reload || config.debug === 'assets') {
            window.location.href = $.param.querystring('/website/theme_customize_reload', {
                href: window.location.href,
                enable: enable.join(','),
                disable: disable.join(','),
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
        }).then(function (bundleHTML) {
            var frontendLinkSelector = 'link[href*=".assets_frontend"]';
            var $links = $(frontendLinkSelector);
            var $newLinks = $(bundleHTML).filter(frontendLinkSelector);

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
                self.$modal.removeClass('loading');
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
        var $option = $(ev.target).find('input').addBack('input');
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
        self._processChange($options, ev);
        self._updateStyle(
            self._getXMLIDs($enable),
            self._getXMLIDs($disable),
            $option.data('reload') && window.location.href.match(new RegExp($option.data('reload')))
        );
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
            def = this._openThemeCustomizeDialog();
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
     * @returns {Deferred}
     */
    _openThemeCustomizeDialog: function () {
        return new ThemeCustomizeDialog(this).open();
    },
});

websiteNavbarData.websiteNavbarRegistry.add(ThemeCustomizeMenu, '#theme_customize');

return ThemeCustomizeDialog;
});