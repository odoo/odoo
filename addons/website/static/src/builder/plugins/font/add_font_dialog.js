import { useLayoutEffect, useRef } from "@web/owl2/utils";
import { rpc } from "@web/core/network/rpc";
import { Component, proxy } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { Dialog } from "@web/core/dialog/dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

class GoogleFontAutoComplete extends AutoComplete {
    setup() {
        super.setup();
        this.inputRef = useRef("input");
        this.sourcesListRef = useRef("sourcesList");
        useLayoutEffect(
            (el) => {
                el.setAttribute("id", "google_font");
            },
            () => [this.inputRef.el]
        );
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

// These Google Fonts weight names should stay in sync with FONT_WEIGHT_OPTIONS
// in theme_tab_plugin.js.
const UPLOADED_FONT_WEIGHT_BY_NAME = {
    thin: 100,
    "extra light": 200,
    light: 300,
    regular: 400,
    normal: 400,
    medium: 500,
    "semi bold": 600,
    bold: 700,
    "extra bold": 800,
    black: 900,
};

const EXPLICIT_FONT_WEIGHT_REGEX = /(?:^|[^0-9])(100|200|300|400|500|600|700|800|900)(?=$|[^0-9])/;
const NORMALIZED_FONT_WEIGHT_REGEX =
    /(?:^|[^a-z])(extra light|semi bold|extra bold|thin|light|regular|normal|medium|bold|black)(?: italic| oblique)?$/;

/**
 * Normalizes uploaded font filenames so weight/style keywords can be matched
 * consistently across extension-based, dash/underscore-separated, and camel-cased names.
 */
function normalizeUploadedFontName(fontName) {
    return fontName
        .replace(/\.[^.]+$/, "")
        .replace(/([a-z])([A-Z])/g, "$1 $2")
        .replace(/[-_]+/g, " ")
        .trim()
        .toLowerCase();
}

function getUploadedFontWeight(fontName) {
    const normalizedFontName = normalizeUploadedFontName(fontName);
    const explicitWeight = normalizedFontName.match(EXPLICIT_FONT_WEIGHT_REGEX);
    if (explicitWeight) {
        return parseInt(explicitWeight[1]);
    }
    const namedWeight = normalizedFontName.match(NORMALIZED_FONT_WEIGHT_REGEX);
    return namedWeight && UPLOADED_FONT_WEIGHT_BY_NAME[namedWeight[1]];
}

export class AddFontDialog extends Component {
    static template = "website.dialog.addFont";
    static components = { GoogleFontAutoComplete, Dialog };
    static props = {
        close: Function,
        allFonts: Array,
        googleFonts: Array,
        googleLocalFonts: Array,
        uploadedLocalFonts: Array,
        variable: String,
        customize: Function,
        reloadEditor: Function,
    };
    state = proxy({
        valid: true,
        loading: false,
        googleFontFamily: undefined,
        googleServe: !this.env.services.website.currentWebsite.cookies_bar,
        uploadedFontName: undefined,
        uploadedFonts: [],
        uploadedFontFaces: undefined,
        previewText: _t("The quick brown fox jumps over the lazy dog."),
    });
    setup() {
        this.fileInput = useRef("fileInput");
        this.dialog = useService("dialog");
        this.orm = useService("orm");
    }

    async onClickSave() {
        if (this.state.loading) {
            return;
        }
        this.state.loading = true;
        const shouldClose = await this.save(this.state);
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
        return [
            {
                options: async (term) => {
                    if (!this.googleFontList) {
                        await rpc("/website/google_font_metadata").then((data) => {
                            this.googleFontList = data.familyMetadataList.map(
                                (font) => font.family
                            );
                        });
                    }
                    const lowerCaseTerm = term.toLowerCase();
                    const filtered = this.googleFontList.filter((value) =>
                        value.toLowerCase().includes(lowerCaseTerm)
                    );
                    return filtered.map((fontFamilyName) => ({
                        label: fontFamilyName,
                        onSelect: () => this.onGoogleFontSelect(fontFamilyName),
                    }));
                },
            },
        ];
    }
    async onGoogleFontSelect(fontFamily) {
        this.fileInput.el.value = "";
        this.state.uploadedFonts = [];
        this.state.uploadedFontName = undefined;
        this.state.uploadedFontFaces = undefined;
        try {
            const result = await fetch(
                `https://fonts.googleapis.com/css?family=${encodeURIComponent(
                    fontFamily
                )}:100,100i,200,200i,300,300i,400,400i,500,500i,600,600i,700,700i,800,800i,900,900i`,
                { method: "HEAD" }
            );
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
            const base64 = e.target.result.split(",")[1];
            rpc("/website/theme_upload_font", {
                name: file.name,
                data: base64,
            }).then((result) => {
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
            font.weight = getUploadedFontWeight(font.name);
            font.style = font.isItalic ? "italic" : "normal";
            if (font.weight) {
                targetFonts[`${font.weight}${font.style}`] = font;
            }
        }
        if (!Object.values(targetFonts).some((font) => font.weight === 400)) {
            // Keep font with shortest name.
            shortestNamedFont.weight = 400;
            shortestNamedFont.style = "normal";
            targetFonts["400normal"] = shortestNamedFont;
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
        let styleEl = document.head.querySelector(
            `style[id='WebsiteThemeFontPreview-${baseFontName}']`
        );
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
    async save(state) {
        const uploadedFontName = state.uploadedFontName;
        const uploadedFontFaces = state.uploadedFontFaces;
        let font = undefined;
        if (uploadedFontName && uploadedFontFaces) {
            const fontExistsLocally = this.props.uploadedLocalFonts.some(
                (localFont) => localFont.split(":")[0] === `'${uploadedFontName}'`
            );
            if (fontExistsLocally) {
                this.dialog.add(ConfirmationDialog, {
                    title: _t("Font exists"),
                    body: _t(
                        "This uploaded font already exists.\nTo replace an existing font, remove it first."
                    ),
                });
                return;
            }
            const homonymGoogleFontExists =
                this.props.googleFonts.some((font) => font === uploadedFontName) ||
                this.props.googleLocalFonts.some(
                    (font) => font.split(":")[0] === `'${uploadedFontName}'`
                );
            if (homonymGoogleFontExists) {
                this.dialog.add(ConfirmationDialog, {
                    title: _t("Font name already used"),
                    body: _t(
                        "A font with the same name already exists.\nTry renaming the uploaded file."
                    ),
                });
                return;
            }
            // Create attachment.
            const [fontCssId] = await this.orm.call("ir.attachment", "create_unique", [
                [
                    {
                        name: uploadedFontName,
                        description: `CSS font face for ${uploadedFontName}`,
                        raw: btoa(uploadedFontFaces),
                        res_model: "ir.attachment",
                        mimetype: "text/css",
                        public: true,
                    },
                ],
            ]);
            this.props.uploadedLocalFonts.push(`'${uploadedFontName}': ${fontCssId}`);
            font = uploadedFontName;
        } else {
            let isValidFamily = false;
            font = state.googleFontFamily;

            try {
                const result = await fetch(
                    "https://fonts.googleapis.com/css?family=" +
                        encodeURIComponent(font) +
                        ":100,100i,200,200i,300,300i,400,400i,500,500i,600,600i,700,700i,800,800i,900,900i",
                    { method: "HEAD" }
                );
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
            const fontExistsLocally = this.props.googleLocalFonts.some(
                (localFont) => localFont.split(":")[0] === fontName
            );
            const fontExistsOnServer = this.props.allFonts.includes(fontName);
            const preventFontAddition =
                fontExistsLocally || (fontExistsOnServer && googleFontServe);
            if (preventFontAddition) {
                this.dialog.add(ConfirmationDialog, {
                    title: _t("Font exists"),
                    body: _t(
                        "This font already exists, you can only add it as a local font to replace the server version."
                    ),
                });
                return;
            }
            if (googleFontServe) {
                this.props.googleFonts.push(font);
            } else {
                this.props.googleLocalFonts.push(`'${font}': ''`);
            }
        }
        await this.props.customize({
            values: { [this.props.variable]: `'${font}'` },
            googleFonts: this.props.googleFonts,
            googleLocalFonts: this.props.googleLocalFonts,
            uploadedLocalFonts: this.props.uploadedLocalFonts,
        });
        const styleEl = document.head.querySelector(`[id='WebsiteThemeFontPreview-${font}']`);
        if (styleEl) {
            delete styleEl.dataset.fontPreview;
        }
        await this.props.reloadEditor();
        return true;
    }
}

export function showAddFontDialog(dialog, fontsData, variable, customize, reloadEditor) {
    dialog.add(
        AddFontDialog,
        {
            allFonts: fontsData.allFonts,
            googleFonts: fontsData.googleFonts,
            googleLocalFonts: fontsData.googleLocalFonts,
            uploadedLocalFonts: fontsData.uploadedLocalFonts,
            variable,
            customize,
            reloadEditor,
        },
        {
            onClose: () => {
                for (const el of document.head.querySelectorAll("[data-font-preview]")) {
                    el.remove();
                }
            },
        }
    );
}
