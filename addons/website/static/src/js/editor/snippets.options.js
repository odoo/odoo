odoo.define('website.editor.snippets.options', function (require) {
'use strict';

const {ColorpickerWidget} = require('web.Colorpicker');
const config = require('web.config');
var core = require('web.core');
var Dialog = require('web.Dialog');
const dom = require('web.dom');
const weUtils = require('web_editor.utils');
var options = require('web_editor.snippets.options');
const wUtils = require('website.utils');
require('website.s_popup_options');

var _t = core._t;
var qweb = core.qweb;

const InputUserValueWidget = options.userValueWidgetsRegistry['we-input'];
const SelectUserValueWidget = options.userValueWidgetsRegistry['we-select'];

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
        this.el.classList.add('o_we_large_input');
        this.inputEl.classList.add('text-left');
        const options = {
            position: {
                collision: 'flip flipfit',
            },
            classes: {
                "ui-autocomplete": 'o_website_ui_autocomplete'
            },
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
        const style = window.getComputedStyle(document.documentElement);
        const nbFonts = parseInt(weUtils.getCSSVariableValue('number-of-fonts', style));
        // User fonts served by google server.
        const googleFontsProperty = weUtils.getCSSVariableValue('google-fonts', style);
        this.googleFonts = googleFontsProperty ? googleFontsProperty.split(/\s*,\s*/g) : [];
        this.googleFonts = this.googleFonts.map(font => font.substring(1, font.length - 1)); // Unquote
        // Local user fonts.
        const googleLocalFontsProperty = weUtils.getCSSVariableValue('google-local-fonts', style);
        this.googleLocalFonts = googleLocalFontsProperty ?
            googleLocalFontsProperty.slice(1, -1).split(/\s*,\s*/g) : [];
        // If a same font exists both remotely and locally, we remove the remote
        // font to prioritize the local font. The remote one will never be
        // displayed or loaded as long as the local one exists.
        this.googleFonts = this.googleFonts.filter(font => {
            const localFonts = this.googleLocalFonts.map(localFont => localFont.split(":")[0]);
            return localFonts.indexOf(`'${font}'`) === -1;
        });
        this.allFonts = [];

        await this._super(...arguments);

        const fontEls = [];
        const methodName = this.el.dataset.methodName || 'customizeWebsiteVariable';
        const variable = this.el.dataset.variable;
        const themeFontsNb = nbFonts - (this.googleLocalFonts.length + this.googleFonts.length);
        _.times(nbFonts, fontNb => {
            const realFontNb = fontNb + 1;
            const fontEl = document.createElement('we-button');
            fontEl.classList.add(`o_we_option_font_${realFontNb}`);
            fontEl.dataset.variable = variable;
            fontEl.dataset[methodName] = weUtils.getCSSVariableValue(`font-number-${realFontNb}`, style);
            const font = weUtils.getCSSVariableValue(`font-number-${realFontNb}`, style);
            this.allFonts.push(font);
            fontEl.dataset[methodName] = font;
            fontEl.dataset.font = realFontNb;
            if (realFontNb <= themeFontsNb) {
                // Add the "cloud" icon next to the theme's default fonts
                // because they are served by Google.
                fontEl.appendChild(Object.assign(document.createElement('i'), {
                    role: 'button',
                    className: 'text-info ml-2 fa fa-cloud',
                    title: _t("This font is hosted and served to your visitors by Google servers"),
                }));
            }
            fontEls.push(fontEl);
            this.menuEl.appendChild(fontEl);
        });

        if (this.googleLocalFonts.length) {
            const googleLocalFontsEls = fontEls.splice(-this.googleLocalFonts.length);
            googleLocalFontsEls.forEach((el, index) => {
                $(el).append(core.qweb.render('website.delete_google_font_btn', {
                    index: index,
                    local: true,
                }));
            });
        }

        if (this.googleFonts.length) {
            const googleFontsEls = fontEls.splice(-this.googleFonts.length);
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
                            // Font family is an encoded query parameter:
                            // "Open+Sans" needs to remain "Open+Sans".
                            const result = await fetch("https://fonts.googleapis.com/css?family=" + m[1] + ':300,300i,400,400i,700,700i', {method: 'HEAD'});
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
                        const googleFontServe = dialog.el.querySelector('#google_font_serve').checked;
                        const fontName = `'${font}'`;
                        // If the font already exists, it will only be added if
                        // the user chooses to add it locally when it is already
                        // imported from the Google Fonts server.
                        const fontExistsLocally = this.googleLocalFonts.some(localFont => localFont.split(':')[0] === fontName);
                        const fontExistsOnServer = this.allFonts.includes(fontName);
                        const preventFontAddition = fontExistsLocally || (fontExistsOnServer && googleFontServe);
                        if (preventFontAddition) {
                            inputEl.classList.add('is-invalid');
                            // Show custom validity error message.
                            inputEl.setCustomValidity(_t("This font already exists, you can only add it as a local font to replace the server version."));
                            inputEl.reportValidity();
                            return;
                        }
                        if (googleFontServe) {
                            this.googleFonts.push(font);
                        } else {
                            this.googleLocalFonts.push(`'${font}': ''`);
                        }
                        this.trigger_up('google_fonts_custo_request', {
                            values: {[variable]: `'${font}'`},
                            googleFonts: this.googleFonts,
                            googleLocalFonts: this.googleLocalFonts,
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
        const values = {};

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
        const isLocalFont = ev.target.dataset.localFont;
        let googleFontName;
        if (isLocalFont) {
            const googleFont = this.googleLocalFonts[googleFontIndex].split(':');
            // Remove double quotes
            googleFontName = googleFont[0].substring(1, googleFont[0].length - 1);
            values['delete-font-attachment-id'] = googleFont[1];
            this.googleLocalFonts.splice(googleFontIndex, 1);
        } else {
            googleFontName = this.googleFonts[googleFontIndex];
            this.googleFonts.splice(googleFontIndex, 1);
        }

        // Adapt font variable indexes to the removal
        const style = window.getComputedStyle(document.documentElement);
        _.each(FontFamilyPickerUserValueWidget.prototype.fontVariables, variable => {
            const value = weUtils.getCSSVariableValue(variable, style);
            if (value.substring(1, value.length - 1) === googleFontName) {
                // If an element is using the google font being removed, reset
                // it to the theme default.
                values[variable] = 'null';
            }
        });

        this.trigger_up('google_fonts_custo_request', {
            values: values,
            googleFonts: this.googleFonts,
            googleLocalFonts: this.googleLocalFonts,
        });
    },
});

const GPSPicker = InputUserValueWidget.extend({
    events: { // Explicitly not consider all InputUserValueWidget events
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
                onSuccess: key => {
                    if (!key) {
                        resolve(false);
                        return;
                    }

                    // TODO see _notifyGMapError, this tries to trigger an error
                    // early but this is not consistent with new gmap keys.
                    this._nearbySearch('(50.854975,4.3753899)', !!key)
                        .then(place => resolve(!!place));
                },
            });
        });
        if (!this._gmapLoaded && !this._gmapErrorNotified) {
            this.trigger_up('user_value_widget_critical');
            return;
        }
    },
    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this.el.classList.add('o_we_large_input');
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
        if (!this._gmapLoaded) {
            return;
        }

        this._gmapPlace = await this._nearbySearch(this._value);

        if (this._gmapPlace) {
            this.inputEl.value = this._gmapPlace.formatted_address;
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} gps
     * @param {boolean} [notify=true]
     * @returns {Promise}
     */
    async _nearbySearch(gps, notify = true) {
        if (this._gmapCacheGPSToPlace[gps]) {
            return this._gmapCacheGPSToPlace[gps];
        }

        const p = gps.substring(1).slice(0, -1).split(',');
        const location = new google.maps.LatLng(p[0] || 0, p[1] || 0);
        return new Promise(resolve => {
            const service = new google.maps.places.PlacesService(document.createElement('div'));
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
                        if (status === google.maps.places.PlacesServiceStatus.OK) {
                            this._gmapCacheGPSToPlace[gps] = place;
                            resolve(place);
                        } else if (GMAP_CRITICAL_ERRORS.includes(status)) {
                            if (notify) {
                                this._notifyGMapError();
                            }
                            resolve();
                        }
                    });
                } else if (GMAP_CRITICAL_ERRORS.includes(status)) {
                    if (notify) {
                        this._notifyGMapError();
                    }
                    resolve();
                } else {
                    resolve();
                }
            });
        });
    },
    /**
     * Indicates to the user there is an error with the google map API and
     * re-opens the configuration dialog. For good measures, this also notifies
     * a critical error which normally removes the related snippet entirely.
     *
     * @private
     */
    _notifyGMapError() {
        // TODO this should be better to detect all errors. This is random.
        // When misconfigured (wrong APIs enabled), sometimes Google throw
        // errors immediately (which then reaches this code), sometimes it
        // throws them later (which then induces an error log in the console
        // and random behaviors).
        if (this._gmapErrorNotified) {
            return;
        }
        this._gmapErrorNotified = true;

        this.displayNotification({
            type: 'danger',
            sticky: true,
            message: _t("A Google Map error occurred. Make sure to read the key configuration popup carefully."),
        });
        this.trigger_up('gmap_api_request', {
            editableMode: true,
            reconfigure: true,
            onSuccess: () => {
                this._gmapErrorNotified = false;
            },
        });

        setTimeout(() => this.trigger_up('user_value_widget_critical'));
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
            const oldValue = this._value;
            this._value = `(${location.lat()},${location.lng()})`;
            this._gmapCacheGPSToPlace[this._value] = gmapPlace;
            if (oldValue !== this._value) {
                this._onUserValueChange(ev);
            }
        }
    },
    /**
     * @override
     */
    _onInputBlur() {
        // As a stable fix: do not call the _super as we actually don't want
        // input focusout messing with the google map API. Because of this,
        // clicking on google map autocomplete suggestion on Firefox was not
        // working properly. This is kept as an empty function because of stable
        // policy (ensures custo can still extend this).
        // TODO review in master.
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
            if (!methodsNames.includes('customizeWebsiteViews')
                    && !methodsNames.includes('customizeWebsiteVariable')
                    && !methodsNames.includes('customizeWebsiteColor')) {
                continue;
            }
            let paramsReload = false;
            if (widget.getMethodsParams('customizeWebsiteViews').reload
                    || widget.getMethodsParams('customizeWebsiteVariable').reload
                    || widget.getMethodsParams('customizeWebsiteColor').reload) {
                paramsReload = true;
            }
            if (paramsReload || config.isDebug('assets')) {
                return (config.isDebug('assets') ? _t("It appears you are in debug=assets mode, all theme customization options require a page reload in this mode.") : true);
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
            case 'customizeWebsiteVariable': {
                return weUtils.getCSSVariableValue(params.variable);
            }
            case 'customizeWebsiteColor': {
                // TODO adapt in master
                const bugfixedValue = weUtils.getCSSVariableValue(`bugfixed-${params.color}`);
                if (bugfixedValue) {
                    return bugfixedValue;
                }
                return weUtils.getCSSVariableValue(params.color);
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
                await this._customizeWebsiteViews(widgetValue, params);
                break;
            case 'variable':
                await this._customizeWebsiteVariable(widgetValue, params);
                break;
            case 'color':
                await this._customizeWebsiteColor(widgetValue, params);
                break;
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
    /**
     * @private
     */
    _customizeWebsiteColor: async function (color, params) {
        const baseURL = '/website/static/src/scss/options/colors/';
        const colorType = params.colorType ? (params.colorType + '_') : '';
        const url = `${baseURL}user_${colorType}color_palette.scss`;

        if (color) {
            if (weUtils.isColorCombinationName(color)) {
                color = parseInt(color);
            } else if (!ColorpickerWidget.isCSSColor(color)) {
                color = `'${color}'`;
            }
        }
        return this._makeSCSSCusto(url, {[params.color]: color});
    },
    /**
     * @private
     */
    _customizeWebsiteVariable: async function (value, params) {
        return this._makeSCSSCusto('/website/static/src/scss/options/user_values.scss', {
            [params.variable]: value,
        });
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
     * @private
     * @param {OdooEvent} ev
     */
    _onGoogleFontsCustoRequest: function (ev) {
        const values = ev.data.values ? _.clone(ev.data.values) : {};
        const googleFonts = ev.data.googleFonts;
        const googleLocalFonts = ev.data.googleLocalFonts;
        if (googleFonts.length) {
            values['google-fonts'] = "('" + googleFonts.join("', '") + "')";
        } else {
            values['google-fonts'] = 'null';
        }
        // check undefined, this is a backport, a custo might not pass this key
        if (googleLocalFonts !== undefined && googleLocalFonts.length) {
            values['google-local-fonts'] = "(" + googleLocalFonts.join(", ") + ")";
        } else {
            values['google-local-fonts'] = 'null';
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
    },
    /**
     * @override
     */
    _removeShapeEl(shapeEl) {
        this.trigger_up('widgets_stop_request', {
            $target: $(shapeEl),
        });
        return this._super(...arguments);
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

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

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
            onSuccess: () => window.location.href = '/web#action=website.theme_install_kanban_action',
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
                    && widget.getMethodsParams('customizeWebsiteVariable').variable === 'color-palettes-number') {
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
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'body_bg_image_opt') {
            return false;
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
            mode: "ace/mode/xml",
            useWorker: false,
        });
        return aceEditor;
    },
    /**
     * @override
     */
    async _renderCustomXML(uiFragment) {
        uiFragment.querySelectorAll('we-colorpicker').forEach(el => {
            el.dataset.lazyPalette = 'true';
        });
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

    /**
     * @override
     */
    async updateUIVisibility() {
        await this._super(...arguments);
        const oldColorSystemEl = this.el.querySelector('.o_old_color_system_warning');
        oldColorSystemEl.classList.toggle('d-none', !this._showOldColorSystemWarning);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _renderCustomXML(uiFragment) {
        const paletteSelectorEl = uiFragment.querySelector('[data-variable="color-palettes-number"]');
        const style = window.getComputedStyle(document.documentElement);
        const nbPalettes = parseInt(weUtils.getCSSVariableValue('number-of-color-palettes', style));
        for (let i = 1; i <= nbPalettes; i++) {
            const btnEl = document.createElement('we-button');
            btnEl.classList.add('o_palette_color_preview_button');
            btnEl.dataset.customizeWebsiteVariable = i;
            for (let c = 1; c <= 5; c++) {
                const colorPreviewEl = document.createElement('span');
                colorPreviewEl.classList.add('o_palette_color_preview');
                const color = weUtils.getCSSVariableValue(`o-palette-${i}-o-color-${c}`, style);
                colorPreviewEl.style.backgroundColor = color;
                btnEl.appendChild(colorPreviewEl);
            }
            paletteSelectorEl.appendChild(btnEl);
        }

        for (let i = 1; i <= 5; i++) {
            const collapseEl = document.createElement('we-collapse');
            const ccPreviewEl = $(qweb.render('web_editor.color.combination.preview'))[0];
            ccPreviewEl.classList.add('text-center', `o_cc${i}`);
            collapseEl.appendChild(ccPreviewEl);
            const editionEls = $(qweb.render('website.color_combination_edition', {number: i}));
            for (const el of editionEls) {
                collapseEl.appendChild(el);
            }
            uiFragment.appendChild(collapseEl);
        }

        await this._super(...arguments);
    },
});

options.registry.menu_data = options.Class.extend({
    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this.isWebsiteDesigner = await this._rpc({
            'model': 'res.users',
            'method': 'has_group',
            'args': ['website.group_website_designer'],
        });
    },
    /**
     * When the users selects a menu, a dialog is opened to ask him if he wants
     * to follow the link (and leave editor), edit the menu or do nothing.
     *
     * @override
     */
    onFocus: function () {
        var self = this;
        const buttons = [
            {
                text: _t("Go to Link"), classes: 'btn-primary', click: function () {
                    self.trigger_up('request_save', {
                        reload: false,
                        onSuccess: function () {
                            window.location.href = self.$target.attr('href');
                        },
                    });
                },
            },
        ];
        if (this.isWebsiteDesigner) {
            buttons.push({
                text: _t("Edit the menu"), classes: 'btn-primary', click: function () {
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
                },
            });
        }
        buttons.push({text: _t("Stay on this page"), close: true});

        (new Dialog(this, {
            title: _t("Confirmation"),
            $content: $(core.qweb.render('website.leaving_current_page_edition')),
            buttons: buttons,
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
                proto.__link = '/web#action=base.action_res_company_form&view_type=form&id=' + encodeURIComponent(res && res[0] && res[0].company_id[0] || 1);
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
        _.each(this.$target.find('[data-slide], [data-slide-to]'), function (el) {
            var $el = $(el);
            if ($el.attr('data-target')) {
                $el.attr('data-target', '#' + id);
            } else if ($el.attr('href')) {
                $el.attr('href', '#' + id);
            }
        });
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
     * Adds a slide.
     *
     * @see this.selectClass for parameters
     */
    addSlide: function (previewMode) {
        const $items = this.$carousel.find('.carousel-item');
        this.$controls.removeClass('d-none');
        this.$indicators.append($('<li>', {
            'data-target': '#' + this.$carousel.attr('id'),
            'data-slide-to': $items.length,
        }));
        this.$indicators.append(' ');
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
            // The active indicator is deleted to ensure that the other
            // indicators will still work after the deletion.
            const $toDelete = $items.filter('.active').add(this.$indicators.find('.active'));
            this.$carousel.one('active_slide_targeted.carousel_item_option', () => {
                $toDelete.remove();
                // To ensure the proper functioning of the indicators, their
                // attributes must reflect the position of the slides.
                const indicatorsEls = this.$indicators[0].querySelectorAll('li');
                for (let i = 0; i < indicatorsEls.length; i++) {
                    indicatorsEls[i].setAttribute('data-slide-to', i);
                }
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
        if (compass === 'w' || compass === 'e') {
            const beginOffset = Number(beginClass.match(/offset-lg-([0-9-]+)|$/)[1] || beginClass.match(/offset-xl-([0-9-]+)|$/)[1] || 0);

            if (compass === 'w') {
                // don't change the right border position when we change the offset (replace col size)
                var beginCol = Number(beginClass.match(/col-lg-([0-9]+)|$/)[1] || 0);
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
            } else if (beginOffset > 0) {
                const endCol = Number(this.grid.e[0][current].match(/col-lg-([0-9]+)|$/)[1] || 0);
                // Avoids overflowing the grid to the right if the
                // column size + the offset exceeds 12.
                if ((endCol + beginOffset) > 12) {
                    this.$target[0].className = this.$target[0].className.replace(/\s*(col-lg-)([0-9-]+)/g, '');
                    this.$target[0].classList.add('col-lg-' + (12 - beginOffset));
                }
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
    selectCount: async function (previewMode, widgetValue, params) {
        const previousNbColumns = this.$('> .row').children().length;
        let $row = this.$('> .row');
        if (!$row.length) {
            $row = this.$target.contents().wrapAll($('<div class="row"><div class="col-lg-12"/></div>')).parent().parent();
        }

        const nbColumns = parseInt(widgetValue);
        await this._updateColumnCount($row, (nbColumns || 1) - $row.children().length);
        // Yield UI thread to wait for event to bubble before activate_snippet is called.
        // In this case this lets the select handle the click event before we switch snippet.
        // TODO: make this more generic in activate_snippet event handler.
        await new Promise(resolve => setTimeout(resolve));
        if (nbColumns === 0) {
            $row.contents().unwrap().contents().unwrap();
            this.trigger_up('activate_snippet', {$snippet: this.$target});
        } else if (previousNbColumns === 0) {
            this.trigger_up('activate_snippet', {$snippet: this.$('> .row').children().first()});
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        if (methodName === 'selectCount') {
            return this.$('> .row').children().length;
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'zero_cols_opt') {
            // Note: "s_allow_columns" indicates containers which may have
            // bare content (without columns) and are allowed to have columns.
            // By extension, we only show the "None" option on elements that
            // were marked as such as they were allowed to have bare content in
            // the first place.
            return this.$target.is('.s_allow_columns');
        }
        return this._super(...arguments);
    },
    /**
     * Adds new columns which are clones of the last column or removes the
     * last x columns.
     *
     * @private
     * @param {jQuery} $row - the row in which to update the columns
     * @param {integer} count - positif to add, negative to remove
     */
    _updateColumnCount: async function ($row, count) {
        if (!count) {
            return;
        }

        if (count > 0) {
            var $lastColumn = $row.children().last();
            for (var i = 0; i < count; i++) {
                await new Promise(resolve => {
                    this.trigger_up('clone_snippet', {$snippet: $lastColumn, onSuccess: resolve});
                });
            }
        } else {
            var self = this;
            for (const el of $row.children().slice(count)) {
                await new Promise(resolve => {
                    self.trigger_up('remove_snippet', {$snippet: $(el), onSuccess: resolve});
                });
            }
        }

        this._resizeColumns($row.children());
        this.trigger_up('cover_update');
    },
    /**
     * Resizes the columns so that they are kept on one row.
     *
     * @private
     * @param {jQuery} $columns - the columns to resize
     */
    _resizeColumns: function ($columns) {
        const colsLength = $columns.length;
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
        $panel.attr('data-parent', '#' + tablistId);
        $panel.data('parent', '#' + tablistId);

        const panelId = setUniqueId($panel, 'myCollapseTab');
        $tab.attr('data-target', '#' + panelId);
        $tab.data('target', '#' + panelId);
    },
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
        // Don't use setTarget, we want it to be set directly at initialization.
        this.$target = this.$target.closest('#wrapwrap > header');
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        // TODO Remove in master.
        const signInOptionEl = this.el.querySelector('[data-customize-website-views="portal.user_sign_in"]');
        signInOptionEl.dataset.noPreview = 'true';
    },
    /**
     * @private
     */
    async updateUI() {
        await this._super(...arguments);
        // For all header templates except those in the following array, change
        // the label of the option to "Mobile Alignment" (instead of
        // "Alignment") because it only impacts the mobile view.
        if (!["'default'", "'hamburger'", "'sidebar'", "'magazine'", "'hamburger-full'"]
            .includes(weUtils.getCSSVariableValue("header-template"))) {
            const alignmentOptionTitleEl = this.el.querySelector('[data-name="header_alignment_opt"] we-title');
            alignmentOptionTitleEl.textContent = _t("Mobile Alignment");
        }
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
        if (widgetName === 'option_logo_height_scrolled') {
            return !!this.$('.navbar-brand').length;
        }
        if (widgetName === 'header_alignment_opt') {
            if (!this.$target[0].querySelector('.o_offcanvas_menu_toggler')) {
                // If hamburger type is "Default", hides the alignment option
                // for "hamburger full" and "magazine" header templates.
                return !this.$target[0].querySelector('#oe_structure_header_hamburger_full_1, #oe_structure_header_magazine_1');
            }
            return true;
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
        // When entering edit mode via the URL (enable_editor) the WebsiteNavbar
        // is not yet ReadyForActions because it is waiting for its
        // sub-component EditPageMenu to start edit mode. Then invisible blocks
        // options start (so this option too). But for isShown() to work, the
        // navbar must be ReadyForActions. This is the reason why we can't wait
        // for isShown here, otherwise we would have a deadlock. On one hand the
        // navbar waiting for the invisible snippets options to be started to be
        // ReadyForActions and on the other hand this option which needs the
        // navbar to be ReadyForActions to be started.
        // TODO in master: Use the data-invisible system to get rid of this
        // piece of code.
        this._isShown().then(isShown => {
            this.trigger_up('snippet_option_visibility_update', {show: isShown});
        });
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
        await new Promise(resolve => {
            this.trigger_up('action_demand', {
                actionName: 'toggle_page_option',
                params: [{name: this.pageOptionName, value: show}],
                onSuccess: () => resolve(),
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
        return new Promise(resolve => {
            this.trigger_up('action_demand', {
                actionName: 'get_page_option',
                params: [this.pageOptionName],
                onSuccess: v => resolve(!!v),
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
        $(window).trigger('resize');
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
        await new Promise(resolve => {
            this.trigger_up('action_demand', {
                actionName: 'toggle_page_option',
                params: [{name: 'header_overlay', value: transparent}],
                onSuccess: () => resolve(),
            });
        });
        if (!transparent) {
            return;
        }
        await new Promise(resolve => {
            this.trigger_up('action_demand', {
                actionName: 'toggle_page_option',
                params: [{name: 'header_color', value: ''}],
                onSuccess: () => resolve(),
            });
        });
    },
    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        const _super = this._super.bind(this);
        if (methodName === 'visibility') {
            this.shownValue = await new Promise(resolve => {
                this.trigger_up('action_demand', {
                    actionName: 'get_page_option',
                    params: ['header_overlay'],
                    onSuccess: v => resolve(v ? 'transparent' : 'regular'),
                });
            });
        }
        return _super(...arguments);
    },
    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'header_visibility_opt') {
            return this.$target[0].classList.contains('o_header_sidebar') ? '' : 'true';
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _renderCustomXML(uiFragment) {
        // TODO in master: put this in the XML.
        const weSelectEl = uiFragment.querySelector('we-select#option_header_visibility');
        if (weSelectEl) {
            weSelectEl.dataset.name = 'header_visibility_opt';
        }
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
        return new Promise(resolve => {
            this.trigger_up('action_demand', {
                actionName: 'get_page_option',
                params: ['header_overlay'],
                onSuccess: value => resolve(!!value),
            });
        });
    },
});

/**
 * Manage the visibility of snippets on mobile.
 */
options.registry.MobileVisibility = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Allows to show or hide the associated snippet in mobile display mode.
     *
     * @see this.selectClass for parameters
     */
    showOnMobile(previewMode, widgetValue, params) {
        // For compatibility with former implementation: remove the previously
        // added `d-md-*` class if any, as it should now be `d-lg-*`.
        if (widgetValue) {
            this.$target[0].classList.remove(`d-md-${this.$target.css('display')}`);
        }
        const classes = `d-none d-lg-${this.$target.css('display')}`;
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
                classList.some(className => className.match(/^(d-md-|d-lg-)/g)) ? '' : 'true';
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
            this.displayNotification({
              type: 'success',
              message: _.str.sprintf(_t("Anchor copied to clipboard<br>Link: %s"), this._getAnchorLink()),
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

/**
 * Controls box properties.
 */
options.registry.Box = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * TODO this should be reviewed in master to avoid the need of using the
     * 'reset' previewMode and having to remember the previous box-shadow value.
     * We are forced to remember the previous box shadow before applying a new
     * one as the whole box-shadow value is handled by multiple widgets.
     *
     * @see this.selectClass for parameters
     */
    async setShadow(previewMode, widgetValue, params) {
        // Check if the currently configured shadow is not using the same shadow
        // mode, in which case nothing has to be done.
        const styles = window.getComputedStyle(this.$target[0]);
        const currentBoxShadow = styles['box-shadow'] || 'none';
        const currentMode = currentBoxShadow === 'none'
            ? ''
            : currentBoxShadow.includes('inset') ? 'inset' : 'outset';
        if (currentMode === widgetValue) {
            return;
        }

        if (previewMode === true) {
            this._prevBoxShadow = currentBoxShadow;
        }

        // Add/remove the shadow class
        this.$target.toggleClass(params.shadowClass, !!widgetValue);

        // Change the mode of the old box shadow. If no shadow was currently
        // set then get the shadow value that is supposed to be set according
        // to the shadow mode. Try to apply it via the selectStyle method so
        // that it is either ignored because the shadow class had its effect or
        // forced (to the shadow value or none) if toggling the class is not
        // enough (e.g. if the item has a default shadow coming from CSS rules,
        // removing the shadow class won't be enough to remove the shadow but in
        // most other cases it will).
        let shadow = 'none';
        if (previewMode === 'reset') {
            shadow = this._prevBoxShadow;
        } else {
            if (currentBoxShadow === 'none') {
                shadow = this._getDefaultShadow(widgetValue, params.shadowClass) || 'none';
            } else {
                if (widgetValue === 'outset') {
                    shadow = currentBoxShadow.replace('inset', '').trim();
                } else if (widgetValue === 'inset') {
                    shadow = currentBoxShadow + ' inset';
                }
            }
        }
        await this.selectStyle(previewMode, shadow, Object.assign({cssProperty: 'box-shadow'}, params));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === 'setShadow') {
            const shadowValue = this.$target.css('box-shadow');
            if (!shadowValue || shadowValue === 'none') {
                return '';
            }
            return this.$target.css('box-shadow').includes('inset') ? 'inset' : 'outset';
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'fake_inset_shadow_opt') {
            return false;
        }
        return this._super(...arguments);
    },
    /**
     * @private
     * @param {string} type
     * @param {string} shadowClass
     * @returns {string}
     */
    _getDefaultShadow(type, shadowClass) {
        const el = document.createElement('div');
        if (type) {
            el.classList.add(shadowClass);
        }

        let shadow = ''; // TODO in master this should be changed to 'none'
        document.body.appendChild(el);
        switch (type) {
            case 'outset': {
                shadow = $(el).css('box-shadow');
                break;
            }
            case 'inset': {
                shadow = $(el).css('box-shadow') + ' inset';
                break;
            }
        }
        el.remove();
        return shadow;
    }
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
            return this.customizeWebsiteVariable(previewMode, defaultShadow || 'none', params);
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

        // TODO: `o_record_has_cover` should be handled using model field, not
        // resize_class to avoid all of this.
        let coverClass = this.$el.find('[data-cover-opt-name="size"] we-button.active').data('selectClass') || '';
        const bg = this.$image.css('background-image');
        if (bg && bg !== 'none') {
            coverClass += " o_record_has_cover";
        }
        // Update saving dataset
        this.$target[0].dataset.coverClass = coverClass;
        this.$target[0].dataset.textAlignClass = this.$el.find('[data-cover-opt-name="text_align"] we-button.active').data('selectClass') || '';
        this.$target[0].dataset.filterValue = this.$filterValueOpts.filter('.active').data('filterValue') || 0.0;
        let colorPickerWidget = null;
        this.trigger_up('user_value_widget_request', {
            name: 'bg_color_opt',
            onSuccess: _widget => colorPickerWidget = _widget,
        });
        const color = colorPickerWidget._value;
        const isCSSColor = ColorpickerWidget.isCSSColor(color);
        this.$target[0].dataset.bgColorClass = isCSSColor ? '' : weUtils.computeColorClasses([color])[0];
        this.$target[0].dataset.bgColorStyle = isCSSColor ? `background-color: ${color};` : '';
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
});

options.registry.ContainerWidth = options.Class.extend({
    /**
     * @override
     */
    cleanForSave: function () {
        this.$target.removeClass('o_container_preview');
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    selectClass: async function (previewMode, widgetValue, params) {
        await this._super(...arguments);
        if (previewMode === 'reset') {
            this.$target.removeClass('o_container_preview');
        } else if (previewMode) {
            this.$target.addClass('o_container_preview');
        }
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
        if (params.name === 'move_up_opt' || params.name === 'move_down_opt') {
            const mainScrollingEl = $().getScrollingElement()[0];
            const elTop = this.$target[0].getBoundingClientRect().top;
            const heightDiff = mainScrollingEl.offsetHeight - this.$target[0].offsetHeight;
            const bottomHidden = heightDiff < elTop;
            const hidden = elTop < 0 || bottomHidden;
            if (hidden) {
                dom.scrollTo(this.$target[0], {
                    extraOffset: 50,
                    forcedOffset: bottomHidden ? heightDiff - 50 : undefined,
                    easing: 'linear',
                    duration: 500,
                });
            }
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

// TODO there is no data-js associated to this but a data-option-name, somehow
// it acts as data-js... it will be reviewed in master.
options.registry.minHeight = options.Class.extend({
    /**
     * @override
     */
    _renderCustomXML(uiFragment) {
        // TODO adapt in master. This sets up a different UI for the image
        // gallery snippet: for this one, we allow to force a specific height
        // in auto mode. It was done in stable as without it, the default height
        // is difficult to understand for the user as it depends on screen
        // height of the one who edited the website and not on the added images.
        // It was also a regression as in <= 11.0, this was a possibility.
        if (this.$target[0].dataset.snippet !== 's_image_gallery') {
            return;
        }
        const minHeightEl = uiFragment.querySelector('we-button-group');
        if (!minHeightEl) {
            return;
        }
        minHeightEl.setAttribute('string', _t("Min-Height"));
        const heightEl = document.createElement('we-input');
        heightEl.setAttribute('string', _t("└ Height"));
        heightEl.dataset.name = 'image_gallery_height_opt';
        heightEl.dataset.unit = 'px';
        heightEl.dataset.selectStyle = '';
        heightEl.dataset.cssProperty = 'height';
        // For this setting, we need to always force the style (= if the block
        // is naturally 800px tall and the user enters 800px for this setting,
        // we set 800px as inline style anyway). Indeed, this snippet's style
        // is based on the height that is forced but once the related public
        // widgets are started, the inner carousel items receive a min-height
        // which makes it so the snippet "natural" height is equal to the
        // initially forced height... so if the style is not forced, it would
        // ultimately be removed by mistake thinking it is not necessary.
        // Note: this is forced as not important as we still need the height to
        // be reset to 'auto' in mobile (generic css rules).
        heightEl.dataset.forceStyle = '';
        uiFragment.appendChild(heightEl);
    },
    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'image_gallery_height_opt') {
            return !this.$target[0].classList.contains('o_half_screen_height')
                && !this.$target[0].classList.contains('o_full_screen_height');
        }
        return this._super(...arguments);
    },
});

return {
    UrlPickerUserValueWidget: UrlPickerUserValueWidget,
    FontFamilyPickerUserValueWidget: FontFamilyPickerUserValueWidget,
};
});
