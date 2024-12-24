/** @odoo-module **/

import { loadCSS } from "@web/core/assets";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { useChildRef } from "@web/core/utils/hooks";
import weUtils from "@web_editor/js/common/utils";
import options from "@web_editor/js/editor/snippets.options";
import { NavbarLinkPopoverWidget } from "@website/js/widgets/link_popover_widget";
import wUtils from "@website/js/utils";
import {
    applyModifications,
    isImageSupportedForStyle,
    loadImageInfo,
} from "@web_editor/js/editor/image_processing";
import "@website/snippets/s_popup/options";
import { range } from "@web/core/utils/numbers";
import { _t } from "@web/core/l10n/translation";
import { pyToJsLocale } from "@web/core/l10n/utils";
import {Domain} from "@web/core/domain";
import {
    isCSSColor,
    convertCSSColorToRgba,
    convertRgbaToCSSColor,
    convertRgbToHsl,
    convertHslToRgb,
 } from '@web/core/utils/colors';
import { renderToElement, renderToFragment } from "@web/core/utils/render";
import { browser } from "@web/core/browser/browser";
import {
    removeTextHighlight,
    drawTextHighlightSVG,
} from "@website/js/text_processing";
import { throttleForAnimation } from "@web/core/utils/timing";

import { Component, markup, useEffect, useRef, useState } from "@odoo/owl";

const InputUserValueWidget = options.userValueWidgetsRegistry['we-input'];
const SelectUserValueWidget = options.userValueWidgetsRegistry['we-select'];
const Many2oneUserValueWidget = options.userValueWidgetsRegistry['we-many2one'];

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

