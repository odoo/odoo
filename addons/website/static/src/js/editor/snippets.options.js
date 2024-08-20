/** @odoo-module **/

import { loadCSS } from "@web/core/assets";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { registry } from "@web/core/registry";
import { useChildRef, useService } from "@web/core/utils/hooks";
import weUtils from "@web_editor/js/common/utils";
import options from "@web_editor/js/editor/snippets.options.legacy";
import { NavbarLinkPopoverWidget } from "@website/js/widgets/link_popover_widget";
import wUtils from "@website/js/utils";
import {
    applyModifications,
    isImageCorsProtected,
    isImageSupportedForStyle,
    loadImage,
    loadImageInfo,
} from "@web_editor/js/editor/image_processing";
import { SnippetPopup } from "../../snippets/s_popup/options";
import { range } from "@web/core/utils/numbers";
import { _t } from "@web/core/l10n/translation";
import {Domain} from "@web/core/domain";
import {
    isCSSColor,
    convertCSSColorToRgba,
    convertRgbaToCSSColor,
    convertRgbToHsl,
    convertHslToRgb,
 } from '@web/core/utils/colors';
import { renderToElement } from "@web/core/utils/render";
import { browser } from "@web/core/browser/browser";
import {
    removeTextHighlight,
    drawTextHighlightSVG,
} from "@website/js/text_processing";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { Component, markup, onMounted, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";

import {
    BackgroundToggler,
    Box,
    ButtonUserValue,
    CarouselHandler,
    GridColumns,
    ImageTools,
    LayoutColumn,
    Many2oneUserValue,
    registerBackgroundOptions,
    ReplaceMedia,
    SelectTemplate,
    SelectUserValue,
    serviceCached,
    SnippetMove,
    SnippetOption,
    SnippetOptionComponent,
    SnippetSave,
    UserValue,
    UserValueComponent,
    vAlignment,
    WeButton,
    WeInput,
    WeSelect,
    WeTitle,
} from '@web_editor/js/editor/snippets.options';
import { registerWebsiteOption } from "./snippets.registry";

patch(SnippetOption.prototype, {
    loadMethodsData() {
        super.loadMethodsData(...arguments);

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

patch(Many2oneUserValue.prototype, {
    /**
     * @override
     */
    constructorPatch() {
        // We can't do that with `constructor()` because super calls a static
        // property with `this.constructor.prop`. Overriding the constructor in
        // a patch makes it impossible to call such static properties.
        super.constructorPatch(...arguments);
        this.fields = this.env.services.field;
    },
    /**
     * @override
     */
    async _getSearchDomain() {
        // Add the current website's domain if the model has a website_id field.
        // Note that the `_rpc` method is cached in Many2X user value widget,
        // see `_rpcCache`.
        const websiteIdField = await this.fields.loadFields(this.options.model, {
            fieldNames: ["website_id"],
        });
        const modelHasWebsiteId = !!websiteIdField["website_id"];
        if (modelHasWebsiteId && !this.options.domain.find(arr => arr[0] === "website_id")) {
            this.options.domain =
                Domain.and([this.options.domain, wUtils.websiteDomain(this)]).toList();
        }
        return this.options.domain;
    },
});

class WeUrlPicker extends WeInput {
    static template = "website.WeUrlPicker";
    static defaultProps = {
        ...WeInput.defaultProps,
        unit: "",
        saveUnit: "",
    };
    setup() {
        super.setup();
        this.website = useService('website');
        useEffect((inputEl) => {
            const options = {
                classes: {
                    "ui-autocomplete": 'o_website_ui_autocomplete'
                },
                urlChosen: this._onWebsiteURLChosen.bind(this),
            };
            const unmountAutocompleteWithPages = wUtils.autocompleteWithPages(inputEl, options);
            return () => unmountAutocompleteWithPages();
        }, () => [this.inputRef.el]);
    }

    // TODO maybe these open & close can be removed
    open() {
        super.open(...arguments);
        document.querySelector(".o_website_ui_autocomplete")?.classList?.remove("d-none");
    }

    close() {
        super.close(...arguments);
        document.querySelector(".o_website_ui_autocomplete")?.classList?.add("d-none");
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the autocomplete change the input value.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onWebsiteURLChosen(ev) {
        this.state.value = this.inputRef.el.value;
        this._onUserValueChange(ev);
    }
    /**
     * Redirects to the URL the widget currently holds.
     *
     * @private
     */
    _onRedirectTo() {
        if (this.state.value) {
            window.open(this.state.value, '_blank');
        }
    }
}
registry.category("snippet_widgets").add("WeUrlPicker", WeUrlPicker);

class GoogleFontAutoComplete extends AutoComplete {
    setup() {
        super.setup();
        this.inputRef = useRef("input");
        this.sourcesListRef = useRef("sourcesList");
        useEffect((el) => {
            el.setAttribute("id", "google_font");
        }, () => [this.inputRef.el]);
    }

    get dropdownOptions() {
        return {
            ...super.dropdownOptions,
            position: "bottom-fit",
        };
    }

    onInput(ev) {
        super.onInput(ev);
        if (this.sourcesListRef.el) {
            this.sourcesListRef.el.scrollTop = 0;
        }
    }
}

class FontFamilyUserValue extends SelectUserValue {
    constructor() {
        super(...arguments);
        const style = window.getComputedStyle(this.$target[0].ownerDocument.documentElement);
        const nbFonts = parseInt(weUtils.getCSSVariableValue('number-of-fonts', style));
        // User fonts served by google server.
        const googleFontsProperty = weUtils.getCSSVariableValue('google-fonts', style);
        this.googleFonts = googleFontsProperty ? googleFontsProperty.split(/\s*,\s*/g) : [];
        this.googleFonts = this.googleFonts.map(font => font.substring(1, font.length - 1)); // Unquote
        // Local user fonts.
        const googleLocalFontsProperty = weUtils.getCSSVariableValue('google-local-fonts', style);
        this.googleLocalFonts = googleLocalFontsProperty ?
            googleLocalFontsProperty.slice(1, -1).split(/\s*,\s*/g) : [];
        const uploadedLocalFontsProperty = weUtils.getCSSVariableValue('uploaded-local-fonts', style);
        this.uploadedLocalFonts = uploadedLocalFontsProperty ?
            uploadedLocalFontsProperty.slice(1, -1).split(/\s*,\s*/g) : [];
        // If a same font exists both remotely and locally, we remove the remote
        // font to prioritize the local font. The remote one will never be
        // displayed or loaded as long as the local one exists.
        this.googleFonts = this.googleFonts.filter(font => {
            const localFonts = this.googleLocalFonts.map(localFont => localFont.split(":")[0]);
            return localFonts.indexOf(`'${font}'`) === -1;
        });
        this.allFonts = [];

        const fontsToLoad = [];
        for (const font of this.googleFonts) {
            const fontURL = `https://fonts.googleapis.com/css?family=${encodeURIComponent(font).replace(/%20/g, '+')}`;
            fontsToLoad.push(fontURL);
        }
        for (const font of this.googleLocalFonts) {
            const attachmentId = font.split(/\s*:\s*/)[1];
            const fontURL = `/web/content/${encodeURIComponent(attachmentId)}`;
            fontsToLoad.push(fontURL);
        }
        const proms = fontsToLoad.map(async fontURL => loadCSS(fontURL));
        this.fontsLoadingProm = Promise.all(proms);

        this._fonts = [];
        const themeFontsNb = nbFonts - (this.googleLocalFonts.length + this.googleFonts.length + this.uploadedLocalFonts.length);
        const localFontsOffset = nbFonts - this.googleLocalFonts.length - this.uploadedLocalFonts.length;
        const uploadedFontsOffset = nbFonts - this.uploadedLocalFonts.length;

        for (let fontNb = 0; fontNb < nbFonts; fontNb++) {
            const realFontNb = fontNb + 1;
            const fontKey = weUtils.getCSSVariableValue(`font-number-${realFontNb}`, style);
            this.allFonts.push(fontKey);
            let fontName = fontKey.slice(1, -1); // Unquote
            let fontFamily = fontName;
            const isSystemFonts = fontName === "SYSTEM_FONTS";
            if (isSystemFonts) {
                fontName = _t("System Fonts");
                fontFamily = 'var(--o-system-fonts)';
            }

            let type = "cloud";
            let indexForType = fontNb - themeFontsNb;
            if (fontNb >= localFontsOffset) {
                if (fontNb <= uploadedFontsOffset) {
                    type = "google";
                    indexForType = fontNb - localFontsOffset;
                } else {
                    type = "uploaded";
                    indexForType = fontNb - uploadedFontsOffset;
                }
            } 
            this._fonts.push({
                type,
                indexForType,
                fontFamily,
                string: fontName,
            });
        }
    }

    async start() {
        return this.fontsLoadingProm;
    }

    get fonts() {
        return this._fonts;
    }
}

class WeFontFamilyPicker extends WeSelect {
    static isContainer = true;
    static StateModel = FontFamilyUserValue;
    static template = "website.WeFontFamilyPicker";
    static components = { ...WeSelect.components, WeButton, WeTitle };
    static defaultProps = {
        ...WeSelect.defaultProps,
        selectMethod: "customizeWebsiteVariable",
    };
    fontVariables = []; // Filled by editor menu when all options are loaded

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.orm = useService("orm");
    }

    forwardProps(fontValue) {
        const result = Object.assign({}, this.props, {
            [this.props.selectMethod]: fontValue.fontFamily,
        });
        delete result.selectMethod;
        return result;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    async _onAddFontClick() {
        const addFontDialog = class extends Component {
            static template = "website.dialog.addFont";
            static components = { GoogleFontAutoComplete, Dialog };
            static props = { close: Function, title: String, onClickSave: Function };
            state = useState({
                valid: true, loading: false,
                googleFontFamily: undefined, googleServe: true,
                uploadedFontName: undefined, uploadedFonts: [], uploadedFontFaces: undefined,
                previewText: _t("The quick brown fox jumps over the lazy dog."),
            });
            fileInput = useRef("fileInput");
            async onClickSave() {
                if (this.state.loading) {
                    return;
                }
                this.state.loading = true;
                const shouldClose = await this.props.onClickSave(this.state);
                if (shouldClose) {
                    this.props.close();
                    return;
                }
                this.state.loading = false;
            }
            onClickCancel() {
                this.props.close();
            }
            get getGoogleFontList() {
                return [{options: async (term) => {
                    if (!this.googleFontList) {
                        await rpc("/website/google_font_metadata").then((data) => {
                            this.googleFontList = data.familyMetadataList.map((font) => font.family);
                        });
                    }
                    const lowerCaseTerm = term.toLowerCase();
                    const filtered = this.googleFontList.filter((value) => value.toLowerCase().includes(lowerCaseTerm));
                    return filtered.map((fontFamilyName) => {
                        return {
                            label: fontFamilyName,
                            value: fontFamilyName,
                        };
                    });
                }}];
            }
            async onGoogleFontSelect(selected) {
                this.fileInput.el.value = "";
                this.state.uploadedFonts = [];
                this.state.uploadedFontName = undefined;
                this.state.uploadedFontFaces = undefined;
                try {
                    const fontFamily = selected.value;
                    const result = await fetch(`https://fonts.googleapis.com/css?family=${encodeURIComponent(fontFamily)}:300,300i,400,400i,700,700i`, {method: 'HEAD'});
                    // Google fonts server returns a 400 status code if family is not valid.
                    if (result.ok) {
                        const linkId = `previewFont${fontFamily}`;
                        if (!document.querySelector(`link[id='${linkId}']`)) {
                            const linkEl = document.createElement("link");
                            linkEl.id = linkId;
                            linkEl.setAttribute("href", result.url);
                            linkEl.setAttribute("rel", "stylesheet");
                            linkEl.dataset.fontPreview = true;
                            document.head.appendChild(linkEl);
                        }
                        this.state.googleFontFamily = fontFamily;
                    } else {
                        this.state.googleFontFamily = undefined;
                    }
                } catch (error) {
                    console.error(error);
                }
            }
            async onUploadChange(e) {
                this.state.googleFontFamily = undefined;
                const file = this.fileInput.el.files[0];
                if (!file) {
                    this.state.uploadedFonts = [];
                    this.state.uploadedFontName = undefined;
                    this.state.uploadedFontFaces = undefined;
                    return;
                }
                const reader = new FileReader();
                reader.onload = (e) => {
                    const base64 = e.target.result.split(',')[1];
                    rpc("/website/theme_upload_font", {
                        name: file.name,
                        data: base64,
                    }).then(result => {
                        this.state.uploadedFonts = result;
                        this.updateFontStyle(file.name.substr(0, file.name.lastIndexOf(".")));
                    });
                };
                reader.readAsDataURL(file);
            }
            /**
             * Deduces the style of uploaded fonts and creates inline style
             * elements in the backend iframe's head to make the font-faces
             * available for preview.
             *
             * @param baseFontName
             */
            updateFontStyle(baseFontName) {
                const targetFonts = {};
                // Add candidate tags to fonts.
                let shortestNamedFont;
                for (const font of this.state.uploadedFonts) {
                    if (!shortestNamedFont || font.name.length < shortestNamedFont.name.length) {
                        shortestNamedFont = font;
                    }
                    font.isItalic = /italic/i.test(font.name);
                    font.isLight = /light|300/i.test(font.name);
                    font.isBold = /bold|700/i.test(font.name);
                    font.isRegular = /regular|400/i.test(font.name);
                    font.weight = font.isRegular ? 400 : font.isLight ? 300 : font.isBold ? 700 : undefined;
                    if (font.isItalic && !font.weight) {
                        if (!/00|thin|medium|black|condense|extrude/i.test(font.name)) {
                            font.isRegular = true;
                            font.weight = 400;
                        }
                    }
                    font.style = font.isItalic ? "italic" : "normal";
                    if (font.weight) {
                        targetFonts[`${font.weight}${font.style}`] = font;
                    }
                }
                if (!Object.values(targetFonts).filter((font) => font.isRegular).length) {
                    // Keep font with shortest name.
                    shortestNamedFont.weight = 400;
                    shortestNamedFont.style = "normal";
                    targetFonts["400"] = shortestNamedFont;
                }
                const fontFaces = [];
                for (const font of Object.values(targetFonts)) {
                    fontFaces.push(`@font-face{
                        font-family: ${baseFontName};
                        font-style: ${font.style};
                        font-weight: ${font.weight};
                        src:url("${font.url}");
                    }`);
                }
                let styleEl = document.head.querySelector(`style[id='WebsiteThemeFontPreview-${baseFontName}']`);
                if (!styleEl) {
                    styleEl = document.createElement("style");
                    styleEl.id = `WebsiteThemeFontPreview-${baseFontName}`;
                    styleEl.dataset.fontPreview = true;
                    document.head.appendChild(styleEl);
                }
                const previewFontFaces = fontFaces.join("");
                styleEl.textContent = previewFontFaces;
                this.state.uploadedFontName = baseFontName;
                this.state.uploadedFontFaces = previewFontFaces;
            }
        };
        this.dialog.add(addFontDialog, {
            title: _t("Add a Google font or upload a custom font"),
            onClickSave: async (state) => {
                const uploadedFontName = state.uploadedFontName;
                const uploadedFontFaces = state.uploadedFontFaces;
                let font = undefined;
                if (uploadedFontName && uploadedFontFaces) {
                    const fontExistsLocally = this.state.uploadedLocalFonts.some(localFont => localFont.split(':')[0] === `'${uploadedFontName}'`);
                    if (fontExistsLocally) {
                        this.dialog.add(ConfirmationDialog, {
                            title: _t("Font exists"),
                            body: _t("This uploaded font already exists.\nTo replace an existing font, remove it first."),
                        });
                        return;
                    }
                    const homonymGoogleFontExists =
                        this.state.googleFonts.some(font => font === uploadedFontName) ||
                        this.state.googleLocalFonts.some(font => font.split(':')[0] === `'${uploadedFontName}'`);
                    if (homonymGoogleFontExists) {
                        this.dialog.add(ConfirmationDialog, {
                            title: _t("Font name already used"),
                            body: _t("A font with the same name already exists.\nTry renaming the uploaded file."),
                        });
                        return;
                    }
                    // Create attachment.
                    const [fontCssId] = await this.orm.call("ir.attachment", "create_unique", [[{
                        name: uploadedFontName,
                        description: `CSS font face for ${uploadedFontName}`,
                        datas: btoa(uploadedFontFaces),
                        res_model: "ir.attachment",
                        mimetype: "text/css",
                        "public": true,
                    }]]);
                    this.state.uploadedLocalFonts.push(`'${uploadedFontName}': ${fontCssId}`);
                    font = uploadedFontName;
                } else {
                    let isValidFamily = false;
                    font = state.googleFontFamily;

                    try {
                        const result = await fetch("https://fonts.googleapis.com/css?family=" + encodeURIComponent(font) + ':300,300i,400,400i,700,700i', {method: 'HEAD'});
                        // Google fonts server returns a 400 status code if family is not valid.
                        if (result.ok) {
                            isValidFamily = true;
                        }
                    } catch (error) {
                        console.error(error);
                    }

                    if (!isValidFamily) {
                        this.dialog.add(ConfirmationDialog, {
                            title: _t("Font access"),
                            body: _t("The selected font cannot be accessed."),
                        });
                        return;
                    }

                    const googleFontServe = state.googleServe;
                    const fontName = `'${font}'`;
                    // If the font already exists, it will only be added if
                    // the user chooses to add it locally when it is already
                    // imported from the Google Fonts server.
                    const fontExistsLocally = this.state.googleLocalFonts.some(localFont => localFont.split(':')[0] === fontName);
                    const fontExistsOnServer = this.state.allFonts.includes(fontName);
                    const preventFontAddition = fontExistsLocally || (fontExistsOnServer && googleFontServe);
                    if (preventFontAddition) {
                        this.dialog.add(ConfirmationDialog, {
                            title: _t("Font exists"),
                            body: _t("This font already exists, you can only add it as a local font to replace the server version."),
                        });
                        return;
                    }
                    if (googleFontServe) {
                        this.state.googleFonts.push(font);
                    } else {
                        this.state.googleLocalFonts.push(`'${font}': ''`);
                    }
                }
                this.state.option._onFontsCustoRequest({
                    values: {[this.props.variable]: `'${font}'`},
                    googleFonts: this.state.googleFonts,
                    googleLocalFonts: this.state.googleLocalFonts,
                    uploadedLocalFonts: this.state.uploadedLocalFonts,
                });
                let styleEl = document.head.querySelector(`[id='WebsiteThemeFontPreview-${font}']`);
                if (styleEl) {
                    delete styleEl.dataset.fontPreview;
                }
                return true;
            },
        },
        {
            onClose: () => {
                for (const el of document.head.querySelectorAll("[data-font-preview]")) {
                    el.remove();
                }
            },
        });
    }
    /**
     * @private
     * @param {Event} ev TODO update
     */
    async _onDeleteFontClick(font) {
        const values = {};

        const save = await new Promise(resolve => {
            this.env.services.dialog.add(ConfirmationDialog, {
                body: _t("Deleting a font requires a reload of the page. This will save all your changes and reload the page, are you sure you want to proceed?"),
                confirm: () => resolve(true),
                cancel: () => resolve(false),
            });
        });
        if (!save) {
            return;
        }

        // Remove Google font
        const fontIndex = font.indexForType;
        const localFont = font.type;
        let fontName;
        if (localFont === 'uploaded') {
            const font = this.state.uploadedLocalFonts[fontIndex].split(':');
            // Remove double quotes
            fontName = font[0].substring(1, font[0].length - 1);
            values['delete-font-attachment-id'] = font[1];
            this.state.uploadedLocalFonts.splice(fontIndex, 1);
        } else if (localFont === 'google') {
            const googleFont = this.state.googleLocalFonts[fontIndex].split(':');
            // Remove double quotes
            fontName = googleFont[0].substring(1, googleFont[0].length - 1);
            values['delete-font-attachment-id'] = googleFont[1];
            this.state.googleLocalFonts.splice(fontIndex, 1);
        } else {
            fontName = this.state.googleFonts[fontIndex];
            this.state.googleFonts.splice(fontIndex, 1);
        }

        // Adapt font variable indexes to the removal
        const style = window.getComputedStyle(this.state.$target[0].ownerDocument.documentElement);
        this.fontVariables.forEach((variable) => {
            const value = weUtils.getCSSVariableValue(variable, style);
            if (value.substring(1, value.length - 1) === fontName) {
                // If an element is using the google font being removed, reset
                // it to the theme default.
                values[variable] = 'null';
            }
        });
        this.state.option._onFontsCustoRequest({
            values: values,
            googleFonts: this.state.googleFonts,
            googleLocalFonts: this.state.googleLocalFonts,
            uploadedLocalFonts: this.state.uploadedLocalFonts,
        });
    }
}
registry.category("snippet_widgets").add("WeFontFamilyPicker", WeFontFamilyPicker);

class GpsUserValue extends UserValue {
    _gmapCacheGPSToPlace = {};

    constructor() {
        super(...arguments);
        this._state._gmapLoaded = false;
        this._state.gmapPlace = {};
        this.contentWindow = this.$target[0].ownerDocument.defaultView;
    }
    async start() {
        super.start();
        this._state._gmapLoaded = await new Promise(resolve => {
            this.env.gmapApiRequest({
                editableMode: true,
                configureIfNecessary: true,
                onSuccess: key => {
                    if (!key) {
                        resolve(false);
                        return;
                    }

                    // TODO see _notifyGMapError, this tries to trigger an error
                    // early but this is not consistent with new gmap keys.
                    const startLocation = this.$target[0].dataset.mapGps || "(50.854975,4.3753899)";
                    this._nearbySearch(startLocation, !!key)
                        .then(place => {
                            this._state.gmapPlace = place;
                            resolve(!!place);
                        });
                },
            });
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getMethodsParams(methodName) {
        return Object.assign({gmapPlace: this._state.gmapPlace || {}}, super.getMethodsParams(...arguments));
    }
    /**
     * @override
     */
    async setValue() {
        await super.setValue(...arguments);
        if (!this._state._gmapLoaded) {
            return;
        }

        this._state.gmapPlace = await this._nearbySearch(this.value);
    }
    get formattedAddress() {
        return this._state.gmapPlace?.formatted_address;
    }
    get isGmapLoaded() {
        return this._state._gmapLoaded;
    }

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
        const location = new this.contentWindow.google.maps.LatLng(p[0] || 0, p[1] || 0);
        return new Promise(resolve => {
            const service = new this.contentWindow.google.maps.places.PlacesService(document.createElement('div'));
            service.nearbySearch({
                // Do a 'nearbySearch' followed by 'getDetails' to avoid using
                // GMap Geocoder which the user may not have enabled... but
                // ideally Geocoder should be used to get the exact location at
                // those coordinates and to limit billing query count.
                location: location,
                radius: 1,
            }, (results, status) => {
                const GMAP_CRITICAL_ERRORS = [
                    this.contentWindow.google.maps.places.PlacesServiceStatus.REQUEST_DENIED,
                    this.contentWindow.google.maps.places.PlacesServiceStatus.UNKNOWN_ERROR
                ];
                if (status === this.contentWindow.google.maps.places.PlacesServiceStatus.OK) {
                    service.getDetails({
                        placeId: results[0].place_id,
                        fields: ['geometry', 'formatted_address'],
                    }, (place, status) => {
                        if (status === this.contentWindow.google.maps.places.PlacesServiceStatus.OK) {
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
    }
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

        this.env.services.notification.add(
            _t("A Google Map error occurred. Make sure to read the key configuration popup carefully."),
            { type: 'danger', sticky: true }
        );
        this.env.services.website.websiteRootInstance.trigger_up('gmap_api_request', {
            editableMode: true,
            reconfigure: true,
            onSuccess: () => {
                this._gmapErrorNotified = false;
            },
        });

        // TODO user_value_widget_critical
        setTimeout(() => this.env.services.website.websiteRootInstance.trigger_up('user_value_widget_critical'));
    }
}

class WeGpsPicker extends UserValueComponent {
    static template = "website.WeGpsPicker";
    static StateModel = GpsUserValue;
    setup() {
        super.setup();
        this.inputRef = useRef("input");

        // The google API will be loaded inside the website iframe. Let's try
        // not having to load it in the backend too and just using the iframe
        // google object instead.
        useEffect((gmapLoaded, inputEl) => {
            if (gmapLoaded && inputEl) {
                const contentWindow = this.state.$target[0].ownerDocument.defaultView;
                this._gmapAutocomplete = new contentWindow.google.maps.places.Autocomplete(this.inputRef.el, {types: ['geocode']});
                contentWindow.google.maps.event.addListener(this._gmapAutocomplete, 'place_changed', this._onPlaceChanged.bind(this));
            }
        }, () => [this.state.isGmapLoaded, this.inputRef.el]);
        onWillUnmount(() => {
            // Without this, the google library injects elements inside the backend
            // DOM but do not remove them once the editor is left. Notice that
            // this is also done when the widget is destroyed for another reason
            // than leaving the editor, but if the google API needs that container
            // again afterwards, it will simply recreate it.
            for (const el of document.body.querySelectorAll('.pac-container')) {
                el.remove();
            }
        });
    }

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
            this.state.gmapPlace = gmapPlace;
            const location = this.state.gmapPlace.geometry.location;
            const oldValue = this.state.value;
            this.state.value = `(${location.lat()},${location.lng()})`;
            this.state._gmapCacheGPSToPlace[this.state.value] = gmapPlace;
            if (oldValue !== this.state.value) {
                this._onUserValueChange(ev);
            }
        }
    }
}
registry.category("snippet_widgets").add("WeGpsPicker", WeGpsPicker);
/*
options.userValueWidgetsRegistry['we-urlpicker'] = UrlPickerUserValueWidget;
options.userValueWidgetsRegistry['we-fontfamilypicker'] = FontFamilyPickerUserValueWidget;
options.userValueWidgetsRegistry['we-gpspicker'] = GPSPicker;
*/

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

patch(SnippetOption.prototype, {
    specialCheckAndReloadMethodsNames: [
        'customizeWebsiteViews',
        'customizeWebsiteVariable',
        'customizeWebsiteColor',
        'customizeWebsiteLayer2Color',
    ],

    /**
     * @override
     */
    constructorPatch() {
        super.constructorPatch(...arguments);
        // Since the website is displayed in an iframe, its jQuery
        // instance is not the same as the editor. This property allows
        // for easy access to bootstrap plugins (Carousel, Modal, ...).
        // This is only needed because jQuery doesn't send custom events
        // the same way native javascript does. So if a jQuery instance
        // triggers a custom event, only that same jQuery instance will
        // trigger handlers set with `.on`.
        this.$bsTarget = this.ownerDocument.defaultView.$(this.$target[0]);
    },

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
    customizeWebsiteVariables: async function (previewMode, widgetValue, params) {
        await this._customizeWebsite(previewMode, widgetValue, params, 'variables');
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
        const needReload = await super._checkIfWidgetsUpdateNeedReload(...arguments);
        if (needReload) {
            return needReload;
        }
        for (const widget of widgets) {
            const methodsNames = widget.getMethodsNames();
            const methodNamesToCheck = this.data.pageOptions
                ? methodsNames
                : methodsNames.filter(m => this.specialCheckAndReloadMethodsNames.includes(m));
            if (methodNamesToCheck.some(m => widget.getMethodsParams(m).reload)) {
                return true;
            }
        }
        return false;
    },
    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'customizeWebsiteViews': {
                return this._getEnabledCustomizeValues(params.possibleValues, true);
            }
            case 'customizeWebsiteVariable': {
                const ownerDocument = this.$target[0].ownerDocument;
                const style = ownerDocument.defaultView.getComputedStyle(ownerDocument.documentElement);
                let finalValue = weUtils.getCSSVariableValue(params.variable, style);
                if (!params.colorNames) {
                    return finalValue;
                }
                let tempValue = finalValue;
                while (tempValue) {
                    finalValue = tempValue;
                    tempValue = weUtils.getCSSVariableValue(tempValue.replaceAll("'", ''), style);
                }
                return finalValue;
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
        return super._computeWidgetState(...arguments);
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
            case "variables":
                const defaultVariables = params.defaultVariables ?
                    Object.fromEntries(params.defaultVariables.split(",")
                        .map((variable) => variable.split(":").map(v => v.trim()))) :
                    {};
                const overriddenVariables = Object.fromEntries(widgetValue.split(",")
                    .map((variable) => variable.split(":").map(v => v.trim())));
                const variables = Object.assign(defaultVariables, overriddenVariables);
                await this._customizeWebsiteVariables(variables, params.nullValue);
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
        await this._refreshBundles();
    },
    /**
     * @private
     */
    async _refreshBundles() {
        // Finally, only update the bundles as no reload is required
        await this._reloadBundles();

        // Some public widgets may depend on the variables that were
        // customized, so we have to restart them *all*.
        await new Promise((resolve, reject) => {
            this.env.services.website.websiteRootInstance.trigger_up("widgets_start_request", {
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
                } else if (!isCSSColor(color)) {
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
     * Customizes several website variables at the same time.
     *
     * @private
     * @param {Object} values: value per key variable
     * @param {string} nullValue: string that represent null
     */
    _customizeWebsiteVariables: async function (values, nullValue) {
        await this._makeSCSSCusto('/website/static/src/scss/options/user_values.scss', values, nullValue);
        await this._refreshBundles();
    },
    /**
     * @private
     */
    async _customizeWebsiteData(value, params, isViewData) {
        const allDataKeys = this._getDataKeysFromPossibleValues(params.possibleValues);
        const keysToEnable = value.split(/\s*,\s*/);
        const enableDataKeys = allDataKeys.filter(value => keysToEnable.includes(value));
        const disableDataKeys = allDataKeys.filter(value => !enableDataKeys.includes(value));
        const resetViewArch = !!params.resetViewArch;

        return rpc('/website/theme_customize_data', {
            'is_view_data': isViewData,
            'enable': enableDataKeys,
            'disable': disableDataKeys,
            'reset_view_arch': resetViewArch,
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
        // return only unique non-empty strings
        return allDataKeys.filter((v, i, arr) => v && arr.indexOf(v) === i);
    },
    /**
     * @private
     * @param {Array} possibleValues
     * @param {Boolean} isViewData true = "ir.ui.view", false = "ir.asset"
     * @returns {String}
     */
    async _getEnabledCustomizeValues(possibleValues, isViewData) {
        const allDataKeys = this._getDataKeysFromPossibleValues(possibleValues);
        const enabledValues = await rpc('/website/theme_customize_data_get', {
            'keys': allDataKeys,
            'is_view_data': isViewData,
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
        Object.keys(values).forEach((key) => {
            values[key] = values[key] || defaultValue;
        });
        return this.env.services.orm.call("web_editor.assets", "make_scss_customization", [url, values]);
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
            this.env.services.website.websiteRootInstance?.trigger_up('widgets_start_request', {
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
            this.env.reloadBundles({
                onSuccess: () => resolve(),
                onFailure: () => reject(),
            });
        });
    },
    /**
     * @override
     */
    async _select(previewMode, widget) {
        await super._select(...arguments);

        // Some blocks flicker when we start their public widgets, so we skip
        // the refresh for them to avoid the flickering.
        const targetNoRefreshSelector = ".s_instagram_page";
        // TODO: we should review the way public widgets are restarted when
        // converting to OWL and a new API.
        if (this.options.isWebsite && widget._methodsParams.noWidgetRefresh !== "true"
            && !this.$target[0].matches(targetNoRefreshSelector)) {
            // TODO the flag should be retrieved through widget params somehow
            await this._refreshPublicWidgets();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * TODO: @owl-options update doc
     * @param {Object}
     */
    _onFontsCustoRequest({values, googleFonts, googleLocalFonts, uploadedLocalFonts}) {
        values = values ? Object.assign({}, values) : {};
        if (googleFonts.length) {
            values['google-fonts'] = "('" + googleFonts.join("', '") + "')";
        } else {
            values['google-fonts'] = 'null';
        }
        if (googleLocalFonts.length) {
            values['google-local-fonts'] = "(" + googleLocalFonts.join(", ") + ")";
        } else {
            values['google-local-fonts'] = 'null';
        }
        if (uploadedLocalFonts.length) {
            values['uploaded-local-fonts'] = "(" + uploadedLocalFonts.join(", ") + ")";
        } else {
            values['uploaded-local-fonts'] = 'null';
        }
        this.options.snippetEditionRequest({exec: async () => {
            return this._makeSCSSCusto('/website/static/src/scss/options/user_values.scss', values);
        }});
        this.env.requestSave({
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

patch(BackgroundToggler.prototype, {
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
            const bgVideoOpt = bgVideoWidget.option;
            return bgVideoOpt._setBgVideo(false, '');
        } else {
            // TODO: use trigger instead of el.click when possible
            this._requestUserValueWidgets('bg_video_opt')[0].enable();
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
        return super._computeWidgetState(...arguments);
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
        return super._getLastPreFilterLayerElement(...arguments);
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

patch(ReplaceMedia.prototype, {
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
        return super._computeWidgetState(...arguments);
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
        return super._computeWidgetVisibility(...arguments);
    },
});

class BackgroundVideo extends SnippetOption {

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Sets the target's background video.
     *
     * @see this.selectClass for parameters
     */
    background(previewMode, widgetValue, params) {
        if (previewMode === 'reset' && this.videoSrc) {
            return this._setBgVideo(false, this.videoSrc);
        }
        return this._setBgVideo(previewMode, widgetValue);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === 'background') {
            if (this.$target[0].classList.contains('o_background_video')) {
                return this.$('> .o_bg_video_container iframe').attr('src');
            }
            return '';
        }
        return this._super(...arguments);
    }
    /**
     * Updates the background video used by the snippet.
     *
     * @private
     * @see this.selectClass for parameters
     * @returns {Promise}
     */
    async _setBgVideo(previewMode, value) {
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
    }
}

export class WebsiteLevelColor extends SnippetOption {
    /**
     * @constructor
     */
    constructor() {
        super(...arguments);
        this._rpc = options.serviceCached(rpc);
    }
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
    }

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
        return super._computeWidgetState(...arguments);
    }
    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        if (
            [
                "footer_language_selector_label_opt",
                "footer_language_selector_opt",
            ].includes(widgetName)
        ) {
            this._languages = await this._rpc.call("/website/get_languages");
            if (this._languages.length === 1) {
                return false;
            }
        }
        return super._computeWidgetVisibility(...arguments);
    }
}

registerWebsiteOption("Header", {
    Class: WebsiteLevelColor,
    template: "website.header_option",
    selector: "#wrapwrap > header",
    noCheck: true,
    data: {
        groups: ["website.group_website_designer"],
    },
});

registerWebsiteOption("Footer", {
    Class: WebsiteLevelColor,
    template: "website.footer_option",
    selector: "#wrapwrap > footer",
    noCheck: true,
    data: {
        groups: ["website.group_website_designer"],
    },
});

registerWebsiteOption("Footer Copyright", {
    Class: WebsiteLevelColor,
    template: "website.footer_copyright_option",
    selector: ".o_footer_copyright",
    noCheck: true,
    data: {
        groups: ["website.group_website_designer"],
    },
});

export class OptionsTab extends WebsiteLevelColor {
    static GRAY_PARAMS = {EXTRA_SATURATION: "gray-extra-saturation", HUE: "gray-hue"};

    /**
     * @override
     */
    constructor() {
        super(...arguments);
        this.grayParams = {};
        this.grays = {};
    }

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

        // If the gray palette has been generated by Odoo standard option,
        // the hue of all gray is the same and the saturation has been
        // increased/decreased by the same amount for all grays in
        // comparaison with BS grays. However the system supports any
        // gray palette.

        const hues = [];
        const saturationDiffs = [];
        let oneHasNoSaturation = false;
        const baseStyle = getComputedStyle(document.documentElement);
        for (let id = 100; id <= 900; id += 100) {
            const gray = weUtils.getCSSVariableValue(`${id}`, style);
            const grayRGB = convertCSSColorToRgba(gray);
            const grayHSL = convertRgbToHsl(grayRGB.red, grayRGB.green, grayRGB.blue);

            const baseGray = weUtils.getCSSVariableValue(`base-${id}`, baseStyle);
            const baseGrayRGB = convertCSSColorToRgba(baseGray);
            const baseGrayHSL = convertRgbToHsl(baseGrayRGB.red, baseGrayRGB.green, baseGrayRGB.blue);

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
        this.grayParams[OptionsTab.GRAY_PARAMS.HUE] = (!hues.length) ? 0 : Math.round((Math.atan2(
            hues.map(hue => Math.sin(hue * Math.PI / 180)).reduce((memo, value) => memo + value, 0) / hues.length,
            hues.map(hue => Math.cos(hue * Math.PI / 180)).reduce((memo, value) => memo + value, 0) / hues.length
        ) * 180 / Math.PI) + 360) % 360;

        // Average of found saturation diffs, or all grays have no
        // saturation, or all grays are fully saturated.
        this.grayParams[OptionsTab.GRAY_PARAMS.EXTRA_SATURATION] = saturationDiffs.length
            ? saturationDiffs.reduce((memo, value) => memo + value, 0) / saturationDiffs.length
            : (oneHasNoSaturation ? -100 : 100);

        await super.updateUI(...arguments);
    }

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

        // Save all computed (JS side) grays in database
        await this._customizeWebsite(previewMode, undefined, Object.assign({}, params, {
            customCustomization: () => { // TODO this could be prettier
                return this._customizeWebsiteColors(this.grays, Object.assign({}, params, {
                    colorType: 'gray',
                }));
            },
        }));
    }
    /**
     * @see this.selectClass for parameters
     */
    async configureApiKey(previewMode, widgetValue, params) {
        return new Promise(resolve => {
            this.env.gmapApiKeyRequest({
                editableMode: true,
                reconfigure: true,
                onSuccess: () => resolve(),
            });
        });
    }
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
    }
    /**
     * @override
     */
    async customizeBodyBg(previewMode, widgetValue, params) {
        await this._customizeWebsiteVariables({
            'body-image-type': this.bodyImageType,
            'body-image': widgetValue ? `'${widgetValue}'` : '',
        }, params.nullValue);
    }
    async openCustomCodeDialog(previewMode, widgetValue, params) {
        return new Promise(resolve => {
            this.options.wysiwyg._onOpenEditHeadBodyDialog({
                data: {onSuccess: resolve},
            });
        });
    }
    /**
     * @see this.selectClass for parameters
     */
    async switchTheme(previewMode, widgetValue, params) {
        const save = await new Promise(resolve => {
            this.dialog.add(ConfirmationDialog, {
                body: _t("Changing theme requires to leave the editor. This will save all your changes, are you sure you want to proceed? Be careful that changing the theme will reset all your color customizations."),
                confirm: () => resolve(true),
                cancel: () => resolve(false),
            });
        });
        if (!save) {
            return;
        }
        this.env.requestSave({
            reload: false,
            action: 'website.theme_install_kanban_action',
        });
    }
    /**
     * @see this.selectClass for parameters
     */
    async addLanguage(previewMode, widgetValue, params) {
        // Retrieve the website id to check by default the website checkbox in
        // the dialog box 'action_view_base_language_install'
        const websiteId = this.options.context.website_id;
        const save = await new Promise((resolve) => {
            this.dialog.add(ConfirmationDialog, {
                body: _t("Adding a language requires to leave the editor. This will save all your changes, are you sure you want to proceed?"),
                confirm: () => resolve(true),
                cancel: () => resolve(false),
            });
        });
        if (!save) {
            return;
        }
        this.env.requestSave({
            reload: false,
            action: "base.action_view_base_language_install",
            options: {
                additionalContext: {
                    params: {
                        website_id: websiteId,
                        url_return: "[lang]",
                    }
                },
            }
        });
    }
    /**
     * @see this.selectClass for parameters
     */
    async customizeButtonStyle(previewMode, widgetValue, params) {
        await this._customizeWebsiteVariables({
            [`btn-${params.button}-outline`]: widgetValue === "outline" ? "true" : "false",
            [`btn-${params.button}-flat`]: widgetValue === "flat" ? "true" : "false",
        }, params.nullValue);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {String} id
     * @returns {String} the adjusted color of gray
     */
    _buildGray(id) {
        // Getting base grays defined in color_palette.scss
        const gray = weUtils.getCSSVariableValue(`base-${id}`, getComputedStyle(document.documentElement));
        const grayRGB = convertCSSColorToRgba(gray);
        const hsl = convertRgbToHsl(grayRGB.red, grayRGB.green, grayRGB.blue);
        const adjustedGrayRGB = convertHslToRgb(this.grayParams[OptionsTab.GRAY_PARAMS.HUE],
            Math.min(Math.max(hsl.saturation + this.grayParams[OptionsTab.GRAY_PARAMS.EXTRA_SATURATION], 0), 100),
            hsl.lightness);
        return convertRgbaToCSSColor(adjustedGrayRGB.red, adjustedGrayRGB.green, adjustedGrayRGB.blue);
    }
    /**
     * @override
     */
    async _getRenderContext() {
        const context = await super._getRenderContext(...arguments);
        this._updateRenderContext(context);
        return context;
    }
    _updateRenderContext(context) {
        context = context || this.renderContext;
        context.grays = this.grays;
        const baseGrays = range(100, 1000, 100).map(id => {
            const gray = weUtils.getCSSVariableValue(`base-${id}`);
            const grayRGB = convertCSSColorToRgba(gray);
            const hsl = convertRgbToHsl(grayRGB.red, grayRGB.green, grayRGB.blue);
            return {id: id, hsl: hsl};
        });
        const first = baseGrays[0];
        const maxValue = baseGrays.reduce((gray, value) => {
            return gray.hsl.saturation > value.hsl.saturation ? gray : value;
        }, first);
        const minValue = baseGrays.reduce((gray, value) => {
            return gray.hsl.saturation < value.hsl.saturation ? gray : value;
        }, first);
        context.extraSaturationRangeMax = 100 - minValue.hsl.saturation;
        context.extraSaturationRangeMin = -maxValue.hsl.saturation;
        return context;
    }
    /**
     * @override
     */
    async _renderCustomXML(uiFragment) {
        await super._renderCustomXML(...arguments);
        this._updateRenderContext();
    }
    /**
     * @override
     */
    async _checkIfWidgetsUpdateNeedWarning(widgets) {
        const warningMessage = await super._checkIfWidgetsUpdateNeedWarning(...arguments);
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
    }
    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName === 'customizeBodyBgType') {
            const bgImage = getComputedStyle(this.ownerDocument.querySelector('#wrapwrap'))['background-image'];
            if (bgImage === 'none') {
                return "NONE";
            }
            return weUtils.getCSSVariableValue('body-image-type');
        }
        if (methodName === 'customizeGray') {
            // See updateUI override
            return this.grayParams[params.param];
        }
        if (methodName === 'customizeButtonStyle') {
            const isOutline = weUtils.getCSSVariableValue(`btn-${params.button}-outline`);
            const isFlat = weUtils.getCSSVariableValue(`btn-${params.button}-flat`);
            return isFlat === "true" ? "flat" : isOutline === "true" ? "outline" : "fill";
        }
        return super._computeWidgetState(...arguments);
    }
    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'body_bg_image_opt') {
            return false;
        }
        if (params.param === OptionsTab.GRAY_PARAMS.HUE) {
            return this.grayHueIsDefined;
        }
        if (params.removeFont) {
            const font = await this._computeWidgetState('customizeWebsiteVariable', {
                variable: params.removeFont,
            });
            return !!font;
        }
        return super._computeWidgetVisibility(...arguments);
    }
}

export class ThemeColors extends OptionsTab {
    /**
     * @override
     */
    async willStart() {
        // Checks for support of the old color system
        const style = window.getComputedStyle(this.$target[0].ownerDocument.documentElement);
        const supportOldColorSystem = weUtils.getCSSVariableValue('support-13-0-color-system', style) === 'true';
        const hasCustomizedOldColorSystem = weUtils.getCSSVariableValue('has-customized-13-0-color-system', style) === 'true';
        this._showOldColorSystemWarning = supportOldColorSystem && hasCustomizedOldColorSystem;

        return super.willStart(...arguments);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _getRenderContext() {
        const context = await super._getRenderContext(...arguments);
        context.showOldColorSystemWarning = this._showOldColorSystemWarning;

        // Prepare palette colors
        const style = window.getComputedStyle(document.documentElement);
        const allPaletteNames = weUtils.getCSSVariableValue('palette-names', style).split(', ').map((name) => {
            return name.replace(/'/g, "");
        });
        context.palettes = allPaletteNames.map((paletteName) => {
            return {
                name: paletteName,
                colors: [1, 3, 2].map((c) => {
                    return weUtils.getCSSVariableValue(`o-palette-${paletteName}-o-color-${c}`, style);
                }),
            };
        });
        return context;
    }
}

registerWebsiteOption("ThemeColors", {
    Class: ThemeColors,
    template: "website.theme_colors_option",
    selector: "theme-colors",
    noCheck: true,
});
registerWebsiteOption("Theme Settings", {
    Class: OptionsTab,
    template: "website.theme_settings_option",
    selector: "website-settings",
    noCheck: true,
});
registerWebsiteOption("Theme Paragraph", {
    Class: OptionsTab,
    template: "website.theme_paragraph_option",
    selector: "theme-paragraph",
    noCheck: true,
});
registerWebsiteOption("Theme Headings", {
    Class: OptionsTab,
    template: "website.theme_headings_option",
    selector: "theme-headings",
    noCheck: true,
});
registerWebsiteOption("Theme Button", {
    Class: OptionsTab,
    template: "website.theme_button_option",
    selector: "theme-button",
    noCheck: true,
});
registerWebsiteOption("Theme Link", {
    Class: OptionsTab,
    template: "website.theme_link_option",
    selector: "theme-link",
    noCheck: true,
});
registerWebsiteOption("Theme Input", {
    Class: OptionsTab,
    template: "website.theme_input_option",
    selector: "theme-input",
    noCheck: true,
});
registerWebsiteOption("Theme Advanced", {
    Class: OptionsTab,
    template: "website.theme_advanced_option",
    selector: "theme-advanced",
    noCheck: true,
});

export class MenuElementOverlay extends SnippetOption {
    constructor() {
        super(...arguments);
        this.notification = this.env.services.notification;
        this.orm = this.env.services.orm;
        this.website = this.env.services.website;
    }

    /**
     * When the users selects a menu, a popover is shown with 4 possible
     * actions: follow the link in a new tab, copy the menu link, edit the menu,
     * or edit the menu tree.
     * The popover shows a preview of the menu link. Remote URL only show the
     * favicon.
     *
     * @override
     */
    async willStart() {
        const popoverContainer = this.ownerDocument.getElementById('oe_manipulators');
        NavbarLinkPopoverWidget.createFor({
            target: this.$target[0],
            wysiwyg: this.options.wysiwyg,
            container: popoverContainer,
            notify: this.notification.add,
            checkIsWebsiteDesigner: () => user.hasGroup("website.group_website_designer"),
            onEditLinkClick: (widget) => {
                var $menu = widget.$target.find('[data-oe-id]');
                this.options.wysiwyg.openMenuDialog(
                    $menu.text(),
                    $menu.parent().attr('href'),
                    (name, url) => {
                        const websiteId = this.website.currentWebsite.id;
                        const data = {
                            id: $menu.data('oe-id'),
                            name,
                            url,
                        };
                        return this.orm.call(
                            "website.menu",
                            "save",
                            [websiteId, {'data': [data]}]
                        ).then(() => {
                            this.options.wysiwyg.odooEditor.observerUnactive();
                            widget.$target.attr('href', url);
                            $menu.text(name);
                            this.options.wysiwyg.odooEditor.observerActive();
                        });
                    },
                );
                widget.popover.hide();
            },
            onEditMenuClick: (widget) => {
                const contentMenu = widget.target.closest('[data-content_menu_id]');
                const rootID = contentMenu ? parseInt(contentMenu.dataset.content_menu_id, 10) : undefined;
                this.options.wysiwyg.openEditMenuDialog(rootID);
            },
        });
        return super.willStart(...arguments);
    }
    /**
      * When the users selects another element on the page, makes sure the
      * popover is closed.
      *
      * @override
      */
    async onBlur() {
        this.$target.popover('hide');
    }
}

registerWebsiteOption("MenuElementOverlay", {
    Class: MenuElementOverlay,
    selector: ".top_menu li > a, [data-content_menu_id] li > a",
    exclude: ".dropdown-toggle, li.o_header_menu_button a, [data-toggle], .o_offcanvas_logo",
    noCheck: true,
});

class Carousel extends CarouselHandler {
    /**
     * @override
     */
    constructor() {
        super(...arguments);

        this.$bsTarget.carousel('pause');
        this.$indicators = this.$target.find('.carousel-indicators');
        this.$controls = this.$target.find('.carousel-control-prev, .carousel-control-next, .carousel-indicators');

        // Prevent enabling the carousel overlay when clicking on the carousel
        // controls (indeed we want it to change the carousel slide then enable
        // the slide overlay) + See "CarouselItem" option.
        this.$controls.addClass('o_we_no_overlay');

        let _slideTimestamp;
        this.$bsTarget.on('slide.bs.carousel.carousel_option', () => {
            _slideTimestamp = window.performance.now();
            setTimeout(() => this.env.hideOverlay());
        });
        this.$bsTarget.on('slid.bs.carousel.carousel_option', () => {
            // slid.bs.carousel is most of the time fired too soon by bootstrap
            // since it emulates the transitionEnd with a setTimeout. We wait
            // here an extra 20% of the time before retargeting edition, which
            // should be enough...
            const _slideDuration = (window.performance.now() - _slideTimestamp);
            setTimeout(() => {
                this.env.activateSnippet(this.$target.find('.carousel-item.active'), false, true);
                this.$bsTarget.trigger('active_slide_targeted');
            }, 0.2 * _slideDuration);
        });
    }
    /**
     * @override
     */
    destroy() {
        super.destroy(...arguments);
        this.$bsTarget.off('.carousel_option');
    }
    /**
     * @override
     */
    onBuilt() {
        this._assignUniqueID();
    }
    /**
     * @override
     */
    onClone() {
        this._assignUniqueID();
    }
    /**
     * @override
     */
    // TODO: @owl-options check if this should be cleanUI() rather than cleanForSave()
    cleanUI() {
        const $items = this.$target.find('.carousel-item');
        $items.removeClass('next prev left right active').first().addClass('active');
        this.$indicators.find('li').removeClass('active').empty().first().addClass('active');
    }
    /**
     * @override
     */
    notify(name, data) {
        super.notify(...arguments);
        if (name === 'add_slide') {
            this._addSlide();
        }
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    addSlide(previewMode, widgetValue, params) {
        this._addSlide();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Creates a unique ID for the carousel and reassign data-attributes that
     * depend on it.
     *
     * @private
     */
    _assignUniqueID() {
        const id = 'myCarousel' + Date.now();
        this.$target.attr('id', id);
        this.$target.find('[data-bs-target]').attr('data-bs-target', '#' + id);
        this.$target.find('[data-bs-slide], [data-bs-slide-to]').toArray().forEach((el) => {
            var $el = $(el);
            if ($el.attr('data-bs-target')) {
                $el.attr('data-bs-target', '#' + id);
            } else if ($el.attr('href')) {
                $el.attr('href', '#' + id);
            }
        });
    }
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
        this.$bsTarget.carousel('next');
    }
    /**
     * @override
     */
    _getItemsGallery() {
        return Array.from(this.$target[0].querySelectorAll(".carousel-item"));
    }
    /**
     * @override
     */
    _reorderItems(itemsEls, newItemPosition) {
        const carouselInnerEl = this.$target[0].querySelector(".carousel-inner");
        // First, empty the content of the carousel.
        carouselInnerEl.replaceChildren();
        // Then fill it with the new slides.
        for (const itemsEl of itemsEls) {
            carouselInnerEl.append(itemsEl);
        }
        this._updateIndicatorAndActivateSnippet(newItemPosition);
    }
}
registerWebsiteOption("Carousel", {
    Class: Carousel,
    template: "website.Carousel",
    selector: "section",
    target: "> .carousel",
});

class CarouselItem extends SnippetOption {
    static isTopOption = true;
    static forceNoDeleteButton = true;

    /**
     * @override
     */
    constructor() {
        super(...arguments);

        this.$carousel = this.$bsTarget.closest('.carousel');
        this.$indicators = this.$carousel.find('.carousel-indicators');
        this.$controls = this.$carousel.find('.carousel-control-prev, .carousel-control-next, .carousel-indicators');
    }
    /**
     * @override
     */
    destroy() {
        super.destroy(...arguments);
        this.$carousel.off('.carousel_item_option');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Updates the slide counter.
     *
     * @override
     */
    async updateUI() {
        await super.updateUI(...arguments);
        const $items = this.$carousel.find('.carousel-item');
        const $activeSlide = $items.filter('.active');
        // TODO: @owl-options: block the editor UI until the new options are
        // created.
        this.callbacks.updateExtraTitle(` (${$activeSlide.index() + 1}/${$items.length})`);
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    addSlideItem(previewMode, widgetValue, params) {
        this.callbacks.notifyOptions({
            optionName: 'Carousel',
            name: 'add_slide',
        });
    }
    /**
     * Removes the current slide.
     *
     * @see this.selectClass for parameters.
     */
    removeSlide(previewMode) {
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
                    indicatorsEls[i].setAttribute('data-bs-slide-to', i);
                }
                this.$controls.toggleClass('d-none', newLength === 1);
                this.$carousel.trigger('content_changed');
                this.removing = false;
            });
            this.removing = true;
            this.$carousel.carousel('prev');
        }
    }
    /**
     * Goes to next slide or previous slide.
     *
     * @see this.selectClass for parameters
     */
    switchToSlide(previewMode, widgetValue, params) {
        switch (widgetValue) {
            case 'left':
                this.$controls.filter('.carousel-control-prev')[0].click();
                break;
            case 'right':
                this.$controls.filter('.carousel-control-next')[0].click();
                break;
        }
    }
}
registerWebsiteOption("CarouselItem", {
    Class: CarouselItem,
    template: "website.CarouselItem",
    selector: ".s_carousel .carousel-item, .s_quotes_carousel .carousel-item",
});

class Parallax extends SnippetOption {
    /**
     * @override
     */
    async willStart() {
        this.parallaxEl = this.$target.find('> .s_parallax_bg')[0] || null;
        // Delay the notify that changes the target because options that handle
        // the target might not be initialized yet.
        this.env.snippetEditionRequest(() => {
            this._updateBackgroundOptions();
        });

        this.$target.on('content_changed.ParallaxOption', this._onExternalUpdate.bind(this));

        return super.willStart(...arguments);
    }
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
    }
    /**
     * @override
     */
    onMove() {
        this._refreshPublicWidgets();
    }
    /**
     * @override
     */
    destroy() {
        super.destroy();
        this.$target.off('.ParallaxOption');
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Build/remove parallax.
     *
     * @see this.selectClass for parameters
     */
    async selectDataAttribute(previewMode, widgetValue, params) {
        await super.selectDataAttribute(...arguments);
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
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeVisibility(widgetName) {
        return !this.$target.hasClass('o_background_video');
    }
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
        return super._computeWidgetState(...arguments);
    }
    /**
     * Updates external background-related option to work with the parallax
     * element instead of the original target when necessary.
     *
     * @private
     */
    _updateBackgroundOptions() {
        this.callbacks.notifyOptions({
            optionNames: ['BackgroundImage', 'BackgroundPosition', 'BackgroundOptimize'],
            name: 'target',
            data: this.parallaxEl ? $(this.parallaxEl) : this.$target,
        });
    }

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
    }
}

export class BSCollapse extends SnippetOption {
    /**
     * @override
     */
    async willStart() {
        var self = this;
        this.$bsTarget.on('shown.bs.collapse hidden.bs.collapse', '[role="region"]', function () {
            self.callbacks.coverUpdate();
            self.$target.trigger('content_changed');
        });
        return super.willStart(...arguments);
    }
    /**
     * @override
     */
    onBuilt() {
        this._createIDs();
    }
    /**
     * @override
     */
    onClone() {
        this._createIDs();
    }
    /**
     * @override
     */
    onMove() {
        this._createIDs();
        var $panel = this.$bsTarget.find('.collapse').removeData('bs.collapse');
        if ($panel.attr('aria-expanded') === 'true') {
            $panel.closest('.accordion').find('.collapse[aria-expanded="true"]')
                .filter((i, el) => (el !== $panel[0]))
                .collapse('hide')
                .one('hidden.bs.collapse', function () {
                    $panel.trigger('shown.bs.collapse');
                });
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Associates unique ids on collapse elements.
     *
     * @private
     */
    _createIDs() {
        let time = new Date().getTime();
        const accordionEl = this.$target[0].closest(".accordion");
        const accordionBtnEl = this.$target[0].querySelector(".accordion-button");
        const accordionContentEl = this.$target[0].querySelector('[role="region"]');
        const $body = this.$target.closest('body');

        const setUniqueId = (el, label) => {
            let elemId = el.id;
            if (!elemId || $body.find('[id="' + elemId + '"]').length > 1) {
                do {
                    time++;
                    elemId = label + time;
                } while ($body.find('#' + elemId).length);
                el.id = elemId;
            }
            return elemId;
        };

        const accordionId = setUniqueId(accordionEl, "myCollapse");
        accordionContentEl.dataset.bsParent = "#" + accordionId;
        
        const contentId = setUniqueId(accordionContentEl, "myCollapseTab");
        accordionBtnEl.dataset.bsTarget = "#" + contentId;
        accordionBtnEl.setAttribute("aria-controls", contentId);

        const buttonId = setUniqueId(accordionBtnEl, "myCollapseBtn");
        accordionContentEl.setAttribute("aria-labelledby", buttonId);
    }
}

registerWebsiteOption("Accordion", {
    Class: BSCollapse,
    selector: ".accordion > .accordion-item",
    dropIn: ".accordion:has(> .accordion-item)",
});

export class HeaderElements extends SnippetOption {
    constructor() {
        super(...arguments);
        this._rpc = options.serviceCached(rpc);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        switch (widgetName) {
            case "header_language_selector_opt":
                this._languages = await this._rpc.call("/website/get_languages");
                if (this._languages.length === 1) {
                    return false;
                }
                break;
        }
        return super._computeWidgetVisibility(...arguments);
    }
}

registerWebsiteOption("HeaderElements", {
    Class: HeaderElements,
    template: "website.HeaderElements",
    selector: "#wrapwrap > header",
    noCheck: true,
    data: {
        groups: ["website.group_website_designer"],
    },
}, {
    sequence: 80,
});

registerWebsiteOption("HeaderScrollEffect", {
    template: "website.HeaderScrollEffect",
    selector: "#wrapwrap > header",
    noCheck: true,
    data: {
        groups: ["website.group_website_designer"],
    },
}, {
    sequence: 50,
});

registerWebsiteOption("HeaderLanguageSelector", {
    template: "website.HeaderLanguageSelector",
    selector: "#wrapwrap > header nav.navbar .o_header_language_selector",
    noCheck: true,
    data: {
        groups: ["website.group_website_designer"],
    },
});

registerWebsiteOption("HeaderBrand", {
    template: "website.HeaderBrand",
    selector: "#wrapwrap > header nav.navbar .navbar-brand",
    noCheck: true,
    data: {
        groups: ["website.group_website_designer"],
    },
});

export class HeaderNavbar extends SnippetOption {
    /**
     * Particular case: we want the option to be associated on the header navbar
     * in XML so that the related options only appear on navbar click (not
     * header), in a different section, etc... but we still want the target to
     * be the header itself.
     */
    constructor() {
        super(...arguments);
        this.setTarget(this.$target.closest('#wrapwrap > header'));
    }

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
                return !!this.$('.navbar-brand').length;
            }
        }
        return super._computeWidgetVisibility(...arguments);
    }
}

registerWebsiteOption("HeaderNavbar", {
    Class: HeaderNavbar,
    template: "website.HeaderNavbar",
    selector: "#wrapwrap > header nav.navbar",
    noCheck: true,
    data: {
        groups: ["website.group_website_designer"],
    },
});

/**
 * @abstract
 */
export class VisibilityPageOptionUpdate extends SnippetOption {
    /**
     * @abstract
     * @type {string}
     */
    static pageOptionName = undefined;

    constructor({ callbacks, options }) {
        super(...arguments);
        this.requestUserValue = callbacks.requestUserValue;
        this.updateSnippetOptionVisibility = callbacks.updateSnippetOptionVisibility;
        this.wysiwyg = options.wysiwyg;
        this.shownValue = "";
    }

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
        await this.visibility(this.shownValue);
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for params
     */
    async visibility(previewMode, widgetValue, params) {
        const show = (widgetValue !== 'hidden');
        await this.wysiwyg.togglePageOption(this.constructor.pageOptionName, show);
        this.updateSnippetOptionVisibility(show);
    }

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
    }
    /**
     * @private
     * @returns {Promise<boolean>}
     */
    async _isShown() {
        return await this.wysiwyg.getPageOption(this.constructor.pageOptionName);
    }
}

export class TopMenuVisibility extends VisibilityPageOptionUpdate {
    /**
     * @override
     */
    static pageOptionName = "header_visible";

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Handles the switching between 3 differents visibilities of the header.
     *
     * @see this.selectClass for params
     */
    async visibility(previewMode, widgetValue, params) {
        await super.visibility(...arguments);
        await this._changeVisibility(widgetValue);
        // TODO this is hacky but changing the header visibility may have an
        // effect on features like FullScreenHeight which depend on viewport
        // size so we simulate a resize.
        const targetWindow = this.$target[0].ownerDocument.defaultView;
        targetWindow.dispatchEvent(new targetWindow.Event('resize'));
    }

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
        await this.wysiwyg.togglePageOption("header_overlay", transparent);
        if (!transparent) {
            return;
        }
        await this.wysiwyg.togglePageOption("header_color", "");
        await this.wysiwyg.togglePageOption("header_text_color", "");
    }
    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName === 'visibility') {
            const pageHeaderOverlay = await this.wysiwyg.getPageOption("header_overlay");
            this.shownValue = pageHeaderOverlay ? "transparent" : "regular";
        }
        return super._computeWidgetState(...arguments);
    }
}
registerWebsiteOption("TopMenuVisibility", {
    Class: TopMenuVisibility,
    template: "website.TopMenuVisibility",
    selector: "[data-main-object^='website.page('] #wrapwrap > header",
    noCheck: true,
}, {
    sequence: 60,
});

export class TopMenuColor extends SnippetOption {

    constructor({ options }) {
        super(...arguments);
        this.wysiwyg = options.wysiwyg;
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async selectStyle(previewMode, widgetValue, params) {
        await super.selectStyle(...arguments);
        if (widgetValue && !isCSSColor(widgetValue)) {
            widgetValue = params.colorPrefix + widgetValue;
        }
        this.wysiwyg.togglePageOption(params.pageOptionName, widgetValue);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeVisibility() {
        const show = await super._computeVisibility(...arguments);
        if (!show) {
            return false;
        }
        return !!this.wysiwyg.getPageOption("header_overlay");
    }
}

registerWebsiteOption("TopMenuColor", {
    Class: TopMenuColor,
    template: "website.TopMenuColor",
    selector: "[data-main-object^='website.page('] #wrapwrap > header",
    noCheck: true,
}, {
    sequence: 70,
});

/**
 * Manage the visibility of snippets on mobile/desktop.
 */
options.registry.DeviceVisibility = options.Class.extend({});
export class DeviceVisibility extends SnippetOption {
    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Toggles the device visibility.
     *
     * @see this.selectClass for parameters
     */
    async toggleDeviceVisibility(previewMode, widgetValue, params) {
        this.$target[0].classList.remove('d-none', 'd-md-none', 'd-lg-none',
            'o_snippet_mobile_invisible', 'o_snippet_desktop_invisible',
            'o_snippet_override_invisible',
        );
        const style = getComputedStyle(this.$target[0]);
        this.$target[0].classList.remove(`d-md-${style['display']}`, `d-lg-${style['display']}`);
        if (widgetValue === 'no_desktop') {
            this.$target[0].classList.add('d-lg-none', 'o_snippet_desktop_invisible');
        } else if (widgetValue === 'no_mobile') {
            this.$target[0].classList.add(`d-lg-${style['display']}`, 'd-none', 'o_snippet_mobile_invisible');
        }

        // Update invisible elements.
        const isMobile = wUtils.isMobile(this);
        this.callbacks.updateSnippetOptionVisibility(widgetValue !== (isMobile ? 'no_mobile' : 'no_desktop'));
    }
    /**
     * @override
     */
    async onTargetHide() {
        this.$target[0].classList.remove('o_snippet_override_invisible');
    }
    /**
     * @override
     */
    async onTargetShow() {
        const isMobilePreview = weUtils.isMobileView(this.$target[0]);
        const isMobileHidden = this.$target[0].classList.contains("o_snippet_mobile_invisible");
        if ((this.$target[0].classList.contains('o_snippet_mobile_invisible')
                || this.$target[0].classList.contains('o_snippet_desktop_invisible')
            ) && isMobilePreview === isMobileHidden) {
            this.$target[0].classList.add('o_snippet_override_invisible');
        }
    }
    /**
     * @override
     */
    cleanForSave() {
        this.$target[0].classList.remove('o_snippet_override_invisible');
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName === 'toggleDeviceVisibility') {
            const classList = [...this.$target[0].classList];
            if (classList.includes('d-none') &&
                    classList.some(className => className.match(/^d-(md|lg)-/))) {
                return 'no_mobile';
            }
            if (classList.some(className => className.match(/d-(md|lg)-none/))) {
                return 'no_desktop';
            }
            return '';
        }
        return await super._computeWidgetState(...arguments);
    }
    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        if (this.$target[0].classList.contains('s_table_of_content_main')) {
            return false;
        }
        return super._computeWidgetVisibility(...arguments);
    }
}
registerWebsiteOption("DeviceVisibility", {
    Class: DeviceVisibility,
    template: "website.DeviceVisibility",
    selector: "section .row > div",
    exclude: ".s_col_no_resize.row > div, .s_masonry_block .s_col_no_resize",
});

/**
 * Hide/show footer in the current page.
 */
export class HideFooter extends VisibilityPageOptionUpdate {
    /**
     * @override
     */
    static pageOptionName = "footer_visible";

    constructor() {
        super(...arguments);
        this.shownValue = "shown";
    }
}
registerWebsiteOption("HideFooter", {
    Class: HideFooter,
    template: "website.HideFooter",
    selector: "[data-main-object^='website.page('] #wrapwrap > footer",
    noCheck: true,
    data: {
        groups: ["website.group_website_designer"],
    },
});

registerWebsiteOption("FooterScrolltop", {
    template: "website.FooterScrolltop",
    selector: "#wrapwrap > footer",
    noCheck: true,
    data: {
        groups: ["website.group_website_designer"],
    },
});

/**
 * Handles the edition of snippet's anchor name.
 */
export class Anchor extends SnippetOption {
    /**
     * @override
     */
    static isTopOption = true;

    constructor() {
        super(...arguments);
        this.notification = this.env.services.notification;
    }

    async onBuilt() {
        this.isModal = this.$target[0].classList.contains("modal");
    }

    /**
     * @override
     */
    onClone() {
        this.$target.removeAttr('data-anchor');
        this.$target.filter(':not(.carousel)').removeAttr('id');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    notify(name, data) {
        super.notify(...arguments);
        if (name === "modalAnchor") {
            this._copyAnchorToClipboard();
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    copyAnchorToClipboard() {
        this._copyAnchorToClipboard();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _copyAnchorToClipboard() {
        const anchorLink = this._getAnchorLink();
        browser.navigator.clipboard.writeText(anchorLink).then(() => {
            const message = markup(_t("Anchor copied to clipboard<br>Link: %s", anchorLink));
            this.notification.add(message, {
                type: "success",
                buttons: [{name: _t("Edit"), onClick: () => this._openAnchorDialog(), primary: true}],
            });
        });
    }

    /**
     * @private
     */
    _openAnchorDialog() {
        const anchorDialog = class extends Component {
            static template = "website.dialog.anchorName";
            static props = { close: Function, confirm: Function, delete: Function, currentAnchor: String };
            static components = { Dialog };
            title = _t("Link Anchor");
            modalRef = useChildRef();
            onClickConfirm() {
                const shouldClose = this.props.confirm(this.modalRef);
                if (shouldClose) {
                    this.props.close();
                }
            }
            onClickDelete() {
                this.props.delete();
                this.props.close();
            }
            onClickDiscard() {
                this.props.close();
            }
        };
        const props = {
            confirm: (modalRef) => {
                const inputEl = modalRef.el.querySelector(".o_input_anchor_name");
                const anchorName = this._text2Anchor(inputEl.value);
                if (this.$target[0].id === anchorName) {
                    // If the chosen anchor name is already the one used by the
                    // element, close the dialog and do nothing else
                    return true;
                }

                const alreadyExists = !!this.ownerDocument.getElementById(anchorName);
                modalRef.el.querySelector('.o_anchor_already_exists').classList.toggle('d-none', !alreadyExists);
                inputEl.classList.toggle('is-invalid', alreadyExists);
                if (!alreadyExists) {
                    this._setAnchorName(anchorName);
                    this._copyAnchorToClipboard();
                    return true;
                }
            },
            currentAnchor: decodeURIComponent(this.$target.attr('id')),
        };
        if (this.$target.attr('id')) {
            props["delete"] = () => {
                this._setAnchorName();
            };
        }
        this.dialog.add(anchorDialog, props);
    }
    /**
     * @private
     * @param {String} value
     */
    _setAnchorName(value) {
        if (value) {
            this.$target[0].id = value;
            if (!this.isModal) {
                this.$target[0].dataset.anchor = true;
            }
        } else {
            this.$target.removeAttr('id data-anchor');
        }
        this.$target.trigger('content_changed');
    }
    /**
     * Returns anchor text.
     *
     * @private
     * @returns {string}
     */
    _getAnchorLink() {
        if (!this.$target[0].id) {
            const $titles = this.$target.find('h1, h2, h3, h4, h5, h6');
            const title = $titles.length > 0 ? $titles[0].innerText : this.data.snippetName;
            const anchorName = this._text2Anchor(title);
            let n = '';
            while (this.ownerDocument.getElementById(anchorName + n)) {
                n = (n || 1) + 1;
            }
            this._setAnchorName(anchorName + n);
        }
        const pathName = this.isModal ? "" : this.ownerDocument.location.pathname;
        return `${pathName}#${this.$target[0].id}`;
    }
    /**
     * Creates a safe id/anchor from text.
     *
     * @private
     * @param {string} text
     * @returns {string}
     */
    _text2Anchor(text) {
        return encodeURIComponent(text.trim().replace(/\s+/g, '-'));
    }
}
registerWebsiteOption("Anchor", {
    Class: Anchor,
    template: "website.anchor",
    selector: ":not(p).oe_structure > *, :not(p)[data-oe-type=html] > *",
    exclude: ".modal *, .oe_structure .oe_structure *, [data-oe-type=html] .oe_structure *, .s_popup",
});
registerWebsiteOption("AnchorModal", {
    Class: Anchor,
    selector: ".s_popup",
    target: ".modal",
});

export class HeaderBox extends Box {

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
        return super.selectStyle(...arguments);
    }
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
        return super.setShadow(...arguments);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _getRenderContext() {
        return {
            ...(await super._getRenderContext(...arguments)),
            noBorderRadius: this.$target[0].classList.contains("o_header_force_no_radius"),
        };
    }

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        const value = await super._computeWidgetState(...arguments);
        if (methodName === "selectStyle" && params.cssProperty === "border-width") {
            // One-sided borders return "0px 0px 3px 0px", which prevents the
            // option from being displayed properly. We only keep the affected
            // border.
            return value.replace(/(^|\s)0px/gi, "").trim() || value;
        }
        return value;
    }
}
registerWebsiteOption("HeaderBox", {
    Class: HeaderBox,
    template: "website.HeaderBox",
    selector: "#wrapwrap > header",
    target: "nav",
    noCheck: true,
    data: {
        groups: ["website.group_website_designer"],
    },
}, {
    sequence: 40,
});

export class CookiesBar extends SnippetPopup {
    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Change the cookies bar layout.
     *
     * @see this.selectClass for parameters
     */
    selectLayout(previewMode, widgetValue, params) {
        const $template = $(renderToElement(`website.cookies_bar.${widgetValue}`, {
            websiteId: this.website.currentWebsite.id,
        }));

        const $content = this.$target.find('.modal-content');

        // The order of selectors is significant since certain selectors may be
        // nested within others, and we want to preserve the nested ones.
        // For instance, in the case of '.o_cookies_bar_text_policy' nested
        // inside '.o_cookies_bar_text_secondary', the parent selector should be
        // copied first, followed by the child selector to ensure that the
        // content of the nested selector is not overwritten.
        const selectorsToKeep = [
            '.o_cookies_bar_text_button',
            '.o_cookies_bar_text_button_essential',
            '.o_cookies_bar_text_title',
            '.o_cookies_bar_text_primary',
            '.o_cookies_bar_text_secondary',
            '.o_cookies_bar_text_policy'
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
    }
}

registerWebsiteOption("CookiesBar", {
    Class: CookiesBar,
    template: "website.cookie_bar_options",
    selector: "#website_cookies_bar",
    target: ".modal",
});

/**
 * Allows edition of 'cover_properties' in website models which have such
 * fields (blogs, posts, events, ...).
 */
export class CoverProperties extends SnippetOption {
    /**
     * @constructor
     */
    constructor() {
        super(...arguments);

        this.$image = this.$target.find('.o_record_cover_image');
        this.$filter = this.$target.find('.o_record_cover_filter');
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Handles a background change.
     *
     * @see this.selectClass for parameters
     */
    async background(previewMode, widgetValue, params) {
        if (previewMode === false) {
            this.$image[0].classList.remove("o_b64_image_to_save");
        }
        if (widgetValue === '') {
            this.$image.css('background-image', '');
            this.$target.removeClass('o_record_has_cover');
        } else {
            if (previewMode === false) {
                const imgEl = document.createElement("img");
                imgEl.src = widgetValue;
                await loadImageInfo(imgEl);
                if (imgEl.dataset.mimetype && ![
                    "image/gif",
                    "image/svg+xml",
                    "image/webp",
                ].includes(imgEl.dataset.mimetype)) {
                    // Convert to webp but keep original width.
                    imgEl.dataset.mimetype = "image/webp";
                    const base64src = await applyModifications(imgEl, {
                        mimetype: "image/webp",
                    });
                    widgetValue = base64src;
                    this.$image[0].classList.add("o_b64_image_to_save");
                }
            }
            this.$image.css('background-image', `url('${widgetValue}')`);
            this.$target.addClass('o_record_has_cover');
            // TODO: @owl-options Obviously wrong because it impacts previewMode - but kept as it was
            this.findWidget("record_cover_default_size_opt").enable();
        }

        if (!previewMode) {
            this._updateSavingDataset();
        }
    }
    /**
     * @see this.selectClass for parameters
     */
    filterValue(previewMode, widgetValue, params) {
        this.$filter.css('opacity', widgetValue || 0);
        this.$filter.toggleClass('oe_black', parseFloat(widgetValue) !== 0);

        if (!previewMode) {
            this._updateSavingDataset();
        }
    }
    /**
     * @override
     */
    async selectStyle(previewMode, widgetValue, params) {
        await super.selectStyle(...arguments);

        if (!previewMode) {
            this._updateSavingDataset(widgetValue);
        }
    }
    /**
     * @override
     */
    async selectClass(previewMode, widgetValue, params) {
        await super.selectClass(...arguments);

        if (!previewMode) {
            this._updateSavingDataset();
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
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
        return super._computeWidgetState(...arguments);
    }
    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        if (params.coverOptName) {
            return this.$target.data(`use_${params.coverOptName}`) === 'True';
        }
        return super._computeWidgetVisibility(...arguments);
    }
    /**
     * @private
     */
    _updateColorDataset(bgColorStyle = '', bgColorClass = '') {
        this.$target[0].dataset.bgColorStyle = bgColorStyle;
        this.$target[0].dataset.bgColorClass = bgColorClass;
    }
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
        const ccValue = colorPickerWidget._state.ccValue;
        const colorOrGradient = colorPickerWidget._state.value;
        const isGradient = weUtils.isColorGradient(colorOrGradient);
        const valueIsCSSColor = !isGradient && isCSSColor(colorOrGradient);
        const colorNames = [];
        if (ccValue) {
            colorNames.push(ccValue);
        }
        if (colorOrGradient && !isGradient && !valueIsCSSColor) {
            colorNames.push(colorOrGradient);
        }
        const bgColorClass = weUtils.computeColorClasses(colorNames).join(' ');
        const bgColorStyle = valueIsCSSColor ? `background-color: ${colorOrGradient};` :
            isGradient ? `background-color: rgba(0, 0, 0, 0); background-image: ${colorOrGradient};` : '';
        this._updateColorDataset(bgColorStyle, bgColorClass);
    }
}

registerWebsiteOption("CoverProperties", {
    Class: CoverProperties,
    template: "website.cover_properties_option",
    selector: ".o_record_cover_container",
    noCheck: true,
    withColorCombinations: true,
    withGradients: true,
});


class ScrollButton extends SnippetOption {
    constructor() {
        super(...arguments);
        this.$button = this.$target.find('.o_scroll_button');
    }

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
    }
    /**
     * Toggles the scroll down button.
     */
    toggleButton(previewMode, widgetValue, params) {
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
    }
    /**
     * @override
     */
    async selectClass(previewMode, widgetValue, params) {
        await super.selectClass(...arguments);
        // If a "d-lg-block" class exists on the section (e.g., for mobile
        // visibility option), it should be replaced with a "d-lg-flex" class.
        // This ensures that the section has the "display: flex" property
        // applied, which is the default rule for both "height" option classes.
        if (params.possibleValues.includes("o_half_screen_height")) {
            if (widgetValue) {
                this.$target[0].classList.replace("d-lg-block", "d-lg-flex");
            } else if (this.$target[0].classList.contains("d-lg-flex")) {
                // There are no known cases, but we still make sure that the
                // <section> element doesn't have a "display: flex" originally.
                this.$target[0].classList.remove("d-lg-flex");
                const sectionStyle = window.getComputedStyle(this.$target[0]);
                const hasDisplayFlex = sectionStyle.getPropertyValue("display") === "flex";
                this.$target[0].classList.add(hasDisplayFlex ? "d-lg-flex" : "d-lg-block");
            }
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _renderCustomXML(uiFragment) {
        // TODO We should have a better way to change labels depending on some
        // condition (maybe a dedicated way in updateUI...)
        if (this.$target[0].dataset.snippet === 's_image_gallery') {
            const minHeightEl = uiFragment.querySelector('[data-name="minheight_auto_opt"]');
            minHeightEl.parentElement.setAttribute('string', _t("Min-Height"));
        }
    }
    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'toggleButton':
                return !!this.$button.parent().length;
        }
        return super._computeWidgetState(...arguments);
    }
    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'fixed_height_opt') {
            return (this.$target[0].dataset.snippet === 's_image_gallery');
        }
        return super._computeWidgetVisibility(...arguments);
    }
}
registerWebsiteOption("ScrollButton", {
    Class: ScrollButton,
    template: "website.scroll_button_option",
    selector: "section",
    exclude: "[data-snippet] :not(.oe_structure) > [data-snippet], .s_instagram_page",
});


options.registry.ConditionalVisibility = options.registry.DeviceVisibility.extend({});
class ConditionalVisibilityComponent extends SnippetOptionComponent {
    setup() {
        super.setup(...arguments);

        onMounted(() => {
            for (const widget of Object.values(this.props.snippetOption.instance._userValues)) {
                const params = widget.getMethodsParams();
                if (params.saveAttribute) {
                    this.props.snippetOption.instance.optionsAttributes.push({
                        saveAttribute: params.saveAttribute,
                        attributeName: params.attributeName,
                        // If callWith dataAttribute is not specified, the default
                        // field to check on the record will be .value for values
                        // coming from another widget than M2M.
                        callWith: params.callWith || 'value',
                    });
                }
            }
        });
    }
}
class ConditionalVisibility extends DeviceVisibility {
    static defaultRenderingComponent = ConditionalVisibilityComponent;

    constructor() {
        super(...arguments);
        this.optionsAttributes = [];
        this.orm = serviceCached(this.env, "orm");
    }
    /**
     * @override
     */
    async _getRenderContext() {
        const context = await super._getRenderContext(...arguments);
        context.countryCode = session.geoip_country_code;
        context.currentWebsite = (await this.orm.searchRead(
            "website",
            [["id", "=", this.env.services.website.currentWebsite.id]],
            ["language_ids"]
        ))[0];
        return context;
    }
    /**
     * @override
     */
    async onTargetHide() {
        await super.onTargetHide(...arguments);
        if (this.$target[0].classList.contains('o_snippet_invisible')) {
            this.$target[0].classList.add('o_conditional_hidden');
        }
    }
    /**
     * @override
     */
    async onTargetShow() {
        await super.onTargetShow(...arguments);
        this.$target[0].classList.remove('o_conditional_hidden');
    }

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
    }
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
    }
    /**
     * Opens the toggler when 'conditional' is selected.
     *
     * @override
     */
    async selectDataAttribute(previewMode, widgetValue, params) {
        await super.selectDataAttribute(...arguments);

        if (params.attributeName === 'visibility') {
            const targetEl = this.$target[0];
            if (widgetValue !== 'conditional') {
                // TODO create a param to allow doing this automatically for genericSelectDataAttribute?
                delete targetEl.dataset.visibility;

                for (const attribute of this.optionsAttributes) {
                    delete targetEl.dataset[attribute.saveAttribute];
                    delete targetEl.dataset[`${attribute.saveAttribute}Rule`];
                }
            }
            this.callbacks.updateSnippetOptionVisibility(true);
        } else if (!params.isVisibilityCondition) {
            return;
        }

        this._updateCSSSelectors();
    }

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
        return super._computeWidgetState(...arguments);
    }
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
    }
}
registerWebsiteOption("ConditionalVisibility", {
    Class: ConditionalVisibility,
    template: "website.ConditionalVisibility",
    selector: "section, .s_hr",
});

/**
 * Mixin to be extended as is by WebsiteAnimate and with additional methods for
 * ImageToolsAnimate.
 */
const WebsiteAnimateMixin = (T) => class extends T {
    constructor() {
        super(...arguments);
        // Animations for which the "On Scroll" and "Direction" options are not
        // available.
        this.limitedAnimations = ['o_anim_flash', 'o_anim_pulse', 'o_anim_shake', 'o_anim_tada', 'o_anim_flip_in_x', 'o_anim_flip_in_y'];
        this.isAnimatedText = this.$target.hasClass('o_animated_text');
        this.$optionsSection = this.$overlay.data('$optionsSection');
        this.$scrollingElement = $().getScrollingElement(this.ownerDocument);
        this.$overlay[0].querySelector(".o_handles").classList.toggle("pe-none", this.isAnimatedText);
    }
    /**
     * @override
     */
    async onBuilt() {
        this.$target[0].classList.toggle('o_animate_preview', this.$target[0].classList.contains('o_animate'));
    }
    /**
     * @override
     */
    cleanForSave() {
        if (this.$target[0].closest('.o_animate')) {
            // As images may have been added in an animated element, we must
            // remove the lazy loading on them.
            this._toggleImagesLazyLoading(false);
        }
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async selectClass(previewMode, widgetValue, params) {
        await super.selectClass(...arguments);
        if (params.forceAnimation && params.name !== 'o_anim_no_effect_opt' && previewMode !== 'reset') {
            this._forceAnimation();
        }
        if (params.isAnimationTypeSelection) {
            this.$target[0].classList.toggle("o_animate_preview", this.$target[0].classList.contains("o_animate"));
        }
    }
    /**
     * @override
     */
    async selectDataAttribute(previewMode, widgetValue, params) {
        await super.selectDataAttribute(...arguments);
        if (params.forceAnimation) {
            this._forceAnimation();
        }
    }
    /**
     * Sets the animation mode.
     *
     * @see this.selectClass for parameters
     */
    animationMode(previewMode, widgetValue, params) {
        const targetClassList = this.$target[0].classList;
        this.$scrollingElement[0].classList.remove('o_wanim_overflow_xy_hidden');
        targetClassList.remove('o_animating', 'o_animate_both_scroll', 'o_visible', 'o_animated', 'o_animate_out');
        this.$target[0].style.animationDelay = '';
        this.$target[0].style.animationPlayState = '';
        this.$target[0].style.animationName = '';
        this.$target[0].style.visibility = '';

        if (widgetValue === 'onScroll') {
            this.$target[0].dataset.scrollZoneStart = 0;
            this.$target[0].dataset.scrollZoneEnd = 100;
        } else {
            delete this.$target[0].dataset.scrollZoneStart;
            delete this.$target[0].dataset.scrollZoneEnd;
        }

        const setToFadeIn = () => {
            targetClassList.add('o_anim_fade_in');
            this._toggleImagesLazyLoading(false);
        }
        const resetProperties = () => {
            const possibleEffects = this._requestUserValueWidgets('animation_effect_opt')[0].getMethodsParams('selectClass').possibleValues;
            const possibleDirections = this._requestUserValueWidgets('animation_direction_opt')[0].getMethodsParams('selectClass').possibleValues;
            const possibleEffectsAndDirections = possibleEffects.concat(possibleDirections);
            // Remove the classes added by "Effect" and "Direction" options if
            // "Animation" is "None".
            for (const targetClass of targetClassList.value.split(/\s+/g)) {
                if (possibleEffectsAndDirections.indexOf(targetClass) >= 0) {
                    targetClassList.remove(targetClass);
                }
            }
            this.$target[0].style.setProperty('--wanim-intensity', '');
            this.$target[0].style.animationDuration = '';
            this._toggleImagesLazyLoading(true);
        }

        if (!params.ImageToolsAnimate) {
            if (!params.activeValue && widgetValue) {
                // If "Animation" was on "None" and it is no longer, it is set
                // to "fade_in" by default.
                setToFadeIn();
            }
            if (!widgetValue) {
                resetProperties();
            }
        }

        return { setToFadeIn, resetProperties };
    }
    /**
     * Sets the animation intensity.
     *
     * @see this.selectClass for parameters
     */
    animationIntensity(previewMode, widgetValue, params) {
        this.$target[0].style.setProperty('--wanim-intensity', widgetValue);
        this._forceAnimation();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    async _forceAnimation() {
        this.$target.css('animation-name', 'dummy');

        if (this.$target[0].classList.contains('o_animate_on_scroll')) {
            // Trigger a DOM reflow.
            void this.$target[0].offsetWidth;
            this.$target.css('animation-name', '');
            this.ownerDocument.defaultView.dispatchEvent(new Event('resize'));
        } else {
            // Trigger a DOM reflow (Needed to prevent the animation from
            // being launched twice when previewing the "Intensity" option).
            await new Promise(resolve => setTimeout(resolve));
            this.$target.addClass('o_animating');
            this.callbacks.coverUpdate(true);
            this.$scrollingElement[0].classList.add('o_wanim_overflow_xy_hidden');
            this.$target.css('animation-name', '');
            this.$target.one('webkitAnimationEnd oanimationend msAnimationEnd animationend', () => {
                this.$scrollingElement[0].classList.remove('o_wanim_overflow_xy_hidden');
                this.$target.removeClass('o_animating');
            });
        }
    }
    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        const hasAnimateClass = this.$target[0].classList.contains("o_animate");
        switch (widgetName) {
            case 'no_animation_opt': {
                return !this.isAnimatedText;
            }
            case 'animation_effect_opt': {
                return hasAnimateClass;
            }
            case 'animation_trigger_opt': {
                return !this.$target[0].closest('.dropdown');
            }
            case 'animation_on_scroll_opt':
            case 'animation_direction_opt': {
                if (widgetName === "animation_direction_opt" && !hasAnimateClass) {
                    return false;
                }
                return !this.limitedAnimations.some(className => this.$target[0].classList.contains(className));
            }
            case 'animation_intensity_opt': {
                if (!hasAnimateClass) {
                    return false;
                }
                const possibleDirections = this._requestUserValueWidgets('animation_direction_opt')[0].getMethodsParams('selectClass').possibleValues;
                if (this.$target[0].classList.contains('o_anim_fade_in')) {
                    for (const targetClass of this.$target[0].classList) {
                        // Show "Intensity" if "Fade in" + direction is not
                        // "In Place" ...
                        if (possibleDirections.indexOf(targetClass) >= 0) {
                            return true;
                        }
                    }
                    // ... but hide if "Fade in" + "In Place" direction.
                    return false;
                }
                return true;
            }
            case 'animation_on_hover_opt': {
                return false;
            }
        }
        return super._computeWidgetVisibility(...arguments);
    }
    /**
     * @override
     */
    _computeVisibility(methodName, params) {
        if (this.$target[0].matches('img')) {
            return isImageSupportedForStyle(this.$target[0]);
        }
        return super._computeVisibility(...arguments);
    }
    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === 'animationIntensity') {
            return window.getComputedStyle(this.$target[0]).getPropertyValue('--wanim-intensity');
        }
        return super._computeWidgetState(...arguments);
    }
    /**
     * Removes or adds the lazy loading on images because animated images can
     * appear before or after their parents and cause bugs in the animations.
     * To put "lazy" back on the "loading" attribute, we simply remove the
     * attribute as it is automatically added on page load.
     *
     * @private
     * @param {Boolean} lazy
     */
    _toggleImagesLazyLoading(lazy) {
        const imgEls = this.$target[0].matches('img')
            ? [this.$target[0]]
            : this.$target[0].querySelectorAll('img');
        for (const imgEl of imgEls) {
            if (lazy) {
                // Let the automatic system add the loading attribute
                imgEl.removeAttribute('loading');
            } else {
                imgEl.loading = 'eager';
            }
        }
    }
}
const WebsiteAnimate = WebsiteAnimateMixin(SnippetOption);

registerWebsiteOption("WebsiteAnimate", {
    Class: WebsiteAnimate,
    template: "website.WebsiteAnimate",
    selector: ".o_animable, section .row > div, .fa, .btn",
    exclude: "[data-oe-xpath], .o_not-animable, .s_col_no_resize.row > div, .s_col_no_resize",
});
registerWebsiteOption("TextAnimate", {
    Class: WebsiteAnimate,
    template: "website.WebsiteAnimate",
    selector: ".o_animated_text",
    textSelector: ".o_animated_text",
});

export class ImageToolsAnimate extends WebsiteAnimateMixin(ImageTools) {
    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    animationMode(previewMode, widgetValue, params) {
        params.ImageToolsAnimate = true;
        const { setToFadeIn, resetProperties } = super.animationMode(...arguments);
        if (params.activeValue === "o_animate_on_hover") {
            this._disableHoverEffect();
        }
        if ((!params.activeValue || params.activeValue === "o_animate_on_hover")
               && widgetValue && widgetValue !== "onHover") {
            // If "Animation" was on "None" or "o_animate_on_hover" and it is no
            // longer, it is set to "fade_in" by default.
            setToFadeIn();
        }
        if (!widgetValue || widgetValue === "onHover") {
            resetProperties();
        }
        if (widgetValue === "onHover") {
            // Pause the history until the hover effect is applied in
            // "setImgShapeHoverEffect". This prevents saving the intermediate
            // steps done (in a tricky way) up to that point.
            this.options.wysiwyg.odooEditor.historyPauseSteps();
            this._enableHoverEffect();
        }
    }
    /**
     * Sets the hover effects of the image shape.
     *
     * @see this.selectClass for parameters
     */
    async setImgShapeHoverEffect(previewMode, widgetValue, params) {
        const imgEl = this._getImg();
        if (previewMode !== "reset") {
            this.prevHoverEffectColor = imgEl.dataset.hoverEffectColor;
            this.prevHoverEffectIntensity = imgEl.dataset.hoverEffectIntensity;
            this.prevHoverEffectStrokeWidth = imgEl.dataset.hoverEffectStrokeWidth;
        }
        delete imgEl.dataset.hoverEffectColor;
        delete imgEl.dataset.hoverEffectIntensity;
        delete imgEl.dataset.hoverEffectStrokeWidth;
        if (previewMode === true) {
            if (params.name === "hover_effect_overlay_opt") {
                imgEl.dataset.hoverEffectColor = this._getCSSColorValue("black-25");
            } else if (params.name === "hover_effect_outline_opt") {
                imgEl.dataset.hoverEffectColor = this._getCSSColorValue("primary");
                imgEl.dataset.hoverEffectStrokeWidth = 10;
            } else {
                imgEl.dataset.hoverEffectIntensity = 20;
                if (params.name !== "hover_effect_mirror_blur_opt") {
                    imgEl.dataset.hoverEffectColor = "rgba(0, 0, 0, 0)";
                }
            }
        } else {
            if (this.prevHoverEffectColor) {
                imgEl.dataset.hoverEffectColor = this.prevHoverEffectColor;
            }
            if (this.prevHoverEffectIntensity) {
                imgEl.dataset.hoverEffectIntensity = this.prevHoverEffectIntensity;
            }
            if (this.prevHoverEffectStrokeWidth) {
                imgEl.dataset.hoverEffectStrokeWidth = this.prevHoverEffectStrokeWidth;
            }
        }
        await this._reapplyCurrentShape();
        // When the hover effects are first activated from the "animationMode"
        // function, the history was paused to avoid recording intermediate
        // steps. That's why we unpause it here.
        if (this.firstHoverEffect) {
            this.options.wysiwyg.odooEditor.historyUnpauseSteps();
            delete this.firstHoverEffect;
        }
    }
    /**
     * @see this.selectClass for parameters
     */
    async selectDataAttribute(previewMode, widgetValue, params) {
        await super.selectDataAttribute(...arguments);
        if (["shapeAnimationSpeed", "hoverEffectIntensity", "hoverEffectStrokeWidth"].includes(params.attributeName)) {
            await this._reapplyCurrentShape();
        }
    }
    /**
     * Sets the color of hover effects.
     *
     * @see this.selectClass for parameters
     */
    async setHoverEffectColor(previewMode, widgetValue, params) {
        const img = this._getImg();
        let defaultColor = "rgba(0, 0, 0, 0)";
        if (img.dataset.hoverEffect === "overlay") {
            defaultColor = "black-25";
        } else if (img.dataset.hoverEffect === "outline") {
            defaultColor = "primary";
        }
        img.dataset.hoverEffectColor = this._getCSSColorValue(widgetValue || defaultColor);
        await this._reapplyCurrentShape();
    }
    /**
     * @see this.selectClass for parameters
     */
    showHoverEffect(previewMode, widgetValue, params) {}

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async updateUI() {
        await super.updateUI(...arguments);
        // Adapts the colorpicker label according to the selected "On Hover"
        // animation.
        const hoverEffectName = this.$target[0].dataset.hoverEffect;
        if (hoverEffectName) {
            const needToAdaptLabel = ["image_zoom_in", "image_zoom_out", "dolly_zoom"].includes(hoverEffectName);
            const newContext = await this._getRenderContext();
            newContext.hoverEffectColorLabel = needToAdaptLabel ? _t("Overlay") : _t("Color");
            Object.assign(this.renderContext, newContext);
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        switch (widgetName) {
            case "animation_on_hover_opt": {
                return this._canHaveHoverEffect() && !await isImageCorsProtected(this.$target[0]);
            }
            case "hover_effect_none_opt": {
                // The hover effects are removed with the "WebsiteAnimate" animation
                // selector so this option should not be visible.
                return false;
            }
        }
        if (params.optionsPossibleValues.setImgShapeHoverEffect) {
            const imgEl = this._getImg();
            return imgEl.classList.contains("o_animate_on_hover") && this._canHaveHoverEffect();
        }
        return super._computeWidgetVisibility(...arguments);
    }
    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === "setHoverEffectColor") {
            const imgEl = this._getImg();
            return imgEl.dataset.hoverEffectColor || "";
        }
        return super._computeWidgetState(...arguments);
    }
    /**
     * @override
     */
    async _writeShape(svgText) {
        const img = this._getImg();
        let needToRefreshPublicWidgets = false;
        let hasHoverEffect = false;

        // Add shape animations on hover.
        if (img.dataset.hoverEffect && this._canHaveHoverEffect()) {
            // The "ImageShapeHoverEffet" public widget needs to restart
            // (e.g. image replacement).
            needToRefreshPublicWidgets = true;
            hasHoverEffect = true;
        }

        const dataURL = await this.computeShape(svgText, img);
        let clonedImgEl = null;
        if (hasHoverEffect) {
            // This is useful during hover effects previews. Without this, in
            // Chrome, the 'mouse out' animation is triggered very briefly when
            // previewMode === 'reset' (when transitioning from one hover effect
            // to another), causing a visual glitch. To avoid this, we hide the
            // image with its clone when the source is set.
            clonedImgEl = img.cloneNode(true);
            this.options.wysiwyg.odooEditor.observerUnactive("addClonedImgForHoverEffectPreview");
            img.classList.add("d-none");
            img.insertAdjacentElement("afterend", clonedImgEl);
            this.options.wysiwyg.odooEditor.observerActive("addClonedImgForHoverEffectPreview");
        }
        const loadedImg = await loadImage(dataURL, img);
        if (hasHoverEffect) {
            this.options.wysiwyg.odooEditor.observerUnactive("removeClonedImgForHoverEffectPreview");
            clonedImgEl.remove();
            img.classList.remove("d-none");
            this.options.wysiwyg.odooEditor.observerActive("removeClonedImgForHoverEffectPreview");
        }
        if (needToRefreshPublicWidgets) {
            await this._refreshPublicWidgets();
        }
        return loadedImg;
    }
    /**
     * @override
     */
    async _computeImgShapeHoverEffect(svgEl, imgEl) {
        // Add shape animations on hover.
        if (imgEl.dataset.hoverEffect && this._canHaveHoverEffect()) {
            this._addImageShapeHoverEffect(svgEl, imgEl);
        }        
    }
    /**
     * Checks if the shape can have a hover effect.
     *
     * @private
     * @returns {boolean}
     */
    _canHaveHoverEffect() {
        return !this._isDeviceShape() && !this._isAnimatedShape() && this._isImageSupportedForShapes();
    }
    /**
     * Adds hover effect to the SVG.
     *
     * @private
     * @param {HTMLElement} svgEl
     * @param {HTMLImageElement} [img] img element
     */
    async _addImageShapeHoverEffect(svgEl, img) {
        let rgba = null;
        let rbg = null;
        let opacity = null;
        // Add the required parts for the hover effects to the SVG.
        const hoverEffectName = img.dataset.hoverEffect;
        if (!this.hoverEffectsSvg) {
            const parser = new DOMParser();
            const response = await fetch("/website/static/src/svg/hover_effects.svg");
            const xmlDoc = parser.parseFromString(await response.text(), "text/xml");
            this.hoverEffectsSvg = xmlDoc.documentElement;
        }
        const hoverEffectEls = this.hoverEffectsSvg.querySelectorAll(`#${hoverEffectName} > *`);
        hoverEffectEls.forEach(hoverEffectEl => {
            svgEl.appendChild(hoverEffectEl.cloneNode(true));
        });
        // Modifies the svg according to the chosen hover effect and the value
        // of the options.
        const animateEl = svgEl.querySelector("animate");
        const animateTransformEls = svgEl.querySelectorAll("animateTransform");
        const animateElValues = animateEl?.getAttribute("values");
        let animateTransformElValues = animateTransformEls[0]?.getAttribute("values");
        if (img.dataset.hoverEffectColor) {
            rgba = convertCSSColorToRgba(img.dataset.hoverEffectColor);
            rbg = `rgb(${rgba.red},${rgba.green},${rgba.blue})`;
            opacity = rgba.opacity / 100;
            if (!["outline", "image_mirror_blur"].includes(hoverEffectName)) {
                svgEl.querySelector('[fill="hover_effect_color"]').setAttribute("fill", rbg);
                animateEl.setAttribute("values", animateElValues.replace("hover_effect_opacity", opacity));
            }
        }
        switch (hoverEffectName) {
            case "outline": {
                svgEl.querySelector('[stroke="hover_effect_color"]').setAttribute("stroke", rbg);
                svgEl.querySelector('[stroke-opacity="hover_effect_opacity"]').setAttribute("stroke-opacity", opacity);
                // The stroke width needs to be multiplied by two because half
                // of the stroke is invisible since it is centered on the path.
                const strokeWidth = parseInt(img.dataset.hoverEffectStrokeWidth) * 2;
                animateEl.setAttribute("values", animateElValues.replace("hover_effect_stroke_width", strokeWidth));
                break;
            }
            case "image_zoom_in":
            case "image_zoom_out":
            case "dolly_zoom": {
                const imageEl = svgEl.querySelector("image");
                const clipPathEl = svgEl.querySelector("#clip-path");
                imageEl.setAttribute("id", "shapeImage");
                // Modify the SVG so that the clip-path is not zoomed when the
                // image is zoomed.
                imageEl.setAttribute("style", "transform-origin: center; width: 100%; height: 100%");
                imageEl.setAttribute("preserveAspectRatio", "none");
                svgEl.setAttribute("viewBox", "0 0 1 1");
                svgEl.setAttribute("preserveAspectRatio", "none");
                clipPathEl.setAttribute("clipPathUnits", "userSpaceOnUse");
                const clipPathValue = imageEl.getAttribute("clip-path");
                imageEl.removeAttribute("clip-path");
                const gEl = document.createElementNS("http://www.w3.org/2000/svg", "g");
                gEl.setAttribute("clip-path", clipPathValue);
                imageEl.parentNode.replaceChild(gEl, imageEl);
                gEl.appendChild(imageEl);
                let zoomValue = 1.01 + parseInt(img.dataset.hoverEffectIntensity) / 200;
                animateTransformEls[0].setAttribute("values", animateTransformElValues.replace("hover_effect_zoom", zoomValue));
                if (hoverEffectName === "image_zoom_out") {
                    // Set zoom intensity for the image.
                    const styleAttr = svgEl.querySelector("style");
                    styleAttr.textContent = styleAttr.textContent.replace("hover_effect_zoom", zoomValue);
                }
                if (hoverEffectName === "dolly_zoom") {
                    clipPathEl.setAttribute("style", "transform-origin: center;");
                    // Set zoom intensity for clip-path and overlay.
                    zoomValue = 0.99 - parseInt(img.dataset.hoverEffectIntensity) / 2000;
                    animateTransformEls.forEach((animateTransformEl, index) => {
                        if (index > 0) {
                            animateTransformElValues = animateTransformEl.getAttribute("values");
                            animateTransformEl.setAttribute("values", animateTransformElValues.replace("hover_effect_zoom", zoomValue));
                        }
                    });
                }
                break;
            }
            case "image_mirror_blur": {
                const imageEl = svgEl.querySelector("image");
                imageEl.setAttribute('id', 'shapeImage');
                imageEl.setAttribute('style', 'transform-origin: center;');
                const imageMirrorEl = imageEl.cloneNode();
                imageMirrorEl.setAttribute("id", 'shapeImageMirror');
                imageMirrorEl.setAttribute("filter", "url(#blurFilter)");
                imageEl.insertAdjacentElement("beforebegin", imageMirrorEl);
                const zoomValue = 0.99 - parseInt(img.dataset.hoverEffectIntensity) / 200;
                animateTransformEls[0].setAttribute("values", animateTransformElValues.replace("hover_effect_zoom", zoomValue));
                break;
            }
        }
    }
    /**
     * Disables the hover effect on the image.
     *
     * @private
     */
    async _disableHoverEffect() {
        const imgEl = this._getImg();
        const shapeName = imgEl.dataset.shape?.split("/")[2];
        delete imgEl.dataset.hoverEffect;
        delete imgEl.dataset.hoverEffectColor;
        delete imgEl.dataset.hoverEffectStrokeWidth;
        delete imgEl.dataset.hoverEffectIntensity;
        await this._applyOptions();
        // If "Square" shape, remove it, it doesn't make sense to keep it
        // without hover effect.
        if (shapeName === "geo_square") {
            this._requestUserValueWidgets("remove_img_shape_opt")[0].enable();
        }
    }
    /**
     * Enables the hover effect on the image.
     * 
     * @private
     */
    _enableHoverEffect() {
        this.env.snippetEditionRequest(() => {
            // Add the "square" shape to the image if it has no shape
            // because the "hover effects" need a shape to work.
            const imgEl = this._getImg();
            const shapeName = imgEl.dataset.shape?.split("/")[2];
            if (!shapeName) {
                const shapeImgSquareWidget = this._requestUserValueWidgets("shape_img_square_opt")[0];
                shapeImgSquareWidget.enable();
            }
            // Add the "Overlay" hover effect to the shape.
            this.firstHoverEffect = true;
            const hoverEffectOverlayWidget = this._requestUserValueWidgets("hover_effect_overlay_opt")[0];
            hoverEffectOverlayWidget.enable();
        });
    }
    /**
     * @override
     */
    async _select(previewMode, widget) {
        await super._select(...arguments);
        // This is a special case where we need to override the "_select"
        // function in order to trigger mouse events for hover effects on the
        // images when previewing the options. This is done here because if it
        // was done in one of the widget methods, the animation would be
        // canceled when "_refreshPublicWidgets" is executed in the "super"
        const hasSetImgShapeHoverEffectMethod = widget.getMethodsNames().includes("setImgShapeHoverEffect");
        const hasShowHoverEffectMethod = widget.getMethodsNames().includes("showHoverEffect");
        // We trigger the animation when preview mode is "false", except for
        // the "setImgShapeHoverEffect" option, where we trigger it when
        // preview mode is "true".
        if (previewMode === hasSetImgShapeHoverEffectMethod && hasShowHoverEffectMethod) {
            this.$target[0].dispatchEvent(new Event("mouseover"));
            this.hoverTimeoutId = setTimeout(() => {
                this.$target[0].dispatchEvent(new Event("mouseout"));
            }, 700);
        } else if (previewMode === "reset") {
            clearTimeout(this.hoverTimeoutId);
        }
    }
    /**
     * Checks if a shape can be applied on the target.
     *
     * @private
     * @returns {boolean}
     */
    _isImageSupportedForShapes() {
        const imgEl = this._getImg();
        return imgEl.dataset.originalId && this._isImageSupportedForProcessing(imgEl);
    }
    /**
     * @override
     */
    _resetImgShape(imgEl) {
        super._resetImgShape(...arguments);
        if (!this._canHaveHoverEffect()) {
            delete imgEl.dataset.hoverEffect;
            delete imgEl.dataset.hoverEffectColor;
            delete imgEl.dataset.hoverEffectStrokeWidth;
            delete imgEl.dataset.hoverEffectIntensity;
            imgEl.classList.remove("o_animate_on_hover");
        }
        if (!this._isAnimatedShape()) {
            delete imgEl.dataset.shapeAnimationSpeed;
        }
    }
    /**
     * @override
     */
    _removeImgShapeWithHoverEffectHook(imgEl, widgetValue) {
        if (imgEl.dataset.hoverEffect && !widgetValue) {
            // When a shape is removed and there is a hover effect on the
            // image, we then place the "Square" shape as the default because a
            // shape is required for the hover effects to work.
            const shapeImgSquareWidget = this._requestUserValueWidgets("shape_img_square_opt")[0];
            widgetValue = shapeImgSquareWidget.getActiveValue("setImgShape");
        }
        return super._removeImgShapeWithHoverEffectHook(imgEl, widgetValue);
    }
    /**
     * @override
     */
    _deleteHoverAttributes(imgEl) {
        delete imgEl.dataset.hoverEffect;
        delete imgEl.dataset.hoverEffectColor;
        delete imgEl.dataset.hoverEffectStrokeWidth;
        delete imgEl.dataset.hoverEffectIntensity;
        imgEl.classList.remove("o_animate_on_hover");
    }
}
registerWebsiteOption("ImageToolsAnimate", {
    Class: ImageToolsAnimate,
    template: "website.ImageToolsAnimate",
    selector: "img",
    exclude: "[data-oe-type='image'] > img, [data-oe-xpath]",
});

/**
 * Allows edition of text "Highlight Effects" following this generic structure:
 * `<span class="o_text_highlight">
 *      <span class="o_text_highlight_item">
 *          line1-textNode1 [line1-textNode2,...]
 *          <svg.../>
 *      </span>
 *      [<br/>]
 *      <span class="o_text_highlight_item">
 *          line2-textNode1 [line2-textNode2,...]
 *          <svg.../>
 *      </span>
 *      ...
 * </span>`
 * To correctly adapt each highlight unit when the text content is changed.
 */
class TextHighlight extends SnippetOption {
    /**
     * @override
     */
    constructor() {
        super(...arguments);
        // Reduce overlay opacity for more highlight visibility on small text.
        this.$overlay[0].style.opacity = "0.25";
        this.$overlay[0].querySelector(".o_handles").classList.add("pe-none");
    }
    /**
    * @override
    */
    notify(name, data) {
        // Apply the highlight effect DOM structure when added for the first time
        // and display the highlight effects grid immediately.
        if (name === "new_text_highlight") {
            this._autoAdaptHighlights();
            this._requestUserValueWidgets("text_highlight_opt")[0]?.enable();
        }
        super.notify(...arguments);
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Activates & deactivates the text highlight effect.
     *
     * @see this.selectClass for parameters
     */
    async setTextHighlight(previewMode, widgetValue, params) {
        return widgetValue ? this._addTextHighlight(widgetValue)
            : removeTextHighlight(this.$target[0]);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Used to add a highlight SVG element to the targeted text node(s).
     * This should also take in consideration a situation where many text nodes
     * are separate e.g. `<p>first text content<br/>second text content...</p>`.
     * To correctly handle those situations, every set of text nodes will be
     * wrapped in a `.o_text_highlight_item` that contains its highlight SVG.
     *
     * @param {String} highlightID
     * @private
     */
    _addTextHighlight(highlightID) {
        const highlightEls = [...this.$target[0].querySelectorAll(".o_text_highlight_item svg")];
        if (highlightEls.length) {
            // If the text element has a highlight effect, we only need to
            // change the SVG.
            highlightEls.forEach(svg => {
                svg.after(drawTextHighlightSVG(svg.parentElement, highlightID));
                svg.remove();
            });
        } else {
            this._autoAdaptHighlights();
        }
    }
    /**
     * Used to set the highlight effect DOM structure on the targeted text
     * content.
     *
     * @private
     */
    _autoAdaptHighlights() {
        this.env.snippetEditionRequest(async () =>
            await this._refreshPublicWidgets($(this.options.wysiwyg.odooEditor.editable))
        );
    }
}
registerWebsiteOption("TextHighlight", {
    Class: TextHighlight,
    template: "website.TextHighlight",
    selector: ".o_text_highlight",
    textSelector: ".o_text_highlight",
});

class TextHighlightBtnUserValue extends ButtonUserValue {
    constructor() {
        super(...arguments);
        this._state.textContentRef = undefined;
    }
    /**
     * @type {import("@web/core/utils/hooks").Ref}
     */
    set textContentRef(value) {
        this._state.textContentRef = value;
    }
    /**
     * Mounts the SVG on the <WeTextHighlightBtn>.
     * This has to be done here in the UserValue because it depends on the
     * parent WeTextHighlightSelect opening - which has access to its subValues
     * but not to its children components.
     */
    mountSvg() {
        // Only when there is no highlight SVGs.
        if (
            this._state.textContentRef.el
            && this._state.textContentRef.el.querySelector("div")
            && !this._state.textContentRef.el.querySelector("svg")
        ) {
            // Get the text highlight linked to the button and apply it to its
            // text content.
            const el = this._state.textContentRef.el.querySelector("div");
            el.append(drawTextHighlightSVG(el, this._data.setTextHighlight));
        }
    }
}
class WeTextHighlightBtn extends WeButton {
    static template = "website.WeTextHighlightBtn";
    static StateModel = TextHighlightBtnUserValue;
    setup() {
        super.setup();
        this.state.textContentRef = this.textContentRef;
    }
}
registry.category("snippet_widgets").add("WeTextHighlightBtn", WeTextHighlightBtn);

class WeTextHighlightSelect extends WeSelect {
    setup() {
        super.setup();
        useEffect(
            (opened) => {
                // To draw highlight SVGs for `<we-select/>` previews, we need
                // the component to be opened (we need the correct size values
                // from `getBoundingClientRect()`). This code will build the
                // highlight preview the first time we open the `<we-select/>`.
                if (opened) {
                    for (const userValue of Object.values(this.state._subValues)) {
                        if (userValue instanceof TextHighlightBtnUserValue) {
                            userValue.mountSvg();
                        }
                    }
                }
            },
            () => [this.state.opened]
        );
    }
}
registry.category("snippet_widgets").add("WeTextHighlightSelect", WeTextHighlightSelect);

/**
 * Replaces current target with the specified template layout
 */
export class MegaMenuLayout extends SelectTemplate {
    /**
     * @override
     */
    static forceNoDeleteButton = true;

    constructor() {
        super(...arguments);
        this.selectTemplateWidgetName = 'mega_menu_template_opt';
    }

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
            super.notify(...arguments);
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === 'selectTemplate') {
            return this._getCurrentTemplateXMLID();
        }
        return super._computeWidgetState(...arguments);
    }
    /**
     * @private
     * @returns {string} xmlid of the current template.
     */
    _getCurrentTemplateXMLID() {
        const templateDefiningClass = this.containerEl.querySelector('section')
            .classList.value.split(' ').filter(cl => cl.startsWith('s_mega_menu'))[0];
        return `website.${templateDefiningClass}`;
    }
}
registerWebsiteOption("MegaMenuLayout", {
    Class: MegaMenuLayout,
    template: "web_editor.mega_menu_layout_options",
    selector: ".o_mega_menu",
});

/**
 * Hides delete and clone buttons for Mega Menu block.
 */
export class MegaMenuNoDelete extends SnippetOption {
    /**
     * @override
     */
    static forceNoDeleteButton = true;

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
    }
}
registerWebsiteOption("MegaMenuNoDelete", {
    Class: MegaMenuLayout,
    selector: ".o_mega_menu > section",
});
registerWebsiteOption("MegaMenuNoDeleteDrop", {
    selector: ".o_mega_menu .nav > .nav-link",
    dropIn: ".o_mega_menu nav",
    dropNear: ".o_mega_menu .nav-link",
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
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async updateUIVisibility() {
        await this._super(...arguments);
        const nonDraggableClasses = [
            's_table_of_content_navbar_wrap',
            's_table_of_content_main',
        ];
        if (nonDraggableClasses.some(c => this.$target[0].classList.contains(c))) {
            const moveHandleEl = this.$overlay[0].querySelector('.o_move_handle');
            moveHandleEl.classList.add('d-none');
        }
    },
});

registerWebsiteOption("InfoPage", {
    template: "website.InfoPage",
    selector: "main:has(.o_website_info)",
    noCheck: true,
    data: {
        groups: ["website.group_website_designer"],
        pageOptions: true,
    },
});

export class SwitchableViews extends SnippetOption {
    /**
     * @override
     */
    async willStart() {
        this.switchableRelatedViews = await new Promise((resolve, reject) => {
            this.env.getSwitchableRelatedViews({
                onSuccess: resolve,
                onFailure: reject,
            });
        });
        return super.willStart(...arguments);
    }
    /**
     * @override
     */
    async _getRenderContext() {
        return {
            switchableRelatedViews: this.switchableRelatedViews,
        };
    }
    /***
     * @override
     */
    _computeVisibility() {
        return !!this.switchableRelatedViews.length;
    }
    /**
     * @override
     */
    _checkIfWidgetsUpdateNeedReload() {
        return true;
    }
}

registerWebsiteOption("SwitchableViews", {
    Class: SwitchableViews,
    template: "website.switchable_views_option",
    selector: "#wrapwrap > main",
    noCheck: "true",
    group: "website.group_website_designer",
});


export class GridImage extends SnippetOption {

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    changeGridImageMode(previewMode, widgetValue, params) {
        const imageGridItemEl = this._getImageGridItem();
        if (imageGridItemEl) {
            imageGridItemEl.classList.toggle('o_grid_item_image_contain', widgetValue === 'contain');
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns the parent column if it is marked as a grid item containing an
     * image.
     *
     * @returns {?HTMLElement}
     */
    _getImageGridItem() {
        return this.$target[0].closest(".o_grid_item_image");
    }
    /**
     * @override
     */
    _computeVisibility() {
        // Special conditions for the hover effects.
        const hasSquareShape = this.$target[0].dataset.shape === "web_editor/geometric/geo_square";
        const effectAllowsOption = !["dolly_zoom", "outline", "image_mirror_blur"]
            .includes(this.$target[0].dataset.hoverEffect);

        return super._computeVisibility(...arguments)
            && !!this._getImageGridItem()
            && (!('shape' in this.$target[0].dataset)
                || hasSquareShape && effectAllowsOption);
    }
    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === 'changeGridImageMode') {
            const imageGridItemEl = this._getImageGridItem();
            return imageGridItemEl && imageGridItemEl.classList.contains('o_grid_item_image_contain')
                ? 'contain'
                : 'cover';
        }
        return super._computeWidgetState(...arguments);
    }
}

registerWebsiteOption("GridImage", {
    Class: GridImage,
    template: "website.grid_image_option",
    selector: "img",
});


class GalleryElement extends SnippetOption {
    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Allows to change the position of an item on the set.
     *
     * @see this.selectClass for parameters
     */
    position(previewMode, widgetValue, params) {
        const optionName = this.$target[0].classList.contains("carousel-item") ? "Carousel"
            : "GalleryImageList";
        const itemEl = this.$target[0];
        this.callbacks.notifyOptions({
            optionName: optionName,
            name: "reorder_items",
            data: {
                itemEl: itemEl,
                position: widgetValue,
            },
        });
    }
}
registerWebsiteOption("GalleryElement", {
    Class: GalleryElement,
    template: "website.GalleryElement",
    selector: ".s_image_gallery img, .s_carousel .carousel-item",
}, { sequence: 10 });


export class Button extends SnippetOption {
    /**
     * @override
     */
    constructor() {
        super(...arguments);
        const isUnremovableButton = this.$target[0].classList.contains("oe_unremovable");
        this.forceDuplicateButton = !isUnremovableButton;
        this.forceNoDeleteButton = isUnremovableButton;
    }
    /**
     * @override
     */
    onBuilt(options) {
        // Only if the button is built, not if a snippet containing that button
        // is built (e.g. true if dropping a button from the snippet menu onto
        // the page, false if dropping an "image-text" snippet).
        if (options.isCurrent) {
            this._adaptButtons();
        }
    }
    /**
     * @override
     */
    onClone(options) {
        // Only if the button is cloned, not if a snippet containing that button
        // is cloned.
        if (options.isCurrent) {
            this._adaptButtons(false);
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Checks if there are buttons before or after the target element and
     * applies appropriate styling.
     *
     * @private
     * @param {Boolean} [adaptAppearance=true]
     */
    _adaptButtons(adaptAppearance = true) {
        const previousSiblingEl = this.$target[0].previousElementSibling;
        const nextSiblingEl = this.$target[0].nextElementSibling;
        let siblingButtonEl = null;
        // When multiple buttons follow each other, they may break on 2 lines or
        // more on mobile, so they need a margin-bottom. Also, if the button is
        // dropped next to another button add a space between them.
        if (nextSiblingEl?.matches(".btn")) {
            nextSiblingEl.classList.add("mb-2");
            this.$target[0].after(' ');
            // It is first the next button that we put in this variable because
            // we want to copy as a priority the style of the previous button
            // if it exists.
            siblingButtonEl = nextSiblingEl;
        }
        if (previousSiblingEl?.matches(".btn")) {
            previousSiblingEl.classList.add("mb-2");
            this.$target[0].before(' ');
            siblingButtonEl = previousSiblingEl;
        }
        if (siblingButtonEl) {
            this.$target[0].classList.add("mb-2");
        }
        if (adaptAppearance) {
            if (siblingButtonEl && !this.$target[0].matches(".s_custom_button")) {
                // If the dropped button is not a custom button then we adjust
                // its appearance to match its sibling.
                if (siblingButtonEl.classList.contains("btn-secondary")) {
                    this.$target[0].classList.remove("btn-primary");
                    this.$target[0].classList.add("btn-secondary");
                }
                if (siblingButtonEl.classList.contains("btn-sm")) {
                    this.$target[0].classList.add("btn-sm");
                } else if (siblingButtonEl.classList.contains("btn-lg")) {
                    this.$target[0].classList.add("btn-lg");
                }
            } else {
                // To align with the editor's behavior, we need to enclose the
                // button in a <p> tag if it's not dropped within a <p> tag. We only
                // put the dropped button in a <p> if it's not next to another
                // button, because some snippets have buttons that aren't inside a
                // <p> (e.g. s_text_cover).
                // TODO: this definitely needs to be fixed at web_editor level.
                // Nothing should prevent adding buttons outside of a paragraph.
                const btnContainerEl = this.$target[0].closest("p");
                if (!btnContainerEl) {
                    const paragraphEl = document.createElement("p");
                    this.$target[0].parentNode.insertBefore(paragraphEl, this.$target[0]);
                    paragraphEl.appendChild(this.$target[0]);
                }
            }
            this.$target[0].classList.remove("s_custom_button");
        }
    }
}

registerWebsiteOption("Button", {
    Class: Button,
    selector: "a.btn",
    exclude: "so_submit_button_selector",
});

class WebsiteLayoutColumn extends LayoutColumn {
    /**
     * @override
     */
    _isMobile() {
        return this.env.services.website.context.isMobile;
    }
}

registerWebsiteOption("GridColumns", {
    Class: GridColumns,
    template: "website.grid_columns_option",
    selector: ".row:not(.s_col_no_resize) > div",
});

registerWebsiteOption("WebsiteLayoutColumns", {
    Class: WebsiteLayoutColumn,
    template: "website.layout_column",
    selector: "section, section.s_carousel_wrapper .carousel-item",
    target: "> *:has(> .row), > .s_allow_columns",
    exclude: ".s_masonry_block, .s_features_grid, .s_media_list, .s_table_of_content, .s_process_steps, .s_image_gallery, .s_timeline",
    tags: ["website"],
}, { sequence: 15 });


registerWebsiteOption("card_color_border_shadow", {
    Class: Box,
    template: "website.card_color_border_shadow",
    selector: ".s_three_columns .row > div, .s_comparisons .row > div",
    target: ".card",
});

registerWebsiteOption("card_color", {
    template: "website.card_color",
    selector: ".card:not(.s_card)",
});

registerWebsiteOption("horizontal_alignment", {
    template: "website.horizontal_alignment_option",
    selector: ".s_share, .s_text_highlight, .s_social_media",
});

registerWebsiteOption("block_width_option", {
    template: "website.block_width_option",
    selector: ".s_blockquote, .s_text_highlight",
});

registerWebsiteOption("block_align_option", {
    template: "website.block_align_option",
    selector: ".s_alert, .s_card, .s_blockquote, .s_text_highlight",
});

registerWebsiteOption("vertical_alignment", {
    class: vAlignment,
    template: "website.vertical_alignment_option",
    selector: ".s_text_image, .s_image_text, .s_three_columns, .s_numbers, .s_faq_collapse, .s_references",
    target: ".row",
});

registerWebsiteOption("share_social_media", {
    template: "website.share_social_media_option",
    selector: ".s_share, .s_social_media",
});

patch(SnippetMove.prototype, {
    /**
     * @override
     */
    _isMobile() {
        return this.env.services.website.context.isMobile;
    },
});

export function websiteRegisterBackgroundOptions(key, options) {
    options.module = "website";
    registerBackgroundOptions(key, options, (name) => name === "toggler" && "website.snippet_options_background_options");
    if (options.withVideos) {
        registerWebsiteOption(`${key}-bgVideo`, {
            Class: BackgroundVideo,
            template: "website.BackgroundVideo",
            ...options,
        }, { sequence: 30 });
    }
    if (options.withImages) {
        registerWebsiteOption(`${key}-parallax`, {
            Class: Parallax,
            template: "website.Parallax",
            ...options,
        }, { sequence: 30 });
    }

}

export const onlyBgColorSelector = "section .row > div, .s_text_highlight, .s_mega_menu_thumbnails_footer, .s_hr, .s_cta_badge";
export const onlyBgColorExclude = ".s_col_no_bgcolor, .s_col_no_bgcolor.row > div, .s_masonry_block .row > div, .s_color_blocks_2 .row > div, .s_image_gallery .row > div, .s_text_cover .row > .o_not_editable, [data-snippet] :not(.oe_structure) > .s_hr";
export const baseOnlyBgImageSelector = ".s_tabs .oe_structure > *, footer .oe_structure > *";
export const onlyBgImageSelector = baseOnlyBgImageSelector;
export const onlyBgImageExclude = "";
export const bothBgColorImageSelector = "section, .carousel-item, .s_masonry_block .row > div, .s_color_blocks_2 .row > div, .parallax, .s_text_cover .row > .o_not_editable";
export const bothBgColorImageExclude = baseOnlyBgImageSelector + ", .s_carousel_wrapper, .s_image_gallery .carousel-item, .s_google_map, .s_map, [data-snippet] :not(.oe_structure) > [data-snippet], .s_masonry_block .s_col_no_resize";

websiteRegisterBackgroundOptions("BothBgImage", {
    selector: bothBgColorImageSelector,
    exclude: bothBgColorImageExclude,
    withColors: true,
    withImages: true,
    withVideos: true,
    withShapes: true,
    withColorCombinations: true,
    withGradients: true,
});

websiteRegisterBackgroundOptions("OnlyBgColor", {
        selector: onlyBgColorSelector,
        exclude: onlyBgColorExclude,
        withColors: true,
        withImages: false,
        withColorCombinations: true,
        withGradients: true,
});

websiteRegisterBackgroundOptions("OnlyBgImage", {
    selector: onlyBgImageSelector,
    exclude: onlyBgImageExclude,
    withColors: false,
    withImages: true,
    withVideos: true,
    withShapes: true,
});

registerWebsiteOption("ColumnsOnly", {
    Class: WebsiteLayoutColumn,
    template: "website.columns_only",
    selector: "section.s_features_grid, section.s_process_steps",
    target: "> *:has(> .row), > .s_allow_columns",
}, { sequence: 15 });

// TODO: @owl-options What to do with those ?
let so_submit_button_selector = ".s_donation_donate_btn, .s_website_form_send";

registerWebsiteOption("SnippetSave", {
    Class: SnippetSave,
    template: "website.snippet_save_option",
    selector: "[data-snippet], a.btn",
    exclude: `.o_no_save, ${so_submit_button_selector}`,
});
