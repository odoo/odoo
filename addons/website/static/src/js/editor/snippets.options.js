odoo.define('website.editor.snippets.options', function (require) {
'use strict';

const ColorpickerDialog = require('web.ColorpickerDialog');
const config = require('web.config');
var core = require('web.core');
var Dialog = require('web.Dialog');
const wUtils = require('website.utils');
var options = require('web_editor.snippets.options');
require('website.s_popup_options');

var _t = core._t;
var qweb = core.qweb;

const InputUserValueWidget = options.userValueWidgetsRegistry['we-input'];
const SelectUserValueWidget = options.userValueWidgetsRegistry['we-select'];

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

const FontFamilyPickerUserValueWidget = SelectUserValueWidget.extend({
    xmlDependencies: (SelectUserValueWidget.prototype.xmlDependencies || [])
        .concat(['/website/static/src/xml/website.editor.xml']),
    events: _.extend({}, SelectUserValueWidget.prototype.events || {}, {
        'click .o_we_add_google_font_btn': '_onAddGoogleFontClick',
        'click .o_we_delete_google_font_btn': '_onDeleteGoogleFontClick',
    }),
    fontVariables: [], // Filled by editor menu when all options are loaded

    /**
     * @override
     */
    start: async function () {
        const style = window.getComputedStyle(document.documentElement);
        this.nbFonts = parseInt(style.getPropertyValue('--number-of-fonts'));
        const googleFontsProperty = style.getPropertyValue('--google-fonts').trim();
        this.googleFonts = googleFontsProperty ? googleFontsProperty.split(/\s*,\s*/g) : [];

        await this._super(...arguments);

        const fontEls = [];
        const methodName = this.el.dataset.methodName || 'customizeWebsite';
        const variable = this.el.dataset.variable;
        _.times(this.nbFonts, fontNb => {
            const realFontNb = fontNb + 1;
            const fontEl = document.createElement('we-button');
            fontEl.classList.add(`o_we_option_font_${realFontNb}`);
            fontEl.dataset.variable = variable;
            fontEl.dataset[methodName] = realFontNb;
            fontEl.dataset.font = realFontNb;
            fontEls.push(fontEl);
            this.menuEl.appendChild(fontEl);
        });

        if (this.googleFonts.length) {
            const googleFontsEls = fontEls.slice(-this.googleFonts.length);
            googleFontsEls.forEach((el, index) => {
                $(el).append(core.qweb.render('website.delete_google_font_btn', {
                    index: index,
                }));
            });
        }
        $(this.menuEl).append($(core.qweb.render('website.add_google_font_btn', {
            variable: variable,
        })));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _updateUI: async function () {
        await this._super(...arguments);

        for (const className of this.menuTogglerEl.classList) {
            if (className.match(/^o_we_option_font_\d+$/)) {
                this.menuTogglerEl.classList.remove(className);
            }
        }
        const activeWidget = this._userValueWidgets.find(widget => !widget.isPreviewed() && widget.isActive());
        this.menuTogglerEl.classList.add(`o_we_option_font_${activeWidget.el.dataset.font}`);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAddGoogleFontClick: function (ev) {
        const variable = $(ev.currentTarget).data('variable');
        const dialog = new Dialog(this, {
            title: _t("Add a Google Font"),
            $content: $(core.qweb.render('website.dialog.addGoogleFont')),
            buttons: [
                {
                    text: _t("Save & Reload"),
                    classes: 'btn-primary',
                    click: () => {
                        const inputEl = dialog.el.querySelector('.o_input_google_font');
                        const m = inputEl.value.match(/\bfamily=([\w+]+)/);
                        if (!m) {
                            inputEl.classList.add('is-invalid');
                            return;
                        }
                        const font = m[1].replace(/\+/g, ' ');
                        this.googleFonts.push(font);
                        const values = {};
                        values[variable] = this.nbFonts + 1;
                        this.trigger_up('google_fonts_custo_request', {
                            values: values,
                            googleFonts: this.googleFonts,
                        });
                    },
                },
                {
                    text: _t("Discard"),
                    close: true,
                },
            ],
        });
        dialog.open();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onDeleteGoogleFontClick: async function (ev) {
        ev.preventDefault();

        const save = await new Promise(resolve => {
            Dialog.confirm(this, _t("Deleting a font requires a reload of the page. This will save all your changes and reload the page, are you sure you want to proceed?"), {
                confirm_callback: () => resolve(true),
                cancel_callback: () => resolve(false),
            });
        });
        if (!save) {
            return;
        }

        const nbBaseFonts = this.nbFonts - this.googleFonts.length;

        // Remove Google font
        const googleFontIndex = parseInt(ev.target.dataset.fontIndex);
        this.googleFonts.splice(googleFontIndex, 1);

        // Adapt font variable indexes to the removal
        const values = {};
        const style = window.getComputedStyle(document.documentElement);
        _.each(FontFamilyPickerUserValueWidget.prototype.fontVariables, variable => {
            const value = parseInt(style.getPropertyValue('--' + variable));
            const googleFontValue = nbBaseFonts + 1 + googleFontIndex;
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

        this.trigger_up('google_fonts_custo_request', {
            values: values,
            googleFonts: this.googleFonts,
        });
    },
});

options.userValueWidgetsRegistry['we-urlpicker'] = UrlPickerUserValueWidget;
options.userValueWidgetsRegistry['we-fontfamilypicker'] = FontFamilyPickerUserValueWidget;

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

options.Class.include({
    xmlDependencies: (options.Class.prototype.xmlDependencies || [])
        .concat(['/website/static/src/xml/website.editor.xml']),
    custom_events: _.extend({}, options.Class.prototype.custom_events || {}, {
        'google_fonts_custo_request': '_onGoogleFontsCustoRequest',
    }),

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    customizeWebsite: async function (previewMode, widgetValue, params) {
        // Never allow previews for theme customizations
        if (previewMode) {
            return;
        }

        if (params.color) {
            await this._customizeWebsiteColor(widgetValue, params);
        } else if (params.variable) {
            await this._customizeWebsiteVariable(widgetValue, params);
        } else {
            await this._customizeWebsiteViews(widgetValue, params);
        }

        if (params.reload || config.isDebug('assets')) {
            // Caller will reload the page, nothing needs to be done anymore.
            return;
        }

        // Finally, only update the bundles as no reload is required
        await this._reloadBundles();

        // Some public widgets may depend on the variables that were
        // customized, so we have to restart them *all*.
        await new Promise((resolve, reject) => {
            this.trigger_up('widgets_start_request', {
                editableMode: true,
                onSuccess: () => resolve(),
                onFailure: () => reject(),
            });
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: async function (methodName, params) {
        if (methodName === 'customizeWebsite') {
            if (params.color) {
                return this._getCSSColorFromName(params.color);
            }
            if (params.variable) {
                const style = window.getComputedStyle(document.documentElement);
                return style.getPropertyValue('--' + params.variable).trim();
            }

            const allXmlIDs = this._getXMLIDsFromPossibleValues(params.possibleValues);
            const enabledXmlIDs = await this._rpc({
                route: '/website/theme_customize_get',
                params: {
                    'xml_ids': allXmlIDs,
                },
            });
            let mostXmlIDsStr = '';
            let mostXmlIDsNb = 0;
            for (const xmlIDsStr of params.possibleValues) {
                const enableXmlIDs = xmlIDsStr.split(/\s*,\s*/);
                if (enableXmlIDs.length > mostXmlIDsNb
                        && enableXmlIDs.every(xmlID => enabledXmlIDs.includes(xmlID))) {
                    mostXmlIDsStr = xmlIDsStr;
                    mostXmlIDsNb = enableXmlIDs.length;
                }
            }
            return mostXmlIDsStr; // Need to return the exact same string as in possibleValues
        }
        return this._super(...arguments);
    },
    /**
     * @private
     */
    _customizeWebsiteColor: async function (color, params) {
        const baseURL = '/website/static/src/scss/options/colors/';
        const colorType = params.colorType ? (params.colorType + '_') : '';
        const url = `${baseURL}user_${colorType}color_palette.scss`;

        if (!ColorpickerDialog.isCSSColor(color)) {
            const style = window.getComputedStyle(document.documentElement);
            color = style.getPropertyValue('--' + color).trim();
            color = ColorpickerDialog.normalizeCSSColor(color);
        }
        const colors = {};
        colors[params.color] = color;
        if (params.color === 'alpha') {
            colors['beta'] = null;
            colors['gamma'] = null;
            colors['delta'] = null;
            colors['epsilon'] = null;
        }

        return this._makeSCSSCusto(url, colors);
    },
    /**
     * @private
     */
    _customizeWebsiteVariable: async function (value, params) {
        const values = {};
        values[params.variable] = value;
        return this._makeSCSSCusto('/website/static/src/scss/options/user_values.scss', values);
    },
    /**
     * @private
     */
    _customizeWebsiteViews: async function (xmlID, params) {
        const allXmlIDs = this._getXMLIDsFromPossibleValues(params.possibleValues);
        const enableXmlIDs = xmlID.split(/\s*,\s*/);
        const disableXmlIDs = allXmlIDs.filter(xmlID => !enableXmlIDs.includes(xmlID));

        return this._rpc({
            route: '/website/theme_customize',
            params: {
                'enable': enableXmlIDs,
                'disable': disableXmlIDs,
            },
        });
    },
    /**
     * @private
     * @param {string} colorName
     * @returns {string}
     */
    _getCSSColorFromName: function (colorName) {
        const style = window.getComputedStyle(document.documentElement);
        const color = style.getPropertyValue('--' + colorName).trim();
        return ColorpickerDialog.normalizeCSSColor(color);
    },
    /**
     * @private
     */
    _getXMLIDsFromPossibleValues: function (possibleValues) {
        const allXmlIDs = [];
        for (const xmlIDsStr of possibleValues) {
            allXmlIDs.push(...xmlIDsStr.split(/\s*,\s*/));
        }
        return allXmlIDs.filter((v, i, arr) => arr.indexOf(v) === i);
    },
    /**
     * @private
     */
    _makeSCSSCusto: async function (url, values) {
        return this._rpc({
            route: '/website/make_scss_custo',
            params: {
                'url': url,
                'values': _.mapObject(values, v => v || 'null'),
            },
        });
    },
    /**
     * Refreshes all public widgets related to the given element.
     *
     * @private
     * @param {jQuery} [$el=this.$target]
     * @returns {Promise}
     */
    _refreshPublicWidgets: async function ($el) {
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
     * @private
     */
    _reloadBundles: async function () {
        const bundles = await this._rpc({
            route: '/website/theme_customize_bundle_reload',
        });
        let $allLinks = $();
        const proms = _.map(bundles, (bundleURLs, bundleName) => {
            var $links = $('link[href*="' + bundleName + '"]');
            $allLinks = $allLinks.add($links);
            var $newLinks = $();
            _.each(bundleURLs, url => {
                $newLinks = $newLinks.add($('<link/>', {
                    type: 'text/css',
                    rel: 'stylesheet',
                    href: url,
                }));
            });

            const linksLoaded = new Promise(resolve => {
                let nbLoaded = 0;
                $newLinks.on('load error', () => { // If we have an error, just ignore it
                    if (++nbLoaded >= $newLinks.length) {
                        resolve();
                    }
                });
            });
            $links.last().after($newLinks);
            return linksLoaded;
        });
        await Promise.all(proms).then(() => $allLinks.remove());
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

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onUserValueUpdate: async function (ev) {
        const _super = this._super.bind(this);

        // First check if the updated widget or any of the widgets it will
        // trigger uses the 'customizeWebsite' method. If so, check if any one of
        // them will require a reload. If it is the case, warns the user and ask
        // if he agrees to save its current changes. If not, just do nothing.
        // If yes, save the current changes and continue.
        let requiresReload = false;
        if (!ev.data.previewMode && !ev.data.isSimulatedEvent) {
            const linkedWidgets = this._requestUserValueWidgets(...ev.data.triggerWidgetsNames);
            const widgets = [ev.data.widget].concat(linkedWidgets);

            for (const widget of widgets) {
                const methodsNames = widget.getMethodsNames();
                if (!methodsNames.includes('customizeWebsite')) {
                    continue;
                }
                const params = widget.getMethodsParams('customizeWebsite');
                if (params.reload || config.isDebug('assets')) {
                    requiresReload = true;
                    break;
                }
            }
            if (requiresReload) {
                const save = await new Promise(resolve => {
                    Dialog.confirm(this, _t("This change needs to reload the page, this will save all your changes and reload the page, are you sure you want to proceed?") +
                        (config.isDebug('assets') ? _t(" It appears you are in debug=assets mode, all theme customization options require a page reload in this mode.") : ''), {
                        confirm_callback: () => resolve(true),
                        cancel_callback: () => resolve(false),
                    });
                });
                if (!save) {
                    return;
                }
            }
        }

        await _super(...arguments);

        if (requiresReload) {
            this.trigger_up('request_save', {
                reloadEditor: true,
            });
        }
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onGoogleFontsCustoRequest: function (ev) {
        const values = ev.data.values ? _.clone(ev.data.values) : {};
        const googleFonts = ev.data.googleFonts;
        if (googleFonts.length) {
            values['google-fonts'] = "('" + googleFonts.join("', '") + "')";
        } else {
            values['google-fonts'] = 'null';
        }
        this.trigger_up('snippet_edition_request', {exec: async () => {
            return this._makeSCSSCusto('/website/static/src/scss/options/user_values.scss', values);
        }});
        this.trigger_up('request_save', {
            reloadEditor: true,
        });
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

options.registry.Theme = options.Class.extend({

    /**
     * @override
     */
    start: async function () {
        // The normal configuration of Odoo is to have two colors named 'alpha'
        // and 'beta' which generate their own BS CSS classes but which are also
        // used as 'primary' and 'secondary' BS values (to customize standard BS
        // used in Odoo). However, some themes are still going against that
        // system and do not link alpha-primary and beta-secondary at all.
        this._alphaEqualsPrimary = (this._getCSSColorFromName('primary') === this._getCSSColorFromName('alpha'));
        this._betaEqualsSecondary = (this._getCSSColorFromName('secondary') === this._getCSSColorFromName('beta'));
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @todo use scss customization instead (like for user colors)
     * @see this.selectClass for parameters
     */
    customizeBodyBg: async function (previewMode, widgetValue, params) {
        const xmlID = 'website.option_custom_body_image';
        if (widgetValue) {
            await this._rpc({
                model: 'ir.model.data',
                method: 'get_object_reference',
                args: xmlID.split('.'),
            }).then(data => {
                return this._rpc({
                    model: 'ir.ui.view',
                    method: 'save',
                    args: [
                        data[1],
                        `#wrapwrap { background-image: url("${widgetValue}"); }`,
                        '//style',
                    ],
                });
            });
        } else {
            await this._customizeWebsiteViews('', {possibleValues: ['', xmlID]});
        }

        await this._reloadBundles();
    },
    /**
     * @see this.selectClass for parameters
     */
    switchTheme: async function (previewMode, widgetValue, params) {
        const save = await new Promise(resolve => {
            Dialog.confirm(this, _t("Changing theme requires to leave the editor. This will save all your changes, are you sure you want to proceed?"), {
                confirm_callback: () => resolve(true),
                cancel_callback: () => resolve(false),
            });
        });
        if (!save) {
            return;
        }
        this.trigger_up('request_save', {
            reload: false,
            onSuccess: () => window.location.href = '/web#action=website.theme_install_kanban_action',
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: async function (methodName, params) {
        if (methodName === 'customizeBodyBg') {
            const bgURL = $('#wrapwrap').css('background-image');
            const srcValueWrapper = /url\(['"]*|['"]*\)|^none$/g;
            return bgURL && bgURL.replace(srcValueWrapper, '') || '';
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _computeWidgetVisibility: async function (widgetName, params) {
        if (widgetName === 'theme_color_suggestions') {
            return false;
        }
        if (widgetName === 'primary_color_opt' || widgetName === 'alpha_as_extra_color_opt') {
            return !this._alphaEqualsPrimary;
        }
        if (widgetName === 'secondary_color_opt' || widgetName === 'beta_as_extra_color_opt') {
            return !this._betaEqualsSecondary;
        }
        if (widgetName === 'alpha_as_primary_color_opt') {
            return this._alphaEqualsPrimary;
        }
        if (widgetName === 'beta_as_secondary_color_opt') {
            return this._betaEqualsSecondary;
        }
        return this._super(...arguments);
    },
});

options.registry.menu_data = options.Class.extend({
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
            return '' + (this.colsLength || this.$target.children().length);
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

        var colsLength = this.$target.children().length + count;
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

        this._resizeColumns(colsLength);
        this.trigger_up('cover_update');
    },
    /**
     * Resizes the columns so that they are kept on one row.
     *
     * @private
     * @param {number} [colsLength] (default to the actual number of columns)
     */
    _resizeColumns: function (colsLength) {
        var $columns = this.$target.children();
        colsLength = colsLength || $columns.length;
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
        // TODO: remove in master. This is used to keep the UI in sync, but
        // won't be needed once option methods are properly asynchronous.
        this.colsLength = colsLength;
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

options.registry.CookiesBar = options.registry.SnippetPopup.extend({
    xmlDependencies: (options.registry.SnippetPopup.prototype.xmlDependencies || []).concat(
        ['/website/static/src/xml/website.cookies_bar.xml']
    ),

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Change the cookies bar layout.
     *
     * @see this.selectClass for parameters
     */
    selectLayout: function (previewMode, widgetValue, params) {
        let websiteId;
        this.trigger_up('context_get', {
            callback: function (ctx) {
                websiteId = ctx['website_id'];
            },
        });

        const $template = $(qweb.render(`website.cookies_bar.${widgetValue}`, {
            websiteId: websiteId,
        }));

        const $content = this.$target.find('.s_popup_content');
        const selectorsToKeep = [
            '.o_cookies_bar_text_button',
            '.o_cookies_bar_text_policy',
            '.o_cookies_bar_text_title',
            '.o_cookies_bar_text_primary',
            '.o_cookies_bar_text_secondary',
        ];

        if (this.$savedSelectors === undefined) {
            this.$savedSelectors = [];
        }

        for (const selector of selectorsToKeep) {
            const $currentLayoutEls = $content.find(selector).contents();
            const $newLayoutEl = $template.find(selector);
            if ($currentLayoutEls.length) {
                // save value before change, eg 'title' is not inside 'discrete' template
                // but we want to preserve it in case of select another layout later
                this.$savedSelectors[selector] = $currentLayoutEls;
            }
            const $savedSelector = this.$savedSelectors[selector];
            if ($newLayoutEl.length && $savedSelector && $savedSelector.length) {
                $newLayoutEl.empty().append($savedSelector);
            }
        }

        $content.empty().append($template);
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
        this.$filter.toggleClass('oe_black', parseFloat(widgetValue) !== 0);
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
        this.$target[0].dataset.textAlignClass = this.$el.find('[data-cover-opt-name="text_align"] we-button.active').data('selectClass') || '';
        this.$target[0].dataset.filterValue = this.$filterValueOpts.filter('.active').data('filterValue') || 0.0;
        let colorPickerWidget = null;
        this.trigger_up('user_value_widget_request', {
            name: 'bg_color_opt',
            onSuccess: _widget => colorPickerWidget = _widget,
        });
        const color = colorPickerWidget._value;
        const isCSSColor = ColorpickerDialog.isCSSColor(color);
        this.$target[0].dataset.bgColorClass = isCSSColor ? '' : 'bg-' + color;
        this.$target[0].dataset.bgColorStyle = isCSSColor ? `background-color:${color};` : '';
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

return {
    UrlPickerUserValueWidget: UrlPickerUserValueWidget,
    FontFamilyPickerUserValueWidget: FontFamilyPickerUserValueWidget,
};
});
