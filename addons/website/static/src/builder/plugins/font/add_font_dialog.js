import { rpc } from "@web/core/network/rpc";
import { Component, proxy, signal, useProps, useScope, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { Dialog } from "@web/core/dialog/dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Switch } from "@html_editor/components/switch/switch";

const FONT_PREVIEW_BATCH_SIZE = 8;

class GoogleFontAutoComplete extends AutoComplete {
    get dropdownOptions() {
        const options = super.dropdownOptions;
        return {
            ...options,
            position: "bottom-fit",
            onPositioned: (listEl, solution) => {
                options.onPositioned?.(listEl, solution);
                // Restore scrolling once the reopened menu has its final size.
                if (this.restoreScrollTop !== undefined) {
                    listEl.scrollTop = this.restoreScrollTop;
                    this.restoreScrollTop = undefined;
                }
                // Start loading three menu heights before reaching the bottom,
                // so that fast scrolling rarely has to wait for fonts.
                listEl.onscroll = () => {
                    if (listEl.scrollTop + 4 * listEl.clientHeight >= listEl.scrollHeight) {
                        this.loadMoreFonts();
                    }
                };
                // Also fill menus with too few options to scroll.
                listEl.onscroll();
            },
        };
    }

    loadSources(useInput) {
        // Reopen the list where it was left, so that users can preview a font
        // and come back to compare it with the next ones.
        if (!useInput && this.sources.length) {
            this.restoreScrollTop = this.lastScrollTop;
            return;
        }
        this.fontTerm = useInput ? this.inputRef().value.trim() : "";
        return super.loadSources(useInput).catch((error) => {
            this.close();
            this.sources.splice(0);
            throw error;
        });
    }

    close() {
        this.lastScrollTop = this.listRef()?.scrollTop;
        super.close();
    }

    async loadMoreFonts() {
        const source = this.sources[0];
        if (!source || source.isLoading || source.isLoadingMore || source.isComplete) {
            return;
        }
        source.isLoadingMore = true;
        const offset = source.options.length;
        // Show that more fonts are coming while the next batch loads.
        source.options.push(
            this.makeOption({ label: _t("Loading..."), data: { isLoading: true } })
        );
        const options = await this.props.sources[0].options(this.fontTerm, offset);
        source.isLoadingMore = false;
        source.isComplete = options.length < FONT_PREVIEW_BATCH_SIZE;
        source.options.splice(-1, 1, ...options.map((option) => this.makeOption(option)));
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
    static components = { GoogleFontAutoComplete, Dialog, Switch };
    props = useProps({
        close: t.function(),
        allFonts: t.array(),
        googleFonts: t.array(),
        googleLocalFonts: t.array(),
        uploadedLocalFonts: t.array(),
        variable: t.string(),
        customize: t.function(),
        reloadEditor: t.function(),
    });
    state = proxy({
        valid: true,
        loading: false,
        googleFontFamily: undefined,
        googleFontWeights: [],
        googleServe: false,
        uploadedFontName: undefined,
        uploadedFonts: [],
        uploadedFontFaces: undefined,
        previewText: "",
        previewFontSize: "20",
    });
    defaultPreviewText = _t("The quick brown fox jumps over the lazy dog.");
    previewFontSizes = ["14", "16", "20", "24", "32", "40", "56"];
    fileInput = signal.ref();
    scope = useScope();
    // Share pending and completed font loads between searches.
    fontLoads = new Map();
    setup() {
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        // Open Google connections while the font metadata is being fetched.
        for (const url of ["https://fonts.googleapis.com", "https://fonts.gstatic.com"]) {
            const linkEl = document.createElement("link");
            linkEl.rel = "preconnect";
            linkEl.href = url;
            if (url === "https://fonts.gstatic.com") {
                // Font files use CORS, unlike the Google Fonts stylesheet.
                linkEl.crossOrigin = "";
            }
            linkEl.dataset.fontPreview = true;
            document.head.appendChild(linkEl);
        }
        // Start loading the first fonts before the list is opened.
        this.loadFontOptions("", 0).catch(() => {});
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
                optionSlot: "font",
                options: (term, offset = 0) => this.loadFontOptions(term, offset),
            },
        ];
    }
    async loadFontOptions(term, offset) {
        this.googleFontListPromise ||= rpc("/website/google_font_metadata")
            .then((data) => {
                // List the most popular fonts first.
                data.familyMetadataList.sort((a, b) => a.popularity - b.popularity);
                this.googleFontList = data.familyMetadataList.map(({ family, fonts }) => {
                    const variants = Object.keys(fonts);
                    // Some families only have a light, bold or italic variant.
                    const variant = fonts["400"] ? "400" : variants[0];
                    // Google marks italic variants with an "i" suffix, e.g.
                    // "400i".
                    return {
                        family,
                        weight: parseInt(variant),
                        style: variant.endsWith("i") ? "italic" : "normal",
                        weights: variants.map((fontVariant) => parseInt(fontVariant)),
                    };
                });
            })
            .catch((error) => {
                this.googleFontListPromise = undefined;
                throw error;
            });
        await this.googleFontListPromise;
        // The dialog may have closed while the metadata request was pending.
        if (this.scope.isDestroyed()) {
            return [];
        }
        const lowerCaseTerm = term.toLowerCase();
        const fonts = this.googleFontList
            .filter(({ family }) => family.toLowerCase().includes(lowerCaseTerm))
            // List the names starting with the search first. The sort keeps
            // the popularity order within each group.
            .sort(
                (a, b) =>
                    b.family.toLowerCase().startsWith(lowerCaseTerm) -
                    a.family.toLowerCase().startsWith(lowerCaseTerm)
            )
            .slice(offset, offset + FONT_PREVIEW_BATCH_SIZE);
        const fontsToLoad = fonts.filter(({ family }) => !this.fontLoads.has(family));
        if (fontsToLoad.length) {
            // One stylesheet per batch: each added stylesheet restyles the
            // page, which would make scrolling the list less smooth.
            const linkEl = document.createElement("link");
            linkEl.rel = "stylesheet";
            const families = fontsToLoad
                .map(({ family, weight, style }) => {
                    const italic = style === "italic" ? 1 : 0;
                    return `family=${encodeURIComponent(family)}:ital,wght@${italic},${weight}`;
                })
                .join("&");
            // Only download the glyphs needed by the names in this batch.
            linkEl.href = `https://fonts.googleapis.com/css2?${families}&text=${encodeURIComponent(
                fontsToLoad.map(({ family }) => family).join("")
            )}`;
            linkEl.dataset.fontPreview = true;
            const cssLoaded = new Promise((resolve) => {
                linkEl.onload = linkEl.onerror = resolve;
            });
            document.head.appendChild(linkEl);
            for (const { family, weight, style } of fontsToLoad) {
                this.fontLoads.set(
                    family,
                    cssLoaded.then(() =>
                        // A failed font still lists its name, in the default
                        // font.
                        document.fonts
                            .load(`${style} ${weight} 1rem ${JSON.stringify(family)}`, family)
                            .catch(() => {})
                    )
                );
            }
        }
        // The stylesheet can load before its font files, so wait for both.
        await Promise.all(fonts.map(({ family }) => this.fontLoads.get(family)));
        return fonts.map(({ family, weight, style, weights }) => ({
            label: family,
            data: {
                style:
                    `font-family: ${JSON.stringify(family)}; font-size: 1rem; ` +
                    `font-weight: ${weight}; font-style: ${style}`,
            },
            onSelect: () => this.onGoogleFontSelect(family, weights),
        }));
    }
    onGoogleFontSelect(fontFamily, weights) {
        this.fileInput().value = "";
        this.state.uploadedFonts = [];
        this.state.uploadedFontName = undefined;
        this.state.uploadedFontFaces = undefined;
        const linkId = `previewFont${fontFamily}`;
        if (!document.getElementById(linkId)) {
            const linkEl = document.createElement("link");
            linkEl.id = linkId;
            linkEl.rel = "stylesheet";
            linkEl.href = `https://fonts.googleapis.com/css?family=${encodeURIComponent(
                fontFamily
            )}:100,100i,200,200i,300,300i,400,400i,500,500i,600,600i,700,700i,800,800i,900,900i`;
            linkEl.dataset.fontPreview = true;
            linkEl.onerror = () => {
                // Remove the link so that selecting the font again retries.
                linkEl.remove();
                // An earlier selection failing must not clear the current one.
                if (this.state.googleFontFamily === fontFamily) {
                    this.state.googleFontFamily = undefined;
                }
            };
            document.head.appendChild(linkEl);
        }
        this.state.googleFontFamily = fontFamily;
        this.state.googleFontWeights = weights;
    }
    isPreviewWeightAvailable(weight) {
        // Uploaded fonts do not tell which weights they provide.
        return !this.state.googleFontFamily || this.state.googleFontWeights.includes(weight);
    }
    onGoogleFontInput({ inputValue }) {
        if (!inputValue.trim()) {
            this.state.googleFontFamily = undefined;
        }
    }
    async onUploadChange(e) {
        this.state.googleFontFamily = undefined;
        const file = this.fileInput().files[0];
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
                // Create a copy of the font to not mangle the original font
                // when setting the weight and style later
                shortestNamedFont = JSON.parse(JSON.stringify(font));
            }
            font.isItalic = /italic/i.test(font.name);
            font.weight = getUploadedFontWeight(font.name);
            font.style = font.isItalic ? "italic" : "normal";
            if (font.weight) {
                targetFonts[`${font.weight}${font.style}`] = font;
            }
        }
        if (!Object.values(targetFonts).some((font) => font.weight === 400)) {
            // Keep font with the shortest name.
            shortestNamedFont.weight = 400;
            shortestNamedFont.style = "normal";
            targetFonts["400normal"] = shortestNamedFont;
        }
        const fontFaces = [];
        for (const font of Object.values(targetFonts)) {
            fontFaces.push(`@font-face{
                font-family: "${baseFontName}";
                font-style: ${font.style};
                font-weight: ${font.weight};
                font-display: swap;
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
            await this.orm.write("ir.attachment", [fontCssId], {
                url: `/web/font/${fontCssId}/${uploadedFontName}`,
            });
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
