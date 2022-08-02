/* globals google*/
odoo.define('website.editor.snippets.options', function (require) {
'use strict';

const {ColorpickerWidget} = require('web.Colorpicker');
var core = require('web.core');
var Dialog = require('web.Dialog');
const {Markup, sprintf} = require('web.utils');
const weUtils = require('web_editor.utils');
var options = require('web_editor.snippets.options');
const wLinkPopoverWidget = require('@website/js/widgets/link_popover_widget')[Symbol.for("default")];
const wUtils = require('website.utils');
const {isImageSupportedForStyle} = require('web_editor.image_processing');
require('website.s_popup_options');

var _t = core._t;
var qweb = core.qweb;

const InputUserValueWidget = options.userValueWidgetsRegistry['we-input'];
const SelectUserValueWidget = options.userValueWidgetsRegistry['we-select'];

options.UserValueWidget.include({
    loadMethodsData() {
        this._super(...arguments);

        // Method names are sorted alphabetically by default. Exception here:
        // we make sure, customizeWebsiteVariable is considered after
        // customizeWebsiteViews so that the variable is used to show to active
        // value when both methods are used at the same time.
        // TODO find a better way.
        const indexVariable = this._methodsNames.indexOf('customizeWebsiteVariable');
        if (indexVariable >= 0) {
            const indexView = this._methodsNames.indexOf('customizeWebsiteViews');
            if (indexView >= 0) {
                this._methodsNames[indexVariable] = 'customizeWebsiteViews';
                this._methodsNames[indexView] = 'customizeWebsiteVariable';
            }
        }
    },
});

const UrlPickerUserValueWidget = InputUserValueWidget.extend({
    custom_events: _.extend({}, InputUserValueWidget.prototype.custom_events || {}, {
        'website_url_chosen': '_onWebsiteURLChosen',
    }),
    events: _.extend({}, InputUserValueWidget.prototype.events || {}, {
        'click .o_we_redirect_to': '_onRedirectTo',
    }),

    /**
     * @override
     */
    start: async function () {
        await this._super(...arguments);
        const linkButton = document.createElement('we-button');
        const icon = document.createElement('i');
        icon.classList.add('fa', 'fa-fw', 'fa-external-link')
        linkButton.classList.add('o_we_redirect_to');
        linkButton.title = _t("Redirect to URL in a new tab");
        linkButton.appendChild(icon);
        this.containerEl.appendChild(linkButton);
        this.el.classList.add('o_we_large');
        this.inputEl.classList.add('text-start');
        const options = {
            position: {
                collision: 'flip fit',
            },
            classes: {
                "ui-autocomplete": 'o_website_ui_autocomplete'
            },
            body: this.getParent().$target[0].ownerDocument.body,
        };
        wUtils.autocompleteWithPages(this, $(this.inputEl), options);
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
        this._value = this.inputEl.value;
        this._onUserValueChange(ev);
    },
    /**
     * Redirects to the URL the widget currently holds.
     *
     * @private
     */
    _onRedirectTo: function () {
        if (this._value) {
            window.open(this._value, '_blank');
        }
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
        const style = window.getComputedStyle(this.$target[0].ownerDocument.documentElement);
        const nbFonts = parseInt(weUtils.getCSSVariableValue('number-of-fonts', style));
        const googleFontsProperty = weUtils.getCSSVariableValue('google-fonts', style);
        this.googleFonts = googleFontsProperty ? googleFontsProperty.split(/\s*,\s*/g) : [];
        this.googleFonts = this.googleFonts.map(font => font.substring(1, font.length - 1)); // Unquote

        await this._super(...arguments);

        const fontEls = [];
        const methodName = this.el.dataset.methodName || 'customizeWebsiteVariable';
        const variable = this.el.dataset.variable;
        _.times(nbFonts, fontNb => {
            const realFontNb = fontNb + 1;
            const fontEl = document.createElement('we-button');
            fontEl.classList.add(`o_we_option_font_${realFontNb}`);
            fontEl.dataset.variable = variable;
            fontEl.dataset[methodName] = weUtils.getCSSVariableValue(`font-number-${realFontNb}`, style);
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
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async setValue() {
        await this._super(...arguments);

        for (const className of this.menuTogglerEl.classList) {
            if (className.match(/^o_we_option_font_\d+$/)) {
                this.menuTogglerEl.classList.remove(className);
            }
        }
        const activeWidget = this._userValueWidgets.find(widget => !widget.isPreviewed() && widget.isActive());
        if (activeWidget) {
            this.menuTogglerEl.classList.add(`o_we_option_font_${activeWidget.el.dataset.font}`);
        }
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
                    click: async () => {
                        const inputEl = dialog.el.querySelector('.o_input_google_font');
                        // if font page link (what is expected)
                        let m = inputEl.value.match(/\bspecimen\/([\w+]+)/);
                        if (!m) {
                            // if embed code (so that it works anyway if the user put the embed code instead of the page link)
                            m = inputEl.value.match(/\bfamily=([\w+]+)/);
                            if (!m) {
                                inputEl.classList.add('is-invalid');
                                return;
                            }
                        }

                        let isValidFamily = false;

                        try {
                            const result = await fetch("https://fonts.googleapis.com/css?family=" + m[1]+':300,300i,400,400i,700,700i', {method: 'HEAD'});
                            // Google fonts server returns a 400 status code if family is not valid.
                            if (result.ok) {
                                isValidFamily = true;
                            }
                        } catch (error) {
                            console.error(error);
                        }

                        if (!isValidFamily) {
                            inputEl.classList.add('is-invalid');
                            return;
                        }

                        const font = m[1].replace(/\+/g, ' ');
                        this.googleFonts.push(font);
                        this.trigger_up('google_fonts_custo_request', {
                            values: {[variable]: `'${font}'`},
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

        // Remove Google font
        const googleFontIndex = parseInt(ev.target.dataset.fontIndex);
        const googleFont = this.googleFonts[googleFontIndex];
        this.googleFonts.splice(googleFontIndex, 1);

        // Adapt font variable indexes to the removal
        const values = {};
        const style = window.getComputedStyle(document.documentElement);
        _.each(FontFamilyPickerUserValueWidget.prototype.fontVariables, variable => {
            const value = weUtils.getCSSVariableValue(variable, style);
            if (value.substring(1, value.length - 1) === googleFont) {
                // If an element is using the google font being removed, reset
                // it to the theme default.
                values[variable] = 'null';
            }
        });

        this.trigger_up('google_fonts_custo_request', {
            values: values,
            googleFonts: this.googleFonts,
        });
    },
});

const GPSPicker = InputUserValueWidget.extend({
    events: { // Explicitely not consider all InputUserValueWidget events
        'blur input': '_onInputBlur',
    },

    /**
     * @constructor
     */
    init() {
        this._super(...arguments);
        this._gmapCacheGPSToPlace = {};
    },
    /**
     * @override
     */
    async willStart() {
        await this._super(...arguments);
        this._gmapLoaded = await new Promise(resolve => {
            this.trigger_up('gmap_api_request', {
                editableMode: true,
                configureIfNecessary: true,
                onSuccess: key => resolve(!!key),
            });
        });
        if (!this._gmapLoaded) {
            this.trigger_up('user_value_widget_critical');
            return;
        }
    },
    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this.el.classList.add('o_we_large');
        if (!this._gmapLoaded) {
            return;
        }

        this._gmapAutocomplete = new google.maps.places.Autocomplete(this.inputEl, {types: ['geocode']});
        google.maps.event.addListener(this._gmapAutocomplete, 'place_changed', this._onPlaceChanged.bind(this));
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getMethodsParams: function (methodName) {
        return Object.assign({gmapPlace: this._gmapPlace || {}}, this._super(...arguments));
    },
    /**
     * @override
     */
    async setValue() {
        await this._super(...arguments);

        await new Promise(resolve => {
            const gps = this._value;
            if (this._gmapCacheGPSToPlace[gps]) {
                this._gmapPlace = this._gmapCacheGPSToPlace[gps];
                resolve();
                return;
            }
            const service = new google.maps.places.PlacesService(document.createElement('div'));
            const p = gps.substring(1).slice(0, -1).split(',');
            const location = new google.maps.LatLng(p[0] || 0, p[1] || 0);
            service.nearbySearch({
                // Do a 'nearbySearch' followed by 'getDetails' to avoid using
                // GMap Geocoder which the user may not have enabled... but
                // ideally Geocoder should be used to get the exact location at
                // those coordinates and to limit billing query count.
                location: location,
                radius: 1,
            }, (results, status) => {
                const GMAP_CRITICAL_ERRORS = [google.maps.places.PlacesServiceStatus.REQUEST_DENIED, google.maps.places.PlacesServiceStatus.UNKNOWN_ERROR];
                if (status === google.maps.places.PlacesServiceStatus.OK) {
                    service.getDetails({
                        placeId: results[0].place_id,
                        fields: ['geometry', 'formatted_address'],
                    }, (place, status) => {
                        resolve();
                        if (status === google.maps.places.PlacesServiceStatus.OK) {
                            this._gmapCacheGPSToPlace[gps] = place;
                            this._gmapPlace = place;
                        } else if (GMAP_CRITICAL_ERRORS.includes(status)) {
                            this.trigger_up('user_value_widget_critical');
                        }
                    });
                } else if (GMAP_CRITICAL_ERRORS.includes(status)) {
                    resolve();
                    this.trigger_up('user_value_widget_critical');
                }
            });
        });
        if (this._gmapPlace) {
            this.inputEl.value = this._gmapPlace.formatted_address;
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onPlaceChanged(ev) {
        const gmapPlace = this._gmapAutocomplete.getPlace();
        if (gmapPlace && gmapPlace.geometry) {
            this._gmapPlace = gmapPlace;
            const location = this._gmapPlace.geometry.location;
            this._value = `(${location.lat()},${location.lng()})`;
            this._gmapCacheGPSToPlace[this._value] = gmapPlace;
            this._onUserValueChange(ev);
        }
    },
});
options.userValueWidgetsRegistry['we-urlpicker'] = UrlPickerUserValueWidget;
options.userValueWidgetsRegistry['we-fontfamilypicker'] = FontFamilyPickerUserValueWidget;
options.userValueWidgetsRegistry['we-gpspicker'] = GPSPicker;

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

options.Class.include({
    xmlDependencies: (options.Class.prototype.xmlDependencies || [])
        .concat(['/website/static/src/xml/website.editor.xml']),
    custom_events: _.extend({}, options.Class.prototype.custom_events || {}, {
        'google_fonts_custo_request': '_onGoogleFontsCustoRequest',
    }),
    specialCheckAndReloadMethodsNames: ['customizeWebsiteViews', 'customizeWebsiteVariable', 'customizeWebsiteColor'],

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    customizeWebsiteViews: async function (previewMode, widgetValue, params) {
        await this._customizeWebsite(previewMode, widgetValue, params, 'views');
    },
    /**
     * @see this.selectClass for parameters
     */
    customizeWebsiteVariable: async function (previewMode, widgetValue, params) {
        await this._customizeWebsite(previewMode, widgetValue, params, 'variable');
    },
    /**
     * @see this.selectClass for parameters
     */
    customizeWebsiteColor: async function (previewMode, widgetValue, params) {
        await this._customizeWebsite(previewMode, widgetValue, params, 'color');
    },
    /**
     * @see this.selectClass for parameters
     */
    async customizeWebsiteAssets(previewMode, widgetValue, params) {
        await this._customizeWebsite(previewMode, widgetValue, params, 'assets');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _checkIfWidgetsUpdateNeedReload(widgets) {
        const needReload = await this._super(...arguments);
        if (needReload) {
            return needReload;
        }
        for (const widget of widgets) {
            const methodsNames = widget.getMethodsNames();
            const specialMethodsNames = [];
            // If it's a pageOption, it's most likely to need to reload, so check the widgets.
            if (this.data.pageOptions) {
                specialMethodsNames.push(methodsNames);
            } else {
                for (const methodName of methodsNames) {
                    if (this.specialCheckAndReloadMethodsNames.includes(methodName)) {
                        specialMethodsNames.push(methodName);
                    }
                }
            }
            if (!specialMethodsNames.length) {
                continue;
            }
            let paramsReload = false;
            for (const methodName of specialMethodsNames) {
                if (widget.getMethodsParams(methodName).reload) {
                    paramsReload = true;
                    break;
                }
            }
            if (paramsReload) {
                return true;
            }
        }
        return false;
    },
    /**
     * @override
     */
    _computeWidgetState: async function (methodName, params) {
        switch (methodName) {
            case 'customizeWebsiteViews': {
                return this._getEnabledCustomizeValues(params.possibleValues, true);
            }
            case 'customizeWebsiteVariable': {
                const ownerDocument = this.$target[0].ownerDocument;
                const style = ownerDocument.defaultView.getComputedStyle(ownerDocument.documentElement);
                return weUtils.getCSSVariableValue(params.variable, style);
            }
            case 'customizeWebsiteColor': {
                const ownerDocument = this.$target[0].ownerDocument;
                const style = ownerDocument.defaultView.getComputedStyle(ownerDocument.documentElement);
                return weUtils.getCSSVariableValue(params.color, style);
            }
            case 'customizeWebsiteAssets': {
                return this._getEnabledCustomizeValues(params.possibleValues, false);
            }
        }
        return this._super(...arguments);
    },
    /**
     * @private
     */
    _customizeWebsite: async function (previewMode, widgetValue, params, type) {
        // Never allow previews for theme customizations
        if (previewMode) {
            return;
        }

        switch (type) {
            case 'views':
                await this._customizeWebsiteData(widgetValue, params, true);
                break;
            case 'variable':
                await this._customizeWebsiteVariable(widgetValue, params);
                break;
            case 'color':
                await this._customizeWebsiteColor(widgetValue, params);
                break;
            case 'assets':
                await this._customizeWebsiteData(widgetValue, params, false);
                break;
            default:
                if (params.customCustomization) {
                    await params.customCustomization.call(this, widgetValue, params);
                }
        }

        if (params.reload || params.noBundleReload) {
            // Caller will reload the page, nothing needs to be done anymore.
            return;
        }

        // Finally, only update the bundles as no reload is required
        await this._reloadBundles();
        // Any option that require to reload bundle should probably
        // also update the color preview of the theme tabs, as
        // bundles can affect the look of the previews.
        this.trigger_up('option_update', {
            optionName: 'ThemeColors',
            name: 'update_color_previews',
        });

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
    /**
     * @private
     */
    async _customizeWebsiteColor(color, params) {
        await this._customizeWebsiteColors({[params.color]: color}, params);
    },
    /**
     * @private
     */
     async _customizeWebsiteColors(colors, params) {
        colors = colors || {};

        const baseURL = '/website/static/src/scss/options/colors/';
        const colorType = params.colorType ? (params.colorType + '_') : '';
        const url = `${baseURL}user_${colorType}color_palette.scss`;

        const finalColors = {};
        for (const [colorName, color] of Object.entries(colors)) {
            finalColors[colorName] = color;
            if (color) {
                if (weUtils.isColorCombinationName(color)) {
                    finalColors[colorName] = parseInt(color);
                } else if (!ColorpickerWidget.isCSSColor(color)) {
                    finalColors[colorName] = `'${color}'`;
                }
            }
        }
        return this._makeSCSSCusto(url, finalColors, params.nullValue);
    },
    /**
     * @private
     */
    _customizeWebsiteVariable: async function (value, params) {
        return this._makeSCSSCusto('/website/static/src/scss/options/user_values.scss', {
            [params.variable]: value,
        }, params.nullValue);
    },
    /**
     * @private
     */
    async _customizeWebsiteData(value, params, isViewData) {
        const allDataKeys = this._getDataKeysFromPossibleValues(params.possibleValues);
        const enableDataKeys = value.split(/\s*,\s*/);
        const disableDataKeys = allDataKeys.filter(value => !enableDataKeys.includes(value));
        const resetViewArch = !!params.resetViewArch;

        return this._rpc({
            route: '/website/theme_customize_data',
            params: {
                'is_view_data': isViewData,
                'enable': enableDataKeys,
                'disable': disableDataKeys,
                'reset_view_arch': resetViewArch,
            },
        });
    },
    /**
     * @private
     */
    _getDataKeysFromPossibleValues(possibleValues) {
        const allDataKeys = [];
        for (const dataKeysStr of possibleValues) {
            allDataKeys.push(...dataKeysStr.split(/\s*,\s*/));
        }
        return allDataKeys.filter((v, i, arr) => arr.indexOf(v) === i);
    },
    /**
     * @private
     * @param {Array} possibleValues
     * @param {Boolean} isViewData true = "ir.ui.view", false = "ir.asset"
     * @returns {String}
     */
    async _getEnabledCustomizeValues(possibleValues, isViewData) {
        const allDataKeys = this._getDataKeysFromPossibleValues(possibleValues);
        const enabledValues = await this._rpc({
            route: '/website/theme_customize_data_get',
            params: {
                'keys': allDataKeys,
                'is_view_data': isViewData,
            },
        });
        let mostValuesStr = '';
        let mostValuesNb = 0;
        for (const valuesStr of possibleValues) {
            const enableValues = valuesStr.split(/\s*,\s*/);
            if (enableValues.length > mostValuesNb
                    && enableValues.every(value => enabledValues.includes(value))) {
                mostValuesStr = valuesStr;
                mostValuesNb = enableValues.length;
            }
        }
        return mostValuesStr; // Need to return the exact same string as in possibleValues
    },
    /**
     * @private
     */
    _makeSCSSCusto: async function (url, values, defaultValue = 'null') {
        return this._rpc({
            model: 'web_editor.assets',
            method: 'make_scss_customization',
            args: [url, _.mapObject(values, v => v || defaultValue)],
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
    _reloadBundles: async function() {
        return new Promise((resolve, reject) => {
            this.trigger_up('reload_bundles', {
                onSuccess: () => resolve(),
                onFailure: () => reject(),
            });
        });
    },
    /**
     * @override
     */
    _select: async function (previewMode, widget) {
        await this._super(...arguments);

        if (this.options.isWebsite && !widget.$el.closest('[data-no-widget-refresh="true"]').length) {
            // TODO the flag should be retrieved through widget params somehow
            await this._refreshPublicWidgets();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

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

function _getLastPreFilterLayerElement($el) {
    // Make sure parallax and video element are considered to be below the
    // color filters / shape
    const $bgVideo = $el.find('> .o_bg_video_container');
    if ($bgVideo.length) {
        return $bgVideo[0];
    }
    const $parallaxEl = $el.find('> .s_parallax_bg');
    if ($parallaxEl.length) {
        return $parallaxEl[0];
    }
    return null;
}

options.registry.BackgroundToggler.include({
    /**
     * Toggles background video on or off.
     *
     * @see this.selectClass for parameters
     */
    toggleBgVideo(previewMode, widgetValue, params) {
        if (!widgetValue) {
            this.$target.find('> .o_we_bg_filter').remove();
            // TODO: use setWidgetValue instead of calling background directly when possible
            const [bgVideoWidget] = this._requestUserValueWidgets('bg_video_opt');
            const bgVideoOpt = bgVideoWidget.getParent();
            return bgVideoOpt._setBgVideo(false, '');
        } else {
            // TODO: use trigger instead of el.click when possible
            this._requestUserValueWidgets('bg_video_opt')[0].el.click();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === 'toggleBgVideo') {
            return this.$target[0].classList.contains('o_background_video');
        }
        return this._super(...arguments);
    },
    /**
     * TODO an overall better management of background layers is needed
     *
     * @override
     */
    _getLastPreFilterLayerElement() {
        const el = _getLastPreFilterLayerElement(this.$target);
        if (el) {
            return el;
        }
        return this._super(...arguments);
    },
});

options.registry.BackgroundShape.include({
    /**
     * TODO need a better management of background layers
     *
     * @override
     */
    _getLastPreShapeLayerElement() {
        const el = this._super(...arguments);
        if (el) {
            return el;
        }
        return _getLastPreFilterLayerElement(this.$target);
    }
});

options.registry.ReplaceMedia.include({
    /**
     * Adds an anchor to the url.
     * Here "anchor" means a specific section of a page.
     *
     * @see this.selectClass for parameters
     */
    setAnchor(previewMode, widgetValue, params) {
        const linkEl = this.$target[0].parentElement;
        let url = linkEl.getAttribute('href');
        url = url.split('#')[0];
        linkEl.setAttribute('href', url + widgetValue);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === 'setAnchor') {
            const parentEl = this.$target[0].parentElement;
            if (parentEl.tagName === 'A') {
                const href = parentEl.getAttribute('href') || '';
                return href ? `#${href.split('#')[1]}` : '';
            }
            return '';
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'media_link_anchor_opt') {
            const parentEl = this.$target[0].parentElement;
            const linkEl = parentEl.tagName === 'A' ? parentEl : null;
            const href = linkEl ? linkEl.getAttribute('href') : false;
            return href && href.startsWith('/');
        }
        return this._super(...arguments);
    },
    /**
     * Fills the dropdown with the available anchors for the page referenced in
     * the href.
     *
     * @override
     */
    async _renderCustomXML(uiFragment) {
        if (!this.options.isWebsite) {
            return this._super(...arguments);
        }
        await this._super(...arguments);



        const oldURLWidgetEl = uiFragment.querySelector('[data-name="media_url_opt"]');

        const URLWidgetEl = document.createElement('we-urlpicker');
        // Copy attributes
        for (const {name, value} of oldURLWidgetEl.attributes) {
            URLWidgetEl.setAttribute(name, value);
        }
        URLWidgetEl.title = _t("Hint: Type '/' to search an existing page and '#' to link to an anchor.");
        oldURLWidgetEl.replaceWith(URLWidgetEl);

        const hrefValue = this.$target[0].parentElement.getAttribute('href');
        if (!hrefValue || !hrefValue.startsWith('/')) {
            return;
        }
        const urlWithoutAnchor = hrefValue.split('#')[0];
        const selectEl = document.createElement('we-select');
        selectEl.dataset.name = 'media_link_anchor_opt';
        selectEl.dataset.dependencies = 'media_url_opt';
        selectEl.dataset.noPreview = 'true';
        selectEl.classList.add('o_we_sublevel_1');
        selectEl.setAttribute('string', _t("Page Anchor"));
        const anchors = await wUtils.loadAnchors(urlWithoutAnchor);
        for (const anchor of anchors) {
            const weButtonEl = document.createElement('we-button');
            weButtonEl.dataset.setAnchor = anchor;
            weButtonEl.textContent = anchor;
            selectEl.append(weButtonEl);
        }
        URLWidgetEl.after(selectEl);
    },
});

options.registry.BackgroundVideo = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Sets the target's background video.
     *
     * @see this.selectClass for parameters
     */
    background: function (previewMode, widgetValue, params) {
        if (previewMode === 'reset' && this.videoSrc) {
            return this._setBgVideo(false, this.videoSrc);
        }
        return this._setBgVideo(previewMode, widgetValue);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        if (methodName === 'background') {
            if (this.$target[0].classList.contains('o_background_video')) {
                return this.$('> .o_bg_video_container iframe').attr('src');
            }
            return '';
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
});

options.registry.OptionsTab = options.Class.extend({
    GRAY_PARAMS: {EXTRA_SATURATION: "gray-extra-saturation", HUE: "gray-hue"},

    /**
     * @override
     */
    init() {
        this._super(...arguments);
        this.grayParams = {};
        this.grays = {};
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async updateUI() {
        // The bg-XXX classes have been updated (and could be updated by another
        // option like changing color palette) -> update the preview element.
        const ownerDocument = this.$target[0].ownerDocument;
        const style = ownerDocument.defaultView.getComputedStyle(ownerDocument.documentElement);
        const grayPreviewEls = this.$el.find(".o_we_gray_preview span");
        for (const e of grayPreviewEls) {
            const bgValue = weUtils.getCSSVariableValue(e.getAttribute('variable'), style);
            e.style.setProperty("background-color", bgValue, "important");
        }

        // If the gray palette has been generated by Odoo standard option,
        // the hue of all gray is the same and the saturation has been
        // increased/decreased by the same amount for all grays in
        // comparaison with BS grays. However the system supports any
        // gray palette.

        const hues = [];
        const saturationDiffs = [];
        let oneHasNoSaturation = false;
        for (let id = 100; id <= 900; id += 100) {
            const gray = weUtils.getCSSVariableValue(`${id}`, style);
            const grayRGB = ColorpickerWidget.convertCSSColorToRgba(gray);
            const grayHSL = ColorpickerWidget.convertRgbToHsl(grayRGB.red, grayRGB.green, grayRGB.blue);

            const baseGray = weUtils.getCSSVariableValue(`base-${id}`, style);
            const baseGrayRGB = ColorpickerWidget.convertCSSColorToRgba(baseGray);
            const baseGrayHSL = ColorpickerWidget.convertRgbToHsl(baseGrayRGB.red, baseGrayRGB.green, baseGrayRGB.blue);

            if (grayHSL.saturation > 0.01) {
                if (grayHSL.lightness > 0.01 && grayHSL.lightness < 99.99) {
                    hues.push(grayHSL.hue);
                }
                if (grayHSL.saturation < 99.99) {
                    saturationDiffs.push(grayHSL.saturation - baseGrayHSL.saturation);
                }
            } else {
                oneHasNoSaturation = true;
            }
        }
        this.grayHueIsDefined = !!hues.length;

        // Average of angles: we need to take the average of found hues
        // because even if grays are supposed to be set to the exact
        // same hue by the Odoo editor, there might be rounding errors
        // during the conversion from RGB to HSL as the HSL system
        // allows to represent more colors that the RGB hexadecimal
        // notation (also: hue 360 = hue 0 and should not be averaged to 180).
        // This also better support random gray palettes.
        this.grayParams[this.GRAY_PARAMS.HUE] = (!hues.length) ? 0 : Math.round((Math.atan2(
            hues.map(hue => Math.sin(hue * Math.PI / 180)).reduce((memo, value) => memo + value, 0) / hues.length,
            hues.map(hue => Math.cos(hue * Math.PI / 180)).reduce((memo, value) => memo + value, 0) / hues.length
        ) * 180 / Math.PI) + 360) % 360;

        // Average of found saturation diffs, or all grays have no
        // saturation, or all grays are fully saturated.
        this.grayParams[this.GRAY_PARAMS.EXTRA_SATURATION] = saturationDiffs.length
            ? saturationDiffs.reduce((memo, value) => memo + value, 0) / saturationDiffs.length
            : (oneHasNoSaturation ? -100 : 100);

        await this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async customizeGray(previewMode, widgetValue, params) {
        // Gray parameters are used *on the JS side* to compute the grays that
        // will be saved in the database. We indeed need those grays to be
        // computed here for faster previews so this allows to not duplicate
        // most of the logic. Also, this gives flexibility to maybe allow full
        // customization of grays in custo and themes. Also, this allows to ease
        // migration if the computation here was to change: the user grays would
        // still be unchanged as saved in the database.

        this.grayParams[params.param] = parseInt(widgetValue);
        for (let i = 1; i < 10; i++) {
            const key = (100 * i).toString();
            this.grays[key] = this._buildGray(key);
        }

        // Preview UI update
        this.$el.find(".o_we_gray_preview").each((_, e) => {
            e.style.setProperty("background-color", this.grays[e.getAttribute('variable')], "important");
        });

        // Save all computed (JS side) grays in database
        await this._customizeWebsite(previewMode, undefined, Object.assign({}, params, {
            customCustomization: () => { // TODO this could be prettier
                return this._customizeWebsiteColors(this.grays, Object.assign({}, params, {
                    colorType: 'gray',
                }));
            },
        }));
    },
    /**
     * @see this.selectClass for parameters
     */
    async configureApiKey(previewMode, widgetValue, params) {
        return new Promise(resolve => {
            this.trigger_up('gmap_api_key_request', {
                editableMode: true,
                reconfigure: true,
                onSuccess: () => resolve(),
            });
        });
    },
    /**
     * @see this.selectClass for parameters
     */
    async customizeBodyBgType(previewMode, widgetValue, params) {
        if (widgetValue === 'NONE') {
            this.bodyImageType = 'image';
            return this.customizeBodyBg(previewMode, '', params);
        }
        // TODO improve: hack to click on external image picker
        this.bodyImageType = widgetValue;
        const widget = this._requestUserValueWidgets(params.imagepicker)[0];
        widget.enable();
    },
    /**
     * @override
     */
    async customizeBodyBg(previewMode, widgetValue, params) {
        // TODO improve: customize two variables at the same time...
        await this.customizeWebsiteVariable(previewMode, this.bodyImageType, {variable: 'body-image-type'});
        await this.customizeWebsiteVariable(previewMode, widgetValue ? `'${widgetValue}'` : '', {variable: 'body-image'});
    },
    /**
     * @see this.selectClass for parameters
     */
    async openCustomCodeDialog(previewMode, widgetValue, params) {
        const libsProm = this._loadLibs({
            jsLibs: [
                '/web/static/lib/ace/ace.js',
                '/web/static/lib/ace/mode-xml.js',
                '/web/static/lib/ace/mode-qweb.js',
            ],
        });

        let websiteId;
        this.trigger_up('context_get', {
            callback: (ctx) => {
                websiteId = ctx['website_id'];
            },
        });

        let website;
        const dataProm = this._rpc({
            model: 'website',
            method: 'read',
            args: [[websiteId], ['custom_code_head', 'custom_code_footer']],
        }).then(websites => {
            website = websites[0];
        });

        let fieldName, title, contentText;
        if (widgetValue === 'head') {
            fieldName = 'custom_code_head';
            title = _t('Custom head code');
            contentText = _t('Enter code that will be added into the <head> of every page of your site.');
        } else {
            fieldName = 'custom_code_footer';
            title = _t('Custom end of body code');
            contentText = _t('Enter code that will be added before the </body> of every page of your site.');
        }

        await Promise.all([libsProm, dataProm]);

        await new Promise(resolve => {
            const $content = $(core.qweb.render('website.custom_code_dialog_content', {
                contentText,
            }));
            const aceEditor = this._renderAceEditor($content.find('.o_ace_editor_container')[0], website[fieldName] || '');
            const dialog = new Dialog(this, {
                title,
                $content,
                buttons: [
                    {
                        text: _t("Save"),
                        classes: 'btn-primary',
                        click: async () => {
                            await this._rpc({
                                model: 'website',
                                method: 'write',
                                args: [
                                    [websiteId],
                                    {[fieldName]: aceEditor.getValue()},
                                ],
                            });
                        },
                        close: true,
                    },
                    {
                        text: _t("Discard"),
                        close: true,
                    },
                ],
            });
            dialog.on('closed', this, resolve);
            dialog.open();
        });
    },
    /**
     * @see this.selectClass for parameters
     */
    async switchTheme(previewMode, widgetValue, params) {
        const save = await new Promise(resolve => {
            Dialog.confirm(this, _t("Changing theme requires to leave the editor. This will save all your changes, are you sure you want to proceed? Be careful that changing the theme will reset all your color customizations."), {
                confirm_callback: () => resolve(true),
                cancel_callback: () => resolve(false),
            });
        });
        if (!save) {
            return;
        }
        this.trigger_up('request_save', {
            reload: false,
            action: 'website.theme_install_kanban_action',
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {String} id
     * @returns {String} the adjusted color of gray
     */
    _buildGray(id) {
        const ownerDocument = this.$target[0].ownerDocument;
        const gray = weUtils.getCSSVariableValue(`base-${id}`, ownerDocument.defaultView.getComputedStyle(ownerDocument.documentElement));
        const grayRGB = ColorpickerWidget.convertCSSColorToRgba(gray);
        const hsl = ColorpickerWidget.convertRgbToHsl(grayRGB.red, grayRGB.green, grayRGB.blue);
        const adjustedGrayRGB = ColorpickerWidget.convertHslToRgb(this.grayParams[this.GRAY_PARAMS.HUE],
            Math.min(Math.max(hsl.saturation + this.grayParams[this.GRAY_PARAMS.EXTRA_SATURATION], 0), 100),
            hsl.lightness);
        return ColorpickerWidget.convertRgbaToCSSColor(adjustedGrayRGB.red, adjustedGrayRGB.green, adjustedGrayRGB.blue);
    },
    /**
     * @override
     */
    async _renderCustomXML(uiFragment) {
        await this._super(...arguments);
        const extraSaturationRangeEl = uiFragment.querySelector(`we-range[data-param=${this.GRAY_PARAMS.EXTRA_SATURATION}]`);
        if (extraSaturationRangeEl) {
            const baseGrays = _.range(100, 1000, 100).map(id => {
                const gray = weUtils.getCSSVariableValue(`base-${id}`);
                const grayRGB = ColorpickerWidget.convertCSSColorToRgba(gray);
                const hsl = ColorpickerWidget.convertRgbToHsl(grayRGB.red, grayRGB.green, grayRGB.blue);
                return {id: id, hsl: hsl};
            });
            const first = baseGrays[0];
            const maxValue = baseGrays.reduce((gray, value) => {
                return gray.hsl.saturation > value.hsl.saturation ? gray : value;
            }, first);
            const minValue = baseGrays.reduce((gray, value) => {
                return gray.hsl.saturation < value.hsl.saturation ? gray : value;
            }, first);
            extraSaturationRangeEl.dataset.max = 100 - minValue.hsl.saturation;
            extraSaturationRangeEl.dataset.min = -maxValue.hsl.saturation;
        }
        uiFragment.querySelectorAll('we-colorpicker').forEach(el => {
            el.dataset.lazyPalette = 'true';
        });
    },
    /**
     * @override
     */
    async _checkIfWidgetsUpdateNeedWarning(widgets) {
        const warningMessage = await this._super(...arguments);
        if (warningMessage) {
            return warningMessage;
        }
        for (const widget of widgets) {
            if (widget.getMethodsNames().includes('customizeWebsiteVariable')
                    && widget.getMethodsParams('customizeWebsiteVariable').variable === 'color-palettes-name') {
                const hasCustomizedColors = weUtils.getCSSVariableValue('has-customized-colors');
                if (hasCustomizedColors && hasCustomizedColors !== 'false') {
                    return _t("Changing the color palette will reset all your color customizations, are you sure you want to proceed?");
                }
            }
        }
        return '';
    },
    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName === 'customizeBodyBgType') {
            const bgImage = $('#wrapwrap').css('background-image');
            if (bgImage === 'none') {
                return "NONE";
            }
            return weUtils.getCSSVariableValue('body-image-type');
        }
        if (methodName === 'customizeGray') {
            // See updateUI override
            return this.grayParams[params.param];
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'body_bg_image_opt') {
            return false;
        }
        if (params.param === this.GRAY_PARAMS.HUE) {
            return this.grayHueIsDefined;
        }
        return this._super(...arguments);
    },
    /**
     * @private
     * @param {DOMElement} node
     * @param {String} content text of the editor
     * @returns {Object}
     */
    _renderAceEditor(node, content) {
        const aceEditor = window.ace.edit(node);
        aceEditor.setTheme('ace/theme/monokai');
        aceEditor.setValue(content, 1);
        aceEditor.setOptions({
            minLines: 20,
            maxLines: Infinity,
            showPrintMargin: false,
        });
        aceEditor.renderer.setOptions({
            highlightGutterLine: true,
            showInvisibles: true,
            fontSize: 14,
        });

        const aceSession = aceEditor.getSession();
        aceSession.setOptions({
            mode: "ace/mode/qweb",
            useWorker: false,
        });
        return aceEditor;
    },
});

options.registry.ThemeColors = options.registry.OptionsTab.extend({
    /**
     * @override
     */
    async start() {
        // Checks for support of the old color system
        const style = window.getComputedStyle(document.documentElement);
        const supportOldColorSystem = weUtils.getCSSVariableValue('support-13-0-color-system', style) === 'true';
        const hasCustomizedOldColorSystem = weUtils.getCSSVariableValue('has-customized-13-0-color-system', style) === 'true';
        this._showOldColorSystemWarning = supportOldColorSystem && hasCustomizedOldColorSystem;

        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    notify(name, data) {
        if (name === 'update_color_previews') {
            this.updateColorPreviews = true;
        }
    },
    /**
     * @override
     */
    async updateUIVisibility() {
        await this._super(...arguments);
        const oldColorSystemEl = this.el.querySelector('.o_old_color_system_warning');
        oldColorSystemEl.classList.toggle('d-none', !this._showOldColorSystemWarning);
    },
    /**
     * @override
     */
    async updateUI() {
        if (this.updateColorPreviews) {
            const ccPreviewEls = this.el.querySelectorAll('.o_we_cc_preview_wrapper');
            this.trigger_up('update_color_previews', {
                ccPreviewEls,
            });
            this.updateColorPreviews = false;
        }
        await this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _select() {
        this.updateColorPreviews = true;
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async _renderCustomXML(uiFragment) {
        const paletteSelectorEl = uiFragment.querySelector('[data-variable="color-palettes-name"]');
        const style = window.getComputedStyle(document.documentElement);
        const allPaletteNames = weUtils.getCSSVariableValue('palette-names', style).split(', ').map((name) => {
            return name.replace(/'/g, "");
        });
        for (const paletteName of allPaletteNames) {
            const btnEl = document.createElement('we-button');
            btnEl.classList.add('o_palette_color_preview_button');
            btnEl.dataset.customizeWebsiteVariable = `'${paletteName}'`;
            [1, 3, 2].forEach(c => {
                const colorPreviewEl = document.createElement('span');
                colorPreviewEl.classList.add('o_palette_color_preview');
                const color = weUtils.getCSSVariableValue(`o-palette-${paletteName}-o-color-${c}`, style);
                colorPreviewEl.style.backgroundColor = color;
                btnEl.appendChild(colorPreviewEl);
            });
            paletteSelectorEl.appendChild(btnEl);
        }

        const presetCollapseEl = uiFragment.querySelector('we-collapse.o_we_theme_presets_collapse');
        let ccPreviewEls = [];
        for (let i = 1; i <= 5; i++) {
            const collapseEl = document.createElement('we-collapse');
            const ccPreviewEl = $(qweb.render('web_editor.color.combination.preview'))[0];
            ccPreviewEl.classList.add('text-center', `o_cc${i}`, 'o_colored_level', 'o_we_collapse_toggler');
            collapseEl.appendChild(ccPreviewEl);
            const editionEls = $(qweb.render('website.color_combination_edition', {number: i}));
            for (const el of editionEls) {
                collapseEl.appendChild(el);
            }
            ccPreviewEls.push(ccPreviewEl);
            presetCollapseEl.appendChild(collapseEl);
        }
        this.trigger_up('update_color_previews', {
            ccPreviewEls,
        });
        await this._super(...arguments);
    },
});

options.registry.menu_data = options.Class.extend({
    /**
     * When the users selects a menu, a popover is shown with 4 possible
     * actions: follow the link in a new tab, copy the menu link, edit the menu,
     * or edit the menu tree.
     * The popover shows a preview of the menu link. Remote URL only show the
     * favicon.
     *
     * @override
     */
    start: function () {
        const wysiwyg = $(this.ownerDocument.getElementById('wrapwrap')).data('wysiwyg');
        wLinkPopoverWidget.createFor(this, this.$target[0], { wysiwyg });
        return this._super(...arguments);
    },
    /**
      * When the users selects another element on the page, makes sure the
      * popover is closed.
      *
      * @override
      */
    onBlur: function () {
        this.$target.popover('hide');
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
    /**
     * @override
     */
    notify: function (name, data) {
        this._super(...arguments);
        if (name === 'add_slide') {
            this._addSlide();
        }
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    addSlide(previewMode, widgetValue, params) {
        this._addSlide();
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
        this.$target.find('[data-bs-target]').attr('data-bs-target', '#' + id);
        _.each(this.$target.find('[data-bs-slide], [data-bs-slide-to]'), function (el) {
            var $el = $(el);
            if ($el.attr('data-bs-target')) {
                $el.attr('data-bs-target', '#' + id);
            } else if ($el.attr('href')) {
                $el.attr('href', '#' + id);
            }
        });
    },
    /**
     * Adds a slide.
     *
     * @private
     */
    _addSlide() {
        const $items = this.$target.find('.carousel-item');
        this.$controls.removeClass('d-none');
        const $active = $items.filter('.active');
        this.$indicators.append($('<li>', {
            'data-bs-target': '#' + this.$target.attr('id'),
            'data-bs-slide-to': $items.length,
        }));
        this.$indicators.append(' ');
        // Need to remove editor data from the clone so it gets its own.
        $active.clone(false)
            .removeClass('active')
            .insertAfter($active);
        this.$target.carousel('next');
    },
});

options.registry.CarouselItem = options.Class.extend({
    isTopOption: true,
    forceNoDeleteButton: true,

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
     * @see this.selectClass for parameters
     */
    addSlideItem(previewMode, widgetValue, params) {
        this.trigger_up('option_update', {
            optionName: 'Carousel',
            name: 'add_slide',
        });
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

options.registry.Parallax = options.Class.extend({
    /**
     * @override
     */
    async start() {
        this.parallaxEl = this.$target.find('> .s_parallax_bg')[0] || null;
        this._updateBackgroundOptions();

        this.$target.on('content_changed.ParallaxOption', this._onExternalUpdate.bind(this));

        return this._super(...arguments);
    },
    /**
     * @override
     */
    onFocus() {
        // Refresh the parallax animation on focus; at least useful because
        // there may have been changes in the page that influenced the parallax
        // rendering (new snippets, ...).
        // TODO make this automatic.
        if (this.parallaxEl) {
            this._refreshPublicWidgets();
        }
    },
    /**
     * @override
     */
    onMove() {
        this._refreshPublicWidgets();
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        this.$target.off('.ParallaxOption');
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Build/remove parallax.
     *
     * @see this.selectClass for parameters
     */
    async selectDataAttribute(previewMode, widgetValue, params) {
        await this._super(...arguments);
        if (params.attributeName !== 'scrollBackgroundRatio') {
            return;
        }

        const isParallax = (widgetValue !== '0');
        this.$target.toggleClass('parallax', isParallax);
        this.$target.toggleClass('s_parallax_is_fixed', widgetValue === '1');
        this.$target.toggleClass('s_parallax_no_overflow_hidden', (widgetValue === '0' || widgetValue === '1'));
        if (isParallax) {
            if (!this.parallaxEl) {
                this.parallaxEl = document.createElement('span');
                this.parallaxEl.classList.add('s_parallax_bg');
                this.$target.prepend(this.parallaxEl);
            }
        } else {
            if (this.parallaxEl) {
                this.parallaxEl.remove();
                this.parallaxEl = null;
            }
        }

        this._updateBackgroundOptions();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeVisibility(widgetName) {
        return !this.$target.hasClass('o_background_video');
    },
    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName === 'selectDataAttribute' && params.parallaxTypeOpt) {
            const attrName = params.attributeName;
            const attrValue = (this.$target[0].dataset[attrName] || params.attributeDefaultValue).trim();
            switch (attrValue) {
                case '0':
                case '1': {
                    return attrValue;
                }
                default: {
                    return (attrValue.startsWith('-') ? '-1.5' : '1.5');
                }
            }
        }
        return this._super(...arguments);
    },
    /**
     * Updates external background-related option to work with the parallax
     * element instead of the original target when necessary.
     *
     * @private
     */
    _updateBackgroundOptions() {
        this.trigger_up('option_update', {
            optionNames: ['BackgroundImage', 'BackgroundPosition', 'BackgroundOptimize'],
            name: 'target',
            data: this.parallaxEl ? $(this.parallaxEl) : this.$target,
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called on any snippet update to check if the parallax should still be
     * enabled or not.
     *
     * TODO there is probably a better system to implement to solve this issue.
     *
     * @private
     * @param {Event} ev
     */
    _onExternalUpdate(ev) {
        if (!this.parallaxEl) {
            return;
        }
        const bgImage = this.parallaxEl.style.backgroundImage;
        if (!bgImage || bgImage === 'none' || this.$target.hasClass('o_background_video')) {
            // The parallax option was enabled but the background image was
            // removed: disable the parallax option.
            const widget = this._requestUserValueWidgets('parallax_none_opt')[0];
            widget.enable();
            widget.getParent().close(); // FIXME remove this ugly hack asap
        }
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
            self.$target.trigger('content_changed');
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
        let time = new Date().getTime();
        const $tablist = this.$target.closest('[role="tablist"]');
        const $tab = this.$target.find('[role="tab"]');
        const $panel = this.$target.find('[role="tabpanel"]');

        const setUniqueId = ($elem, label) => {
            let elemId = $elem.attr('id');
            if (!elemId || $('[id="' + elemId + '"]').length > 1) {
                do {
                    time++;
                    elemId = label + time;
                } while ($('#' + elemId).length);
                $elem.attr('id', elemId);
            }
            return elemId;
        };

        const tablistId = setUniqueId($tablist, 'myCollapse');
        $panel.attr('data-bs-parent', '#' + tablistId);
        $panel.data('bs-parent', '#' + tablistId);

        const panelId = setUniqueId($panel, 'myCollapseTab');
        $tab.attr('data-bs-target', '#' + panelId);
        $tab.data('bs-target', '#' + panelId);
    },
});

options.registry.WebsiteLevelColor = options.Class.extend({
    specialCheckAndReloadMethodsNames: options.Class.prototype.specialCheckAndReloadMethodsNames
        .concat(['customizeWebsiteLayer2Color']),

    /**
     * @see this.selectClass for parameters
     */
    async customizeWebsiteLayer2Color(previewMode, widgetValue, params) {
        if (previewMode) {
            return;
        }
        params.color = params.layerColor;
        params.variable = params.layerGradient;
        let color = undefined;
        let gradient = undefined;
        if (weUtils.isColorGradient(widgetValue)) {
            color = '';
            gradient = widgetValue;
        } else {
            color = widgetValue;
            gradient = '';
        }
        await this.customizeWebsiteVariable(previewMode, gradient, params);
        params.noBundleReload = false;
        return this.customizeWebsiteColor(previewMode, color, params);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName === 'customizeWebsiteLayer2Color') {
            params.variable = params.layerGradient;
            const gradient = await this._computeWidgetState('customizeWebsiteVariable', params);
            if (gradient) {
                return gradient.substring(1, gradient.length - 1); // Unquote
            }
            params.color = params.layerColor;
            return this._computeWidgetState('customizeWebsiteColor', params);
        }
        return this._super(...arguments);
    },
});

options.registry.HeaderLayout = options.registry.WebsiteLevelColor.extend({
    /**
     * @overide
     */
    async customizeWebsiteViews(previewMode, widgetValue, params) {
        const _super = this._super.bind(this);

        if (params.name === 'header_sidebar_opt') {
            // When the user selects sidebar as header, make sure that the
            // header position is regular.
            await new Promise(resolve => {
                this.trigger_up('action_demand', {
                    actionName: 'toggle_page_option',
                    params: [{name: 'header_overlay', value: false}],
                    onSuccess: () => resolve(),
                });
            });
        }

        return _super(...arguments);
    }
});

options.registry.HeaderNavbar = options.Class.extend({
    /**
     * Particular case: we want the option to be associated on the header navbar
     * in XML so that the related options only appear on navbar click (not
     * header), in a different section, etc... but we still want the target to
     * be the header itself.
     *
     * @constructor
     */
    init() {
        this._super(...arguments);
        this.setTarget(this.$target.closest('#wrapwrap > header'));
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async updateUIVisibility() {
        await this._super(...arguments);

        // TODO improve this: this is a big hack so that the "no mobile
        // hamburger" option is disabled if it is ever hidden (because of the
        // selection of an hamburger template which is a foreign option). This
        // should be done another way in another place somehow...
        const noHamburgerWidget = this.findWidget('no_hamburger_opt');
        const noHamburgerHidden = noHamburgerWidget.$el.hasClass('d-none');
        if (noHamburgerHidden && noHamburgerWidget.isActive()) {
            this.findWidget('default_hamburger_opt').enable();
        }

        // TODO improve this: this is a big hack so that the label of the
        // hamburger option changes if the 'no_hamburger_opt' one is available
        // (= in that case the option controls only the *mobile* hamburger).
        const hamburgerTypeWidget = this.findWidget('header_hamburger_type_opt');
        const labelEl = hamburgerTypeWidget.el.querySelector('we-title');
        if (!this._originalHamburgerTypeLabel) {
            this._originalHamburgerTypeLabel = labelEl.textContent;
        }
        labelEl.textContent = noHamburgerHidden
            ? this._originalHamburgerTypeLabel
            : _t("Mobile menu");
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Needs to be done manually for now because data-dependencies
     * doesn't work with "AND" conditions.
     * TODO: improve this.
     *
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        switch (widgetName) {
            case 'option_logo_height_scrolled': {
                return !this.$('.navbar-brand').hasClass('d-none');
            }
            case 'no_hamburger_opt': {
                return !weUtils.getCSSVariableValue('header-template').includes('hamburger');
            }
        }
        return this._super(...arguments);
    },
});

const VisibilityPageOptionUpdate = options.Class.extend({
    pageOptionName: undefined,
    showOptionWidgetName: undefined,
    shownValue: '',

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        const shown = await this._isShown();
        this.trigger_up('snippet_option_visibility_update', {show: shown});
    },
    /**
     * @override
     */
    async onTargetShow() {
        if (await this._isShown()) {
            // onTargetShow may be called even if the element is already shown.
            // In most cases, this is not a problem but here it is as the code
            // that follows clicks on the visibility checkbox regardless of its
            // status. This avoids searching for that checkbox entirely.
            return;
        }
        // TODO improve: here we make a hack so that if we make the invisible
        // header appear for edition, its actual visibility for the page is
        // toggled (otherwise it would be about editing an element which
        // is actually never displayed on the page).
        const widget = this._requestUserValueWidgets(this.showOptionWidgetName)[0];
        widget.enable();
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for params
     */
    async visibility(previewMode, widgetValue, params) {
        const show = (widgetValue !== 'hidden');
        await new Promise((resolve, reject) => {
            this.trigger_up('action_demand', {
                actionName: 'toggle_page_option',
                params: [{name: this.pageOptionName, value: show}],
                onSuccess: () => resolve(),
                onFailure: reject,
            });
        });
        this.trigger_up('snippet_option_visibility_update', {show: show});
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName === 'visibility') {
            const shown = await this._isShown();
            return shown ? this.shownValue : 'hidden';
        }
        return this._super(...arguments);
    },
    /**
     * @private
     * @returns {boolean}
     */
    async _isShown() {
        return new Promise((resolve, reject) => {
            this.trigger_up('action_demand', {
                actionName: 'get_page_option',
                params: [this.pageOptionName],
                onSuccess: v => resolve(!!v),
                onFailure: reject,
            });
        });
    },
});

options.registry.TopMenuVisibility = VisibilityPageOptionUpdate.extend({
    pageOptionName: 'header_visible',
    showOptionWidgetName: 'regular_header_visibility_opt',

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Handles the switching between 3 differents visibilities of the header.
     *
     * @see this.selectClass for params
     */
    async visibility(previewMode, widgetValue, params) {
        await this._super(...arguments);
        await this._changeVisibility(widgetValue);
        // TODO this is hacky but changing the header visibility may have an
        // effect on features like FullScreenHeight which depend on viewport
        // size so we simulate a resize.
        const targetWindow = this.$target[0].ownerDocument.defaultView;
        targetWindow.dispatchEvent(new targetWindow.Event('resize'));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _changeVisibility(widgetValue) {
        const show = (widgetValue !== 'hidden');
        if (!show) {
            return;
        }
        const transparent = (widgetValue === 'transparent');
        await new Promise((resolve, reject) => {
            this.trigger_up('action_demand', {
                actionName: 'toggle_page_option',
                params: [{name: 'header_overlay', value: transparent}],
                onSuccess: () => resolve(),
                onFailure: reject,
            });
        });
        if (!transparent) {
            return;
        }
        await new Promise((resolve, reject) => {
            this.trigger_up('action_demand', {
                actionName: 'toggle_page_option',
                params: [{name: 'header_color', value: ''}],
                onSuccess: () => resolve(),
                onFailure: reject,
            });
        });
    },
    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        const _super = this._super.bind(this);
        if (methodName === 'visibility') {
            this.shownValue = await new Promise((resolve, reject) => {
                this.trigger_up('action_demand', {
                    actionName: 'get_page_option',
                    params: ['header_overlay'],
                    onSuccess: v => resolve(v ? 'transparent' : 'regular'),
                    onFailure: reject,
                });
            });
        }
        return _super(...arguments);
    },
});

options.registry.topMenuColor = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async selectStyle(previewMode, widgetValue, params) {
        await this._super(...arguments);
        const className = widgetValue ? (params.colorPrefix + widgetValue) : '';
        await new Promise((resolve, reject) => {
            this.trigger_up('action_demand', {
                actionName: 'toggle_page_option',
                params: [{name: 'header_color', value: className}],
                onSuccess: resolve,
                onFailure: reject,
            });
        });
    },

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
        return new Promise((resolve, reject) => {
            this.trigger_up('action_demand', {
                actionName: 'get_page_option',
                params: ['header_overlay'],
                onSuccess: value => resolve(!!value),
                onFailure: reject,
            });
        });
    },
});

/**
 * Manage the visibility of snippets on mobile.
 */
options.registry.MobileVisibility = options.Class.extend({
    isTopOption: true,

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async updateUI() {
        await this._super(...arguments);
        const $button = this.$el.find('we-button');
        $button.attr('title', $button.hasClass('active') ? _t("Visible on mobile") : _t("Hidden on mobile"));
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Allows to show or hide the associated snippet in mobile display mode.
     *
     * @see this.selectClass for parameters
     */
    showOnMobile(previewMode, widgetValue, params) {
        const classes = `d-none d-md-${this.$target.css('display')}`;
        this.$target.toggleClass(classes, !widgetValue);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName === 'showOnMobile') {
            const classList = [...this.$target[0].classList];
            return classList.includes('d-none') &&
                classList.some(className => className.startsWith('d-md-')) ? '' : 'true';
        }
        return await this._super(...arguments);
    },
});

/**
 * Hide/show footer in the current page.
 */
options.registry.HideFooter = VisibilityPageOptionUpdate.extend({
    pageOptionName: 'footer_visible',
    showOptionWidgetName: 'hide_footer_page_opt',
    shownValue: 'shown',
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
            const message = sprintf(Markup(_t("Anchor copied to clipboard<br>Link: %s")), anchor);
            this.displayNotification({
              type: 'success',
              message: message,
              buttons: [{text: _t("Edit"), click: () => this.openAnchorDialog(), primary: true}],
            });
        });

        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    onClone: function () {
        this.$target.removeAttr('data-anchor');
        this.$target.filter(':not(.carousel)').removeAttr('id');
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
                classes: 'btn-link ms-auto',
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
        return `${window.location.pathname}#${this.$target[0].id}`;
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

options.registry.HeaderBox = options.registry.Box.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async selectStyle(previewMode, widgetValue, params) {
        if ((params.variable || params.color)
                && ['border-width', 'border-style', 'border-color', 'border-radius', 'box-shadow'].includes(params.cssProperty)) {
            if (previewMode) {
                return;
            }
            if (params.cssProperty === 'border-color') {
                return this.customizeWebsiteColor(previewMode, widgetValue, params);
            }
            return this.customizeWebsiteVariable(previewMode, widgetValue, params);
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async setShadow(previewMode, widgetValue, params) {
        if (params.variable) {
            if (previewMode) {
                return;
            }
            const defaultShadow = this._getDefaultShadow(widgetValue, params.shadowClass);
            return this.customizeWebsiteVariable(previewMode, defaultShadow, params);
        }
        return this._super(...arguments);
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

        const $content = this.$target.find('.modal-content');
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
    /**
     * @override
     */
    onTargetShow: async function () {
        // @see this.onTargetHide
        this.$target.parent('#website_cookies_bar').show();
        this._super(...arguments);

    },
    /**
     * @override
     */
    onTargetHide: async function () {
        // We hide the parent because contenteditable="true" would force the bar to stay visible in hidden mode.
        this.$target.parent('#website_cookies_bar').hide();
        this._super(...arguments);
    },
    /**
     * @override
     */
    cleanForSave: function () {
        this.$target.parent('#website_cookies_bar').show();
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
            this.$target.addClass('o_record_has_cover');
            const $defaultSizeBtn = this.$el.find('.o_record_cover_opt_size_default');
            $defaultSizeBtn.click();
            $defaultSizeBtn.closest('we-select').click();
        }

        if (!previewMode) {
            this._updateSavingDataset();
        }
    },
    /**
     * @see this.selectClass for parameters
     */
    filterValue: function (previewMode, widgetValue, params) {
        this.$filter.css('opacity', widgetValue || 0);
        this.$filter.toggleClass('oe_black', parseFloat(widgetValue) !== 0);

        if (!previewMode) {
            this._updateSavingDataset();
        }
    },
    /**
     * @override
     */
    selectStyle: async function (previewMode, widgetValue, params) {
        await this._super(...arguments);

        if (!previewMode) {
            this._updateSavingDataset(widgetValue);
        }
    },
    /**
     * @override
     */
    selectClass: async function (previewMode, widgetValue, params) {
        await this._super(...arguments);

        if (!previewMode) {
            this._updateSavingDataset();
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
        if (params.coverOptName) {
            return this.$target.data(`use_${params.coverOptName}`) === 'True';
        }
        return this._super(...arguments);
    },
    /**
     * @private
     */
    _updateColorDataset(bgColorStyle = '', bgColorClass = '') {
        this.$target[0].dataset.bgColorStyle = bgColorStyle;
        this.$target[0].dataset.bgColorClass = bgColorClass;
    },
    /**
     * Updates the cover properties dataset used for saving.
     *
     * @private
     */
    _updateSavingDataset(colorValue) {
        const [colorPickerWidget, sizeWidget, textAlignWidget] = this._requestUserValueWidgets('bg_color_opt', 'size_opt', 'text_align_opt');
        // TODO: `o_record_has_cover` should be handled using model field, not
        // resize_class to avoid all of this.
        // Get values from DOM (selected values in options are only available
        // after updateUI)
        const sizeOptValues = sizeWidget.getMethodsParams('selectClass').possibleValues;
        let coverClass = [...this.$target[0].classList].filter(
            value => sizeOptValues.includes(value)
        ).join(' ');
        const bg = this.$image.css('background-image');
        if (bg && bg !== 'none') {
            coverClass += " o_record_has_cover";
        }
        const textAlignOptValues = textAlignWidget.getMethodsParams('selectClass').possibleValues;
        const textAlignClass = [...this.$target[0].classList].filter(
            value => textAlignOptValues.includes(value)
        ).join(' ');
        const filterEl = this.$target[0].querySelector('.o_record_cover_filter');
        const filterValue = filterEl && filterEl.style.opacity;
        // Update saving dataset
        this.$target[0].dataset.coverClass = coverClass;
        this.$target[0].dataset.textAlignClass = textAlignClass;
        this.$target[0].dataset.filterValue = filterValue || 0.0;
        // TODO there is probably a better way and this should be refactored to
        // use more standard colorpicker+imagepicker structure
        const ccValue = colorPickerWidget._ccValue;
        const colorOrGradient = colorPickerWidget._value;
        const isGradient = weUtils.isColorGradient(colorOrGradient);
        const isCSSColor = !isGradient && ColorpickerWidget.isCSSColor(colorOrGradient);
        const colorNames = [];
        if (ccValue) {
            colorNames.push(ccValue);
        }
        if (colorOrGradient && !isGradient && !isCSSColor) {
            colorNames.push(colorOrGradient);
        }
        const bgColorClass = weUtils.computeColorClasses(colorNames).join(' ');
        const bgColorStyle = isCSSColor ? `background-color: ${colorOrGradient};` :
            isGradient ? `background-color: rgba(0, 0, 0, 0); background-image: ${colorOrGradient};` : '';
        this._updateColorDataset(bgColorStyle, bgColorClass);
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

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    async showScrollButton(previewMode, widgetValue, params) {
        if (widgetValue) {
            this.$button.show();
        } else {
            if (previewMode) {
                this.$button.hide();
            } else {
                this.$button.detach();
            }
        }
    },
    /**
     * Toggles the scroll down button.
     */
    toggleButton: function (previewMode, widgetValue, params) {
        if (widgetValue) {
            if (!this.$button.length) {
                const anchor = document.createElement('a');
                anchor.classList.add(
                    'o_scroll_button',
                    'mb-3',
                    'rounded-circle',
                    'align-items-center',
                    'justify-content-center',
                    'mx-auto',
                    'bg-primary',
                    'o_not_editable',
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
});

options.registry.ConditionalVisibility = options.Class.extend({
    /**
     * @constructor
     */
    init() {
        this._super(...arguments);
        this.optionsAttributes = [];
    },
    /**
     * @override
     */
    async start() {
        await this._super(...arguments);

        for (const widget of this._userValueWidgets) {
            const params = widget.getMethodsParams();
            if (params.saveAttribute) {
                this.optionsAttributes.push({
                    saveAttribute: params.saveAttribute,
                    attributeName: params.attributeName,
                    // If callWith dataAttribute is not specified, the default
                    // field to check on the record will be .value for values
                    // coming from another widget than M2M.
                    callWith: params.callWith || 'value',
                });
            }
        }
    },
    /**
     * @override
     */
    async onTargetHide() {
        this.$target[0].classList.add('o_conditional_hidden');
    },
    /**
     * @override
     */
    async onTargetShow() {
        this.$target[0].classList.remove('o_conditional_hidden');
    },
    /**
     * @override
     */
    cleanForSave() {
        // Kinda hacky: the snippet is forced hidden via onTargetHide on save
        // but should be marked as visible as when entering edit mode later, the
        // snippet will be shown naturally (as the CSS rules won't apply).
        // Without this, the "eye" icon of the visibility panel would be shut
        // when entering edit mode.
        this.trigger_up('snippet_option_visibility_update', { show: true });
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Inserts or deletes record's id and value in target's data-attributes
     * if no ids are selected, deletes the attribute.
     *
     * @see this.selectClass for parameters
     */
    selectRecord(previewMode, widgetValue, params) {
        const recordsData = JSON.parse(widgetValue);
        if (recordsData.length) {
            this.$target[0].dataset[params.saveAttribute] = widgetValue;
        } else {
            delete this.$target[0].dataset[params.saveAttribute];
        }

        this._updateCSSSelectors();
    },
    /**
     * Selects a value for target's data-attributes.
     * Should be used instead of selectRecord if the visibility is not related
     * to database values.
     *
     * @see this.selectClass for parameters
     */
    selectValue(previewMode, widgetValue, params) {
        if (widgetValue) {
            const widgetValueIndex = params.possibleValues.indexOf(widgetValue);
            const value = [{value: widgetValue, id: widgetValueIndex}];
            this.$target[0].dataset[params.saveAttribute] = JSON.stringify(value);
        } else {
            delete this.$target[0].dataset[params.saveAttribute];
        }

        this._updateCSSSelectors();
    },
    /**
     * Opens the toggler when 'conditional' is selected.
     *
     * @override
     */
    async selectDataAttribute(previewMode, widgetValue, params) {
        await this._super(...arguments);

        if (params.attributeName === 'visibility') {
            const targetEl = this.$target[0];
            if (widgetValue === 'conditional') {
                const collapseEl = this.$el.children('we-collapse')[0];
                this._toggleCollapseEl(collapseEl);
            } else {
                // TODO create a param to allow doing this automatically for genericSelectDataAttribute?
                delete targetEl.dataset.visibility;

                for (const attribute of this.optionsAttributes) {
                    delete targetEl.dataset[attribute.saveAttribute];
                    delete targetEl.dataset[`${attribute.saveAttribute}Rule`];
                }
            }
            this.trigger_up('snippet_option_visibility_update', {show: true});
        } else if (!params.isVisibilityCondition) {
            return;
        }

        this._updateCSSSelectors();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName === 'selectRecord') {
            return this.$target[0].dataset[params.saveAttribute] || '[]';
        }
        if (methodName === 'selectValue') {
            const selectedValue = this.$target[0].dataset[params.saveAttribute];
            return selectedValue ? JSON.parse(selectedValue)[0].value : params.attributeDefaultValue;
        }
        return this._super(...arguments);
    },
    /**
     * Reads target's attributes and creates CSS selectors.
     * Stores them in data-attributes to then be reapplied by
     * content/inject_dom.js (ideally we should saved them in a <style> tag
     * directly but that would require a new website.page field and would not
     * be possible in dynamic (controller) pages... maybe some day).
     *
     * @private
     */
    _updateCSSSelectors() {
        // There are 2 data attributes per option:
        // - One that stores the current records selected
        // - Another that stores the value of the rule "Hide for / Visible for"
        const visibilityIDParts = [];
        const onlyAttributes = [];
        const hideAttributes = [];
        const target = this.$target[0];
        for (const attribute of this.optionsAttributes) {
            if (target.dataset[attribute.saveAttribute]) {
                let records = JSON.parse(target.dataset[attribute.saveAttribute]).map(record => {
                    return { id: record.id, value: record[attribute.callWith] };
                });
                if (attribute.saveAttribute === 'visibilityValueLang') {
                    records = records.map(lang => {
                        lang.value = lang.value.replace(/_/g, '-');
                        return lang;
                    });
                }
                const hideFor = target.dataset[`${attribute.saveAttribute}Rule`] === 'hide';
                if (hideFor) {
                    hideAttributes.push({ name: attribute.attributeName, records: records});
                } else {
                    onlyAttributes.push({ name: attribute.attributeName, records: records});
                }
                // Create a visibilityId based on the options name and their
                // values. eg : hide for en_US(id:1) -> lang1h
                const type = attribute.attributeName.replace('data-', '');
                const valueIDs = records.map(record => record.id).sort();
                visibilityIDParts.push(`${type}_${hideFor ? 'h' : 'o'}_${valueIDs.join('_')}`);
            }
        }
        const visibilityId = visibilityIDParts.join('_');
        // Creates CSS selectors based on those attributes, the reducers
        // combine the attributes' values.
        let selectors = '';
        for (const attribute of onlyAttributes) {
            // e.g of selector:
            // html:not([data-attr-1="valueAttr1"]):not([data-attr-1="valueAttr2"]) [data-visibility-id="ruleId"]
            const selector = attribute.records.reduce((acc, record) => {
                return acc += `:not([${attribute.name}="${record.value}"])`;
            }, 'html') + ` body:not(.editor_enable) [data-visibility-id="${visibilityId}"]`;
            selectors += selector + ', ';
        }
        for (const attribute of hideAttributes) {
            // html[data-attr-1="valueAttr1"] [data-visibility-id="ruleId"],
            // html[data-attr-1="valueAttr2"] [data-visibility-id="ruleId"]
            const selector = attribute.records.reduce((acc, record, i, a) => {
                acc += `html[${attribute.name}="${record.value}"] body:not(.editor_enable) [data-visibility-id="${visibilityId}"]`;
                return acc + (i !== a.length - 1 ? ',' : '');
            }, '');
            selectors += selector + ', ';
        }
        selectors = selectors.slice(0, -2);
        if (selectors) {
            this.$target[0].dataset.visibilitySelectors = selectors;
        } else {
            delete this.$target[0].dataset.visibilitySelectors;
        }

        if (visibilityId) {
            this.$target[0].dataset.visibilityId = visibilityId;
        } else {
            delete this.$target[0].dataset.visibilityId;
        }
    },
});

options.registry.WebsiteAnimate = options.Class.extend({
    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this.isAnimatedText = this.$target.hasClass('o_animated_text');
        this.$optionsSection = this.$overlay.data('$optionsSection');
    },
    /**
     * @override
     */
    async onBuilt() {
        this.$target[0].classList.toggle('o_animate_preview', this.$target[0].classList.contains('o_animate'));
    },
    /**
     * @override
     */
    onFocus() {
        if (this.isAnimatedText) {
            // For animated text, the animation options must be in the editor
            // toolbar.
            const $toolbar = this.options.wysiwyg.toolbar.$el;
            $toolbar.append(this.$el);
            this.$optionsSection.addClass('d-none');
        }
    },
    /**
     * @override
     */
    onBlur() {
        if (this.isAnimatedText) {
            // For animated text, the options must be returned to their
            // original location as they were moved in the toolbar.
            this.$optionsSection.append(this.$el);
        }
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async selectClass(previewMode, widgetValue, params) {
        await this._super(...arguments);
        if (params.isAnimationTypeSelection) {
            this._forceAnimation();
            this.$target.toggleClass('o_animate_preview o_animate', !!widgetValue);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _forceAnimation() {
        const $scrollingElement = $().getScrollingElement();
        this.$target.css('animation-name', 'dummy');
        // Trigger a DOM reflow.
        void this.$target[0].offsetWidth;
        this.$target.addClass('o_animating');
        $scrollingElement[0].classList.add('o_wanim_overflow_xy_hidden');
        this.$target.css('animation-name', '');
        this.$target.one('webkitAnimationEnd oanimationend msAnimationEnd animationend', () => {
            $scrollingElement[0].classList.remove('o_wanim_overflow_xy_hidden');
            this.$target.removeClass('o_animating');
        });
    },
    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'no_animation_opt') {
            return !this.isAnimatedText;
        }
        if (widgetName === 'animation_launch_opt') {
            return !this.$target[0].closest('.dropdown');
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _computeVisibility(methodName, params) {
        if (this.$target[0].matches('img')) {
            return isImageSupportedForStyle(this.$target[0]);
        }
        return this._super(...arguments);
    },
});

/**
 * Replaces current target with the specified template layout
 */
options.registry.MegaMenuLayout = options.registry.SelectTemplate.extend({
    /**
     * @override
     */
    init() {
        this._super(...arguments);
        this.selectTemplateWidgetName = 'mega_menu_template_opt';
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    notify(name, data) {
        if (name === 'reset_template') {
            const xmlid = this._getCurrentTemplateXMLID();
            this._getTemplate(xmlid).then(template => {
                this.containerEl.insertAdjacentHTML('beforeend', template);
                data.onSuccess();
            });
        } else {
            this._super(...arguments);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        if (methodName === 'selectTemplate') {
            return this._getCurrentTemplateXMLID();
        }
        return this._super(...arguments);
    },
    /**
     * @private
     * @returns {string} xmlid of the current template.
     */
    _getCurrentTemplateXMLID: function () {
        const templateDefiningClass = this.containerEl.querySelector('section')
            .classList.value.split(' ').filter(cl => cl.startsWith('s_mega_menu'))[0];
        return `website.${templateDefiningClass}`;
    },
});

/**
 * Hides delete button for Mega Menu block.
 */
options.registry.MegaMenuNoDelete = options.Class.extend({
    forceNoDeleteButton: true,

    /**
     * @override
     */
    async onRemove() {
        await new Promise(resolve => {
            this.trigger_up('option_update', {
                optionName: 'MegaMenuLayout',
                name: 'reset_template',
                data: {
                    onSuccess: () => resolve(),
                }
            });
        });
    },
});

options.registry.sizing.include({
    /**
     * @override
     */
    start() {
        const defs = this._super(...arguments);
        const self = this;
        this.$handles.on('mousedown', function (ev) {
            // Since website is edited in an iframe, a div that goes over the
            // iframe is necessary to catch mousemove and mouseup events,
            // otherwise the iframe absorbs them.
            const $body = $(this.ownerDocument.body);
            if (!self.divEl) {
                self.divEl = document.createElement('div');
                self.divEl.style.position = 'absolute';
                self.divEl.style.height = '100%';
                self.divEl.style.width = '100%';
                self.divEl.setAttribute('id', 'iframeEventOverlay');
                $body.append(self.divEl);
            }
            const documentMouseUp = () => {
                // Multiple mouseup can occur if mouse goes out of the window
                // while moving.
                if (self.divEl) {
                    self.divEl.remove();
                    self.divEl = undefined;
                }
                $body.off('mouseup', documentMouseUp);
            };
            $body.on('mouseup', documentMouseUp);
        });
        return defs;
    }
});

options.registry.SwitchableViews = options.Class.extend({
    /**
     * @override
     */
    async willStart() {
        const _super = this._super.bind(this);
        this.switchableRelatedViews = await new Promise((resolve, reject) => {
            this.trigger_up('get_switchable_related_views', {
                onSuccess: resolve,
                onFailure: reject,
            });
        });
        return _super(...arguments);
    },
    /**
     * @override
     */
    _renderCustomXML(uiFragment) {
        for (const view of this.switchableRelatedViews) {
            const weCheckboxEl = document.createElement('we-checkbox');
            weCheckboxEl.setAttribute('string', view.name);
            weCheckboxEl.setAttribute('data-customize-website-views', view.key);
            weCheckboxEl.setAttribute('data-no-preview', 'true');
            weCheckboxEl.setAttribute('data-reload', '/');
            uiFragment.appendChild(weCheckboxEl);
        }
    },
    /***
     * @override
     */
    _computeVisibility() {
        return !!this.switchableRelatedViews.length;
    },
    /**
     * @override
     */
    _checkIfWidgetsUpdateNeedReload() {
        return true;
    }
});

return {
    UrlPickerUserValueWidget: UrlPickerUserValueWidget,
    FontFamilyPickerUserValueWidget: FontFamilyPickerUserValueWidget,
};
});