Many2oneUserValueWidget.include({
    init() {
        this._super(...arguments);
        this.fields = this.bindService("field");
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

const UrlPickerUserValueWidget = InputUserValueWidget.extend({
    events: Object.assign({}, InputUserValueWidget.prototype.events || {}, {
        'click .o_we_redirect_to': '_onRedirectTo',
    }),

    /**
     * @override
     */
    start: async function () {
        await this._super(...arguments);
        const linkButton = document.createElement('we-button');
        const icon = document.createElement('i');
        icon.classList.add('fa', 'fa-fw', 'fa-external-link');
        linkButton.classList.add('o_we_redirect_to', 'o_we_link', 'ms-1');
        linkButton.title = _t("Preview this URL in a new tab");
        linkButton.appendChild(icon);
        this.containerEl.after(linkButton);
        this.el.classList.add('o_we_large');
        this.inputEl.classList.add('text-start');
        const options = {
            classes: {
                "ui-autocomplete": 'o_website_ui_autocomplete'
            },
            body: this.getParent().$target[0].ownerDocument.body,
            urlChosen: this._onWebsiteURLChosen.bind(this),
        };
        this.unmountAutocompleteWithPages = wUtils.autocompleteWithPages(this.inputEl, options);
    },

    open() {
        this._super(...arguments);
        document.querySelector(".o_website_ui_autocomplete")?.classList?.remove("d-none");
    },

    close() {
        this._super(...arguments);
        document.querySelector(".o_website_ui_autocomplete")?.classList?.add("d-none");
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
    destroy() {
        this.unmountAutocompleteWithPages?.();
        this.unmountAutocompleteWithPages = null;
        this._super(...arguments);
    }
});

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

const FontFamilyPickerUserValueWidget = SelectUserValueWidget.extend({
    events: Object.assign({}, SelectUserValueWidget.prototype.events || {}, {
        'click .o_we_add_font_btn': '_onAddFontClick',
        'click .o_we_delete_font_btn': '_onDeleteFontClick',
    }),
    fontVariables: [], // Filled by editor menu when all options are loaded

    /**
     * @override
     */
    init() {
        this.dialog = this.bindService("dialog");
        this.orm = this.bindService("orm");
        return this._super(...arguments);
    },
    /**
     * @override
     */
    start: async function () {
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

        await this._super(...arguments);

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
        // TODO ideally, remove the <link> elements created once this widget
        // instance is destroyed (although it should not hurt to keep them for
        // the whole backend lifecycle).
        const proms = fontsToLoad.map(async fontURL => loadCSS(fontURL));
        const fontsLoadingProm = Promise.all(proms);

        const fontEls = [];
        const methodName = this.el.dataset.methodName || 'customizeWebsiteVariable';
        const variable = this.el.dataset.variable;
        const themeFontsNb = nbFonts - (this.googleLocalFonts.length + this.googleFonts.length + this.uploadedLocalFonts.length);
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
            const fontEl = document.createElement('we-button');
            fontEl.setAttribute('string', fontName);
            fontEl.dataset.variable = variable;
            fontEl.dataset[methodName] = fontKey;
            fontEl.dataset.fontFamily = fontFamily;
            const iconWrapperEl = document.createElement("div");
            iconWrapperEl.classList.add("text-end");
            fontEl.appendChild(iconWrapperEl);
            if ((realFontNb <= themeFontsNb) && !isSystemFonts) {
                // Add the "cloud" icon next to the theme's default fonts
                // because they are served by Google.
                iconWrapperEl.appendChild(Object.assign(document.createElement('i'), {
                    role: 'button',
                    className: 'text-info me-2 fa fa-cloud',
                    title: _t("This font is hosted and served to your visitors by Google servers"),
                }));
            }
            fontEls.push(fontEl);
            this.menuEl.appendChild(fontEl);
        }

        if (this.uploadedLocalFonts.length) {
            const uploadedLocalFontsEls = fontEls.splice(-this.uploadedLocalFonts.length);
            uploadedLocalFontsEls.forEach((el, index) => {
                $(el).find(".text-end").append(renderToFragment('website.delete_font_btn', {
                    index: index,
                    local: "uploaded",
                }));
            });
        }

        if (this.googleLocalFonts.length) {
            const googleLocalFontsEls = fontEls.splice(-this.googleLocalFonts.length);
            googleLocalFontsEls.forEach((el, index) => {
                $(el).find(".text-end").append(renderToFragment('website.delete_font_btn', {
                    index: index,
                    local: "google",
                }));
            });
        }

        if (this.googleFonts.length) {
            const googleFontsEls = fontEls.splice(-this.googleFonts.length);
            googleFontsEls.forEach((el, index) => {
                $(el).find(".text-end").append(renderToFragment('website.delete_font_btn', {
                    index: index,
                }));
            });
        }

        $(this.menuEl).append($(renderToElement('website.add_font_btn', {
            variable: variable,
        })));

        return fontsLoadingProm;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async setValue() {
        await this._super(...arguments);

        this.menuTogglerEl.style.fontFamily = '';
        const activeWidget = this._userValueWidgets.find(widget => !widget.isPreviewed() && widget.isActive());
        if (activeWidget) {
            this.menuTogglerEl.style.fontFamily = activeWidget.el.dataset.fontFamily;
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    async _onAddFontClick(ev) {
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
        const variable = $(ev.currentTarget).data('variable');
        this.dialog.add(addFontDialog, {
            title: _t("Add a Google font or upload a custom font"),
            onClickSave: async (state) => {
                const uploadedFontName = state.uploadedFontName;
                const uploadedFontFaces = state.uploadedFontFaces;
                let font = undefined;
                if (uploadedFontName && uploadedFontFaces) {
                    const fontExistsLocally = this.uploadedLocalFonts.some(localFont => localFont.split(':')[0] === `'${uploadedFontName}'`);
                    if (fontExistsLocally) {
                        this.dialog.add(ConfirmationDialog, {
                            title: _t("Font exists"),
                            body: _t("This uploaded font already exists.\nTo replace an existing font, remove it first."),
                        });
                        return;
                    }
                    const homonymGoogleFontExists =
                        this.googleFonts.some(font => font === uploadedFontName) ||
                        this.googleLocalFonts.some(font => font.split(':')[0] === `'${uploadedFontName}'`);
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
                    this.uploadedLocalFonts.push(`'${uploadedFontName}': ${fontCssId}`);
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
                    const fontExistsLocally = this.googleLocalFonts.some(localFont => localFont.split(':')[0] === fontName);
                    const fontExistsOnServer = this.allFonts.includes(fontName);
                    const preventFontAddition = fontExistsLocally || (fontExistsOnServer && googleFontServe);
                    if (preventFontAddition) {
                        this.dialog.add(ConfirmationDialog, {
                            title: _t("Font exists"),
                            body: _t("This font already exists, you can only add it as a local font to replace the server version."),
                        });
                        return;
                    }
                    if (googleFontServe) {
                        this.googleFonts.push(font);
                    } else {
                        this.googleLocalFonts.push(`'${font}': ''`);
                    }
                }
                this.trigger_up('fonts_custo_request', {
                    values: {[variable]: `'${font}'`},
                    googleFonts: this.googleFonts,
                    googleLocalFonts: this.googleLocalFonts,
                    uploadedLocalFonts: this.uploadedLocalFonts,
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
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onDeleteFontClick: async function (ev) {
        ev.preventDefault();
        const values = {};

        const save = await new Promise(resolve => {
            this.dialog.add(ConfirmationDialog, {
                body: _t("Deleting a font requires a reload of the page. This will save all your changes and reload the page, are you sure you want to proceed?"),
                confirm: () => resolve(true),
                cancel: () => resolve(false),
            });
        });
        if (!save) {
            return;
        }

        // Remove Google font
        const fontIndex = parseInt(ev.target.dataset.fontIndex);
        const localFont = ev.target.dataset.localFont;
        let fontName;
        if (localFont === 'uploaded') {
            const font = this.uploadedLocalFonts[fontIndex].split(':');
            // Remove double quotes
            fontName = font[0].substring(1, font[0].length - 1);
            values['delete-font-attachment-id'] = font[1];
            this.uploadedLocalFonts.splice(fontIndex, 1);
        } else if (localFont === 'google') {
            const googleFont = this.googleLocalFonts[fontIndex].split(':');
            // Remove double quotes
            fontName = googleFont[0].substring(1, googleFont[0].length - 1);
            values['delete-font-attachment-id'] = googleFont[1];
            this.googleLocalFonts.splice(fontIndex, 1);
        } else {
            fontName = this.googleFonts[fontIndex];
            this.googleFonts.splice(fontIndex, 1);
        }

        // Adapt font variable indexes to the removal
        const style = window.getComputedStyle(this.$target[0].ownerDocument.documentElement);
        FontFamilyPickerUserValueWidget.prototype.fontVariables.forEach((variable) => {
            const value = weUtils.getCSSVariableValue(variable, style);
            if (value.substring(1, value.length - 1) === fontName) {
                // If an element is using the google font being removed, reset
                // it to the theme default.
                values[variable] = 'null';
            }
        });

        this.trigger_up('fonts_custo_request', {
            values: values,
            googleFonts: this.googleFonts,
            googleLocalFonts: this.googleLocalFonts,
            uploadedLocalFonts: this.uploadedLocalFonts,
        });
    },
});

const GPSPicker = InputUserValueWidget.extend({
    // Explicitly not consider all InputUserValueWidget events. E.g. we actually
    // don't want input focusout messing with the google map API. Because of
    // this, clicking on google map autocomplete suggestion on Firefox was not
    // working properly.
    events: {},

    /**
     * @constructor
     */
    init() {
        this._super(...arguments);
        this._gmapCacheGPSToPlace = {};

        // The google API will be loaded inside the website iframe. Let's try
        // not having to load it in the backend too and just using the iframe
        // google object instead.
        this.contentWindow = this.$target[0].ownerDocument.defaultView;

        this.notification = this.bindService("notification");
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
        this.el.classList.add('o_we_large');
        if (!this._gmapLoaded) {
            return;
        }

        this._gmapAutocomplete = new this.contentWindow.google.maps.places.Autocomplete(this.inputEl, {types: ['geocode']});
        this.contentWindow.google.maps.event.addListener(this._gmapAutocomplete, 'place_changed', this._onPlaceChanged.bind(this));
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);

        // Without this, the google library injects elements inside the backend
        // DOM but do not remove them once the editor is left. Notice that
        // this is also done when the widget is destroyed for another reason
        // than leaving the editor, but if the google API needs that container
        // again afterwards, it will simply recreate it.
        for (const el of document.body.querySelectorAll('.pac-container')) {
            el.remove();
        }
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

        this.notification.add(
            _t("A Google Map error occurred. Make sure to read the key configuration popup carefully."),
            { type: 'danger', sticky: true }
        );
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
});
options.userValueWidgetsRegistry['we-urlpicker'] = UrlPickerUserValueWidget;
options.userValueWidgetsRegistry['we-fontfamilypicker'] = FontFamilyPickerUserValueWidget;
options.userValueWidgetsRegistry['we-gpspicker'] = GPSPicker;

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

options.Class.include({
    custom_events: Object.assign({}, options.Class.prototype.custom_events || {}, {
        'fonts_custo_request': '_onFontsCustoRequest',
    }),
    specialCheckAndReloadMethodsNames: ['customizeWebsiteViews', 'customizeWebsiteVariable', 'customizeWebsiteColor'],

    /**
     * @override
     */
    init() {
        this._super(...arguments);
        // Since the website is displayed in an iframe, its jQuery
        // instance is not the same as the editor. This property allows
        // for easy access to bootstrap plugins (Carousel, Modal, ...).
        // This is only needed because jQuery doesn't send custom events
        // the same way native javascript does. So if a jQuery instance
        // triggers a custom event, only that same jQuery instance will
        // trigger handlers set with `.on`.
        this.$bsTarget = this.ownerDocument.defaultView.$(this.$target[0]);

        this.orm = this.bindService("orm");
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
        const needReload = await this._super(...arguments);
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
    _computeWidgetState: async function (methodName, params) {
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
                // Color values (e.g. "header-text-color") must be saved as
                // string. TODO: Color values should be added to the color map.
                if (params.colorNames?.includes(widgetValue)) {
                    widgetValue =`'${widgetValue}'`;
                }
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
        return this.orm.call("web_editor.assets", "make_scss_customization", [url, values]);
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

        // Some blocks flicker when we start their public widgets, so we skip
        // the refresh for them to avoid the flickering.
        const targetNoRefreshSelector = ".s_instagram_page";
        // TODO: we should review the way public widgets are restarted when
        // converting to OWL and a new API.
        if (this.options.isWebsite && !widget.$el.closest('[data-no-widget-refresh="true"]').length
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
     * @param {OdooEvent} ev
     */
    _onFontsCustoRequest(ev) {
        const values = ev.data.values ? Object.assign({}, ev.data.values) : {};
        const googleFonts = ev.data.googleFonts;
        const googleLocalFonts = ev.data.googleLocalFonts;
        const uploadedLocalFonts = ev.data.uploadedLocalFonts;
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

options.registry.ImageTools.include({
    async _computeWidgetVisibility(widgetName, params) {
        if (params.optionsPossibleValues.selectStyle
                && params.cssProperty === 'width'
                && this.$target[0].classList.contains('o_card_img')) {
            return false;
        }
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

options.registry.WebsiteLevelColor = options.Class.extend({
    specialCheckAndReloadMethodsNames: options.Class.prototype.specialCheckAndReloadMethodsNames
        .concat(['customizeWebsiteLayer2Color']),
    /**
     * @constructor
     */
    init() {
        this._super(...arguments);
        this._rpc = options.serviceCached(rpc);
    },
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
    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        const _super = this._super.bind(this);
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
        return _super(...arguments);
    },
});

options.registry.OptionsTab = options.registry.WebsiteLevelColor.extend({
    GRAY_PARAMS: {EXTRA_SATURATION: "gray-extra-saturation", HUE: "gray-hue"},

    /**
     * @override
     */
    init() {
        this._super(...arguments);
        this.grayParams = {};
        this.grays = {};
        this.orm = this.bindService("orm");
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
        await this._customizeWebsiteVariables({
            'body-image-type': this.bodyImageType,
            'body-image': widgetValue ? `'${widgetValue}'` : '',
        }, params.nullValue);
    },
    async openCustomCodeDialog(previewMode, widgetValue, params) {
        return new Promise(resolve => {
            this.trigger_up('open_edit_head_body_dialog', {
                onSuccess: resolve,
            });
        });
    },
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
        this.trigger_up('request_save', {
            reload: false,
            action: 'website.theme_install_kanban_action',
        });
    },
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
        this.trigger_up("request_save", {
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
    },
    /**
     * @see this.selectClass for parameters
     */
    async customizeButtonStyle(previewMode, widgetValue, params) {
        await this._customizeWebsiteVariables({
            [`btn-${params.button}-outline`]: widgetValue === "outline" ? "true" : "false",
            [`btn-${params.button}-flat`]: widgetValue === "flat" ? "true" : "false",
        }, params.nullValue);
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
        // Getting base grays defined in color_palette.scss
        const gray = weUtils.getCSSVariableValue(`base-${id}`, getComputedStyle(document.documentElement));
        const grayRGB = convertCSSColorToRgba(gray);
        const hsl = convertRgbToHsl(grayRGB.red, grayRGB.green, grayRGB.blue);
        const adjustedGrayRGB = convertHslToRgb(this.grayParams[this.GRAY_PARAMS.HUE],
            Math.min(Math.max(hsl.saturation + this.grayParams[this.GRAY_PARAMS.EXTRA_SATURATION], 0), 100),
            hsl.lightness);
        return convertRgbaToCSSColor(adjustedGrayRGB.red, adjustedGrayRGB.green, adjustedGrayRGB.blue);
    },
    /**
     * @override
     */
    async _renderCustomXML(uiFragment) {
        await this._super(...arguments);
        const extraSaturationRangeEl = uiFragment.querySelector(`we-range[data-param=${this.GRAY_PARAMS.EXTRA_SATURATION}]`);
        if (extraSaturationRangeEl) {
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
            extraSaturationRangeEl.dataset.max = 100 - minValue.hsl.saturation;
            extraSaturationRangeEl.dataset.min = -maxValue.hsl.saturation;
        }
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
        if (params.removeFont) {
            const font = await this._computeWidgetState('customizeWebsiteVariable', {
                variable: params.removeFont,
            });
            return !!font;
        }
        return this._super(...arguments);
    },
});

options.registry.ThemeColors = options.registry.OptionsTab.extend({
    /**
     * @override
     */
    async start() {
        // Checks for support of the old color system
        const style = window.getComputedStyle(this.$target[0].ownerDocument.documentElement);
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
            const ccPreviewEl = $(renderToElement('web_editor.color.combination.preview.legacy'))[0];
            ccPreviewEl.classList.add('text-center', `o_cc${i}`, 'o_colored_level', 'o_we_collapse_toggler');
            collapseEl.appendChild(ccPreviewEl);
            collapseEl.appendChild(renderToFragment('website.color_combination_edition', {number: i}));
            ccPreviewEls.push(ccPreviewEl);
            presetCollapseEl.appendChild(collapseEl);
        }
        await this._super(...arguments);
    },
});

options.registry.menu_data = options.Class.extend({
    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
        this.notification = this.bindService("notification");
    },

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
        const popoverContainer = this.ownerDocument.getElementById('oe_manipulators');
        NavbarLinkPopoverWidget.createFor({
            target: this.$target[0],
            wysiwyg,
            container: popoverContainer,
            notify: this.notification.add,
            checkIsWebsiteDesigner: () => user.hasGroup("website.group_website_designer"),
            onEditLinkClick: (widget) => {
                var $menu = widget.$target.find('[data-oe-id]');
                this.trigger_up('menu_dialog', {
                    name: $menu.text(),
                    url: $menu.parent().attr('href'),
                    save: (name, url) => {
                        let websiteId;
                        this.trigger_up('context_get', {
                            callback: ctx => websiteId = ctx['website_id'],
                        });
                        const data = {
                            id: $menu.data('oe-id'),
                            name,
                            url,
                        };
                        return this.orm.call(
                            "website.menu",
                            "save",
                            [websiteId, {'data': [data]}]
                        ).then(function () {
                            widget.wysiwyg.odooEditor.observerUnactive();
                            widget.$target.attr('href', url);
                            $menu.text(name);
                            widget.wysiwyg.odooEditor.observerActive();
                        });
                    },
                });
                widget.popover.hide();
            },
            onEditMenuClick: (widget) => {
                const contentMenu = widget.target.closest('[data-content_menu_id]');
                const rootID = contentMenu ? parseInt(contentMenu.dataset.content_menu_id, 10) : undefined;
                this.trigger_up('action_demand', {
                    actionName: 'edit_menu',
                    params: [rootID],
                });
            },
        });
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

options.registry.Carousel = options.registry.CarouselHandler.extend({
    /**
     * @override
     */
    start: function () {
        this.$indicators = this.$target.find('.carousel-indicators');
        this.$controls = this.$target.find('.carousel-control-prev, .carousel-control-next, .carousel-indicators');

        // Prevent enabling the carousel overlay when clicking on the carousel
        // controls (indeed we want it to change the carousel slide then enable
        // the slide overlay) + See "CarouselItem" option.
        this.$controls.addClass('o_we_no_overlay');

        // Handle the sliding manually.
        this.__onControlClick = throttleForAnimation(this._onControlClick.bind(this));
        this.$controls.on("click.carousel_option", this.__onControlClick);

        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        this.$bsTarget.off('.carousel_option');
        this.$controls.off(".carousel_option");
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
    notify(name, data) {
        this._super(...arguments);
        if (name === 'add_slide') {
            this._addSlide().then(data.onSuccess);
        } else if (name === "slide") {
            this._slide(data.direction).then(data.onSuccess);
        }
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    addSlide(previewMode, widgetValue, params) {
        return this._addSlide();
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
        this.$target.find('[data-bs-slide], [data-bs-slide-to]').toArray().forEach((el) => {
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
    async _addSlide() {
        this.options.wysiwyg.odooEditor.historyPauseSteps();
        const $items = this.$target.find('.carousel-item');
        this.$controls.removeClass('d-none');
        const $active = $items.filter('.active');
        this.$indicators.append($('<button>', {
            'data-bs-target': '#' + this.$target.attr('id'),
            'aria-label': _t('Carousel indicator'),
        }));
        this.$indicators.append(' ');
        // Need to remove editor data from the clone so it gets its own.
        $active.clone(false)
            .removeClass('active')
            .insertAfter($active);
        await this._slide("next");
        this.options.wysiwyg.odooEditor.historyUnpauseSteps();
    },
    /**
     * Slides the carousel in the given direction.
     *
     * @private
     * @param {String|Number} direction the direction in which to slide:
     *     - "prev": the previous slide;
     *     - "next": the next slide;
     *     - number: a slide number.
     * @returns {Promise}
     */
    _slide(direction) {
        this.trigger_up("disable_loading_effect");
        let _slideTimestamp;
        this.$bsTarget.one("slide.bs.carousel", () => {
            _slideTimestamp = window.performance.now();
            setTimeout(() => this.trigger_up('hide_overlay'));
        });

        return new Promise(resolve => {
            this.$bsTarget.one("slid.bs.carousel", () => {
                // slid.bs.carousel is most of the time fired too soon by bootstrap
                // since it emulates the transitionEnd with a setTimeout. We wait
                // here an extra 20% of the time before retargeting edition, which
                // should be enough...
                const _slideDuration = (window.performance.now() - _slideTimestamp);
                setTimeout(() => {
                    // Setting the active indicator manually, as Bootstrap could
                    // not do it because the `data-bs-slide-to` attribute is not
                    // here in edit mode anymore.
                    const $activeSlide = this.$target.find(".carousel-item.active");
                    const activeIndex = [...$activeSlide[0].parentElement.children].indexOf($activeSlide[0]);
                    const activeIndicatorEl = [...this.$indicators[0].children][activeIndex];
                    activeIndicatorEl.classList.add("active");
                    activeIndicatorEl.setAttribute("aria-current", "true");

                    this.trigger_up("activate_snippet", {
                        $snippet: $activeSlide,
                        ifInactiveOptions: true,
                    });
                    this.$bsTarget.trigger("active_slide_targeted"); // TODO remove in master: kept for compatibility.
                    this.trigger_up("enable_loading_effect");
                    resolve();
                }, 0.2 * _slideDuration);
            });

            this.$bsTarget.carousel(direction);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Slides the carousel when clicking on the carousel controls. This handler
     * allows to put the sliding in the mutex, to avoid race conditions.
     *
     * @private
     * @param {Event} ev
     */
    _onControlClick(ev) {
        // Compute to which slide the carousel will slide.
        const controlEl = ev.currentTarget;
        let direction;
        if (controlEl.classList.contains("carousel-control-prev")) {
            direction = "prev";
        } else if (controlEl.classList.contains("carousel-control-next")) {
            direction = "next";
        } else {
            const indicatorEl = ev.target;
            if (!indicatorEl.matches(".carousel-indicators > *") || indicatorEl.classList.contains("active")) {
                return;
            }
            direction = [...controlEl.children].indexOf(indicatorEl);
        }

        // Slide the carousel.
        this.trigger_up("snippet_edition_request", {exec: async () => {
            this.options.wysiwyg.odooEditor.historyPauseSteps();
            await this._slide(direction);
            this.options.wysiwyg.odooEditor.historyUnpauseSteps();
            this.options.wysiwyg.odooEditor.historyStep();
        }});
    },
    /**
     * @override
     */
    _getItemsGallery() {
        return Array.from(this.$target[0].querySelectorAll(".carousel-item"));
    },
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
    },

});

options.registry.CarouselItem = options.Class.extend({
    isTopOption: true,
    forceNoDeleteButton: true,

    /**
     * @override
     */
    start: function () {
        this.$carousel = this.$bsTarget.closest('.carousel');
        this.$targetCarousel = this.$target.closest(".carousel");
        this.$indicators = this.$carousel.find('.carousel-indicators');
        this.$controls = this.$carousel.find('.carousel-control-prev, .carousel-control-next, .carousel-indicators');
        this.carouselOptionName = this.$carousel[0].classList.contains("s_carousel_intro") ? "CarouselIntro" : "Carousel";

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
        // Activate the active slide after removing a slide.
        if (this.hasRemovedSlide) {
            this.trigger_up("activate_snippet", {
                $snippet: this.$targetCarousel.find(".carousel-item.active"),
                ifInactiveOptions: true,
            });
            this.hasRemovedSlide = false;
        }
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
        return new Promise(resolve => {
            this.trigger_up("option_update", {
                optionName: this.carouselOptionName,
                name: "add_slide",
                data: {
                    onSuccess: () => resolve(),
                },
            });
        });
    },
    /**
     * Removes the current slide.
     *
     * @see this.selectClass for parameters.
     */
    async removeSlide(previewMode) {
        this.options.wysiwyg.odooEditor.historyPauseSteps();
        const $items = this.$carousel.find('.carousel-item');
        const newLength = $items.length - 1;
        if (!this.removing && newLength > 0) {
            // The active indicator is deleted to ensure that the other
            // indicators will still work after the deletion.
            const $toDelete = $items.filter('.active').add(this.$indicators.find('.active'));
            this.removing = true; // TODO remove in master: kept for stable.
            // Go to the previous slide.
            await new Promise(resolve => {
                this.trigger_up("option_update", {
                    optionName: this.carouselOptionName,
                    name: "slide",
                    data: {
                        direction: "prev",
                        onSuccess: () => resolve(),
                    },
                });
            });
            // Remove the slide.
            $toDelete.remove();
            this.$controls.toggleClass("d-none", newLength === 1);
            this.$carousel.trigger("content_changed");
            this.removing = false;
        }
        this.options.wysiwyg.odooEditor.historyUnpauseSteps();
        this.hasRemovedSlide = true;
    },
    /**
     * Goes to next slide or previous slide.
     *
     * @see this.selectClass for parameters
     */
    switchToSlide(previewMode, widgetValue, params) {
        this.options.wysiwyg.odooEditor.historyPauseSteps();
        const direction = widgetValue === "left" ? "prev" : "next";
        return new Promise(resolve => {
            this.trigger_up("option_update", {
                optionName: this.carouselOptionName,
                name: "slide",
                data: {
                    direction: direction,
                    onSuccess: () => {
                        this.options.wysiwyg.odooEditor.historyUnpauseSteps();
                        resolve();
                    },
                },
            });
        });
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
        this.$bsTarget.on('shown.bs.collapse hidden.bs.collapse', '[role="region"]', function () {
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
        var $panel = this.$bsTarget.find('.collapse').removeData('bs.collapse');
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
    },
});

options.registry.HeaderElements = options.Class.extend({
    /**
     * @constructor
     */
    init() {
        this._super(...arguments);
        this._rpc = options.serviceCached(rpc);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        const _super = this._super.bind(this);
        switch (widgetName) {
            case "header_language_selector_opt":
                this._languages = await this._rpc.call("/website/get_languages");
                if (this._languages.length === 1) {
                    return false;
                }
                break;
        }
        return _super(...arguments);
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
        this.setTarget(this.$target.closest('#wrapwrap > header'));
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
                return !!this.$('.navbar-brand').length;
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
        // TODO should be able to change both options at the same time, as the
        // `params` list suggests.
        await new Promise((resolve, reject) => {
            this.trigger_up('action_demand', {
                actionName: 'toggle_page_option',
                params: [{name: 'header_color', value: ''}],
                onSuccess: () => resolve(),
                onFailure: reject,
            });
        });
        await new Promise(resolve => {
            this.trigger_up('action_demand', {
                actionName: 'toggle_page_option',
                params: [{name: 'header_text_color', value: ''}],
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
        if (widgetValue && !isCSSColor(widgetValue)) {
            widgetValue = params.colorPrefix + widgetValue;
        }
        await new Promise((resolve, reject) => {
            this.trigger_up('action_demand', {
                actionName: 'toggle_page_option',
                params: [{name: params.pageOptionName, value: widgetValue}],
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
 * Manage the visibility of snippets on mobile/desktop.
 */
options.registry.DeviceVisibility = options.Class.extend({

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
        this.trigger_up('snippet_option_visibility_update', {show: widgetValue !== (isMobile ? 'no_mobile' : 'no_desktop')});
    },
    /**
     * @override
     */
    async onTargetHide() {
        this.$target[0].classList.remove('o_snippet_override_invisible');
    },
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
    },
    /**
     * @override
     */
    cleanForSave() {
        this.$target[0].classList.remove('o_snippet_override_invisible');
    },

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
        return await this._super(...arguments);
    },
    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        if (this.$target[0].classList.contains('s_table_of_content_main')) {
            return false;
        }
        return this._super(...arguments);
    }
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

    /**
     * @override
     */
    init() {
        this._super(...arguments);
        this.notification = this.bindService("notification");
    },
    /**
     * @override
     */
    start() {
        // Generate anchor and copy it to clipboard on click, show the tooltip on success
        const buttonEl = this.el.querySelector("we-button");
        this.isModal = this.$target[0].classList.contains("modal");
        if (buttonEl && !this.isModal) {
            this._buildClipboard(buttonEl);
        }

        return this._super(...arguments);
    },
    /**
     * @override
     */
    onClone: function () {
        this.$target.removeAttr('data-anchor');
        this.$target.filter(':not(.carousel)').removeAttr('id');
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    notify(name, data) {
        this._super(...arguments);
        if (name === "modalAnchor") {
            this._buildClipboard(data.buttonEl);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Element} buttonEl
     */
    _buildClipboard(buttonEl) {
        buttonEl.addEventListener("click", async (ev) => {
            const anchorLink = this._getAnchorLink();
            await browser.navigator.clipboard.writeText(anchorLink);
            const message = markup(_t("Anchor copied to clipboard<br>Link: %s", anchorLink));
            this.notification.add(message, {
                type: "success",
                buttons: [{name: _t("Edit"), onClick: () => this._openAnchorDialog(buttonEl), primary: true}],
            });
        });
    },

    /**
     * @private
     * @param {Element} buttonEl
     */
    _openAnchorDialog(buttonEl) {
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
                    buttonEl.click();
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
    },
    /**
     * @private
     * @param {String} value
     */
    _setAnchorName: function (value) {
        if (value) {
            this.$target[0].id = value;
            if (!this.isModal) {
                this.$target[0].dataset.anchor = true;
            }
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
            while (this.ownerDocument.getElementById(anchorName + n)) {
                n = (n || 1) + 1;
            }
            this._setAnchorName(anchorName + n);
        }
        const pathName = this.isModal ? "" : this.ownerDocument.location.pathname;
        return `${pathName}#${this.$target[0].id}`;
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

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        const value = await this._super(...arguments);
        if (methodName === "selectStyle" && params.cssProperty === "border-width") {
            // One-sided borders return "0px 0px 3px 0px", which prevents the
            // option from being displayed properly. We only keep the affected
            // border.
            return value.replace(/(^|\s)0px/gi, "").trim() || value;
        }
        return value;
    },
});

options.registry.CookiesBar = options.registry.SnippetPopup.extend({
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

        const $template = $(renderToElement(`website.cookies_bar.${widgetValue}`, {
            websiteId: websiteId,
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
    /**
     * @override
     */
    async selectClass(previewMode, widgetValue, params) {
        await this._super(...arguments);
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
    },

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
    },
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
    _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'fixed_height_opt') {
            return (this.$target[0].dataset.snippet === 's_image_gallery');
        }
        return this._super(...arguments);
    },
});

options.registry.ConditionalVisibility = options.registry.DeviceVisibility.extend({
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
        await this._super(...arguments);
        if (this.$target[0].classList.contains('o_snippet_invisible')) {
            this.$target[0].classList.add('o_conditional_hidden');
        }
    },
    /**
     * @override
     */
    async onTargetShow() {
        await this._super(...arguments);
        this.$target[0].classList.remove('o_conditional_hidden');
    },
    // Todo: remove me in master.
    /**
     * @override
     */
    cleanForSave() {},

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
                        lang.value = pyToJsLocale(lang.value);
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
        // Animations for which the "On Scroll" and "Direction" options are not
        // available.
        this.limitedAnimations = ['o_anim_flash', 'o_anim_pulse', 'o_anim_shake', 'o_anim_tada', 'o_anim_flip_in_x', 'o_anim_flip_in_y'];
        this.isAnimatedText = this.$target.hasClass('o_animated_text');
        this.$optionsSection = this.$overlay.data('$optionsSection');
        this.$scrollingElement = $().getScrollingElement(this.ownerDocument);
        this.$overlay[0].querySelector(".o_handles").classList.toggle("pe-none", this.isAnimatedText);
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
            this.options.wysiwyg.toolbarEl.append(this.$el[0]);
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
    /**
     * @override
     */
    cleanForSave() {
        if (this.$target[0].closest('.o_animate')) {
            // As images may have been added in an animated element, we must
            // remove the lazy loading on them.
            this._toggleImagesLazyLoading(false);
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
        if (params.forceAnimation && params.name !== 'o_anim_no_effect_opt' && previewMode !== 'reset') {
            this._forceAnimation();
        }
        if (params.isAnimationTypeSelection) {
            this.$target[0].classList.toggle("o_animate_preview", this.$target[0].classList.contains("o_animate"));
        }
    },
    /**
     * @override
     */
    async selectDataAttribute(previewMode, widgetValue, params) {
        await this._super(...arguments);
        if (params.forceAnimation) {
            this._forceAnimation();
        }
    },
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
        if (params.activeValue === "o_animate_on_hover") {
            this.trigger_up("option_update", {
                optionName: "ImageTools",
                name: "disable_hover_effect",
            });
        }
        if ((!params.activeValue || params.activeValue === "o_animate_on_hover")
                && widgetValue && widgetValue !== "onHover") {
            // If "Animation" was on "None" or "o_animate_on_hover" and it is no
            // longer, it is set to "fade_in" by default.
            targetClassList.add('o_anim_fade_in');
            this._toggleImagesLazyLoading(false);
        }
        if (!widgetValue || widgetValue === "onHover") {
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
        if (widgetValue === "onHover") {
            // Pause the history until the hover effect is applied in
            // "setImgShapeHoverEffect". This prevents saving the intermediate
            // steps done (in a tricky way) up to that point.
            this.options.wysiwyg.odooEditor.historyPauseSteps();
            this.trigger_up("option_update", {
                optionName: "ImageTools",
                name: "enable_hover_effect",
            });
        }
    },
    /**
     * Sets the animation intensity.
     *
     * @see this.selectClass for parameters
     */
    animationIntensity(previewMode, widgetValue, params) {
        this.$target[0].style.setProperty('--wanim-intensity', widgetValue);
        this._forceAnimation();
    },

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
            this.trigger_up('cover_update', {
                overlayVisible: true,
            });
            this.$scrollingElement[0].classList.add('o_wanim_overflow_xy_hidden');
            this.$target.css('animation-name', '');
            this.$target.one('webkitAnimationEnd oanimationend msAnimationEnd animationend', () => {
                this.$scrollingElement[0].classList.remove('o_wanim_overflow_xy_hidden');
                this.$target.removeClass('o_animating');
            });
        }
    },
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
                const [hoverEffectOverlayWidget] = this._requestUserValueWidgets("hover_effect_overlay_opt");
                if (hoverEffectOverlayWidget) {
                    const hoverEffectWidget = hoverEffectOverlayWidget.getParent();
                    const imageToolsOpt = hoverEffectWidget.getParent();
                    return (
                        imageToolsOpt._canHaveHoverEffect()
                        && !await weUtils.isImageCorsProtected(this.$target[0])
                    );
                }
                return false;
            }
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
    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === 'animationIntensity') {
            return window.getComputedStyle(this.$target[0]).getPropertyValue('--wanim-intensity');
        }
        return this._super(...arguments);
    },
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
    },
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
options.registry.TextHighlight = options.Class.extend({
    custom_events: Object.assign({}, options.Class.prototype.custom_events, {
        "user_value_widget_opening": "_onWidgetOpening",
    }),
    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this.leftPanelEl = this.$overlay.data("$optionsSection")[0];
        // Reduce overlay opacity for more highlight visibility on small text.
        this.$overlay[0].style.opacity = "0.25";
        this.$overlay[0].querySelector(".o_handles").classList.add("pe-none");
    },
    /**
     * Move "Text Effect" options to the editor's toolbar.
     *
     * @override
     */
    onFocus() {
        this.options.wysiwyg.toolbarEl.append(this.$el[0]);
    },
    /**
     * @override
     */
    onBlur() {
        this.leftPanelEl.appendChild(this.el);
    },
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
        this._super(...arguments);
    },

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
    },

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
    },
    /**
     * Used to set the highlight effect DOM structure on the targeted text
     * content.
     *
     * @private
     */
    _autoAdaptHighlights() {
        this.trigger_up("snippet_edition_request", { exec: async () =>
            await this._refreshPublicWidgets($(this.options.wysiwyg.odooEditor.editable))
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * To draw highlight SVGs for `<we-select/>` preview, we need to open the
     * widget (we need correct size values from `getBoundingClientRect()`).
     * This code will build the highlight preview the first time we open the
     * `<we-select/>`.
     *
     * @private
     */
    _onWidgetOpening(ev) {
        const target = ev.target;
        // Only when there is no highlight SVGs.
        if (target.getName() === "text_highlight_opt" && !target.el.querySelector("svg")) {
            const weToggler = target.el.querySelector("we-toggler");
            weToggler.classList.add("active");
            [...target.el.querySelectorAll("we-button[data-set-text-highlight] div")].forEach(weBtnEl => {
                weBtnEl.textContent = "Text";
                // Get the text highlight linked to each `<we-button/>`
                // and apply it to its text content.
                weBtnEl.append(drawTextHighlightSVG(weBtnEl, weBtnEl.parentElement.dataset.setTextHighlight));
            });
        }
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
 * Hides delete and clone buttons for Mega Menu block.
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

options.registry.GridImage = options.Class.extend({

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
    },

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
    },
    /**
     * @override
     */
    _computeVisibility() {
        // Special conditions for the hover effects.
        const hasSquareShape = this.$target[0].dataset.shape === "web_editor/geometric/geo_square";
        const effectAllowsOption = !["dolly_zoom", "outline", "image_mirror_blur"]
            .includes(this.$target[0].dataset.hoverEffect);

        return this._super(...arguments)
            && !!this._getImageGridItem()
            && (!('shape' in this.$target[0].dataset)
                || hasSquareShape && effectAllowsOption);
    },
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
        return this._super(...arguments);
    },
});

options.registry.GalleryElement = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Allows to change the position of an item on the set.
     *
     * @see this.selectClass for parameters
     */
    position(previewMode, widgetValue, params) {
        const carouselOptionName = this.$target[0].parentNode.parentNode.classList.contains("s_carousel_intro") ? "CarouselIntro" : "Carousel";
        const optionName = this.$target[0].classList.contains("carousel-item") ? carouselOptionName
            : "GalleryImageList";
        const itemEl = this.$target[0];
        this.trigger_up("option_update", {
            optionName: optionName,
            name: "reorder_items",
            data: {
                itemEl: itemEl,
                position: widgetValue,
            },
        });
    },
});

options.registry.Button = options.Class.extend({
    /**
     * @override
     */
    init() {
        this._super(...arguments);
        const isUnremovableButton = this.$target[0].classList.contains("oe_unremovable");
        this.forceDuplicateButton = !isUnremovableButton;
        this.forceNoDeleteButton = isUnremovableButton;
    },
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
    },
    /**
     * @override
     */
    onClone(options) {
        // Only if the button is cloned, not if a snippet containing that button
        // is cloned.
        if (options.isCurrent) {
            this._adaptButtons(false);
        }
    },

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
    },
});

options.registry.layout_column.include({
    /**
     * @override
     */
    _isMobile() {
        return wUtils.isMobile(this);
    },
});

options.registry.SnippetMove.include({
    /**
     * @override
     */
    _isMobile() {
        return wUtils.isMobile(this);
    },
});

export default {
    UrlPickerUserValueWidget: UrlPickerUserValueWidget,
    FontFamilyPickerUserValueWidget: FontFamilyPickerUserValueWidget,
};
