import { rpc } from "@web/core/network/rpc";
import { Component, onWillDestroy, proxy, signal, useProps, useScope, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { Dialog } from "@web/core/dialog/dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Switch } from "@html_editor/components/switch/switch";

const FONT_PREVIEW_BATCH_SIZE = 8;

class GoogleFontAutoComplete extends AutoComplete {
    // Keep loaded options and scroll positions until the dialog is closed.
    fontLists = new Map();

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
                // Start loading one menu height before reaching the bottom.
                const loadMore = () => {
                    if (listEl.scrollTop + 2 * listEl.clientHeight >= listEl.scrollHeight) {
                        this.loadMoreFonts();
                    }
                };
                listEl.onscroll = loadMore;
                // Also fill menus with too few options to scroll.
                loadMore();
            },
        };
    }

    async loadSources(useInput) {
        // Give each search a new ID. If another search starts before this one
        // finishes, its results must not replace the new search's list.
        const requestId = (this.fontRequestId || 0) + 1;
        this.fontRequestId = requestId;
        if (this.activeFontList && this.listRef()) {
            this.activeFontList.scrollTop = this.listRef().scrollTop;
        }
        // Reopen the previous search instead of filtering by the selected name.
        const term = useInput
            ? this.inputRef().value.trim()
            : (this.props.value && this.selectedFontTerm) || "";
        const cachedList = this.fontLists.get(term);
        if (cachedList) {
            const source = this.makeSource(this.props.sources[0]);
            source.options = cachedList.options;
            this.sources.splice(0, this.sources.length, source);
            this.state.activeSourceOption = null;
            this.activeFontList = cachedList;
            this.restoreScrollTop = cachedList.scrollTop;
            return;
        }
        // Pause pagination until the new search has loaded its first batch.
        this.activeFontList = undefined;
        await super.loadSources(useInput);
        if (requestId === this.fontRequestId) {
            const list = {
                term,
                options: this.sources[0].options,
                nextOffset: FONT_PREVIEW_BATCH_SIZE,
                hasMore: true,
                isLoading: false,
                scrollTop: 0,
            };
            this.fontLists.set(term, list);
            this.activeFontList = list;
            this.loadMoreFonts();
        }
    }

    async loadMoreFonts() {
        const list = this.activeFontList;
        // Switching searches must not start the same batch twice for one list.
        if (!list || list.isLoading || !list.hasMore || !this.isOpened) {
            return;
        }
        list.isLoading = true;
        try {
            const options = await this.props.sources[0].options(list.term, list.nextOffset);
            // The user may have changed searches or closed the menu meanwhile.
            if (list !== this.activeFontList || !this.isOpened) {
                return;
            }
            // Failed fonts still occupy a slot in the requested batch.
            list.nextOffset += FONT_PREVIEW_BATCH_SIZE;
            list.hasMore = options.hasMore;
            list.options.push(...options.map((option) => this.makeOption(option)));
        } finally {
            list.isLoading = false;
        }
    }

    selectOption(option) {
        this.selectedFontTerm = this.activeFontList?.term;
        super.selectOption(option);
    }

    close() {
        if (this.activeFontList && this.listRef()) {
            this.activeFontList.scrollTop = this.listRef().scrollTop;
        }
        super.close();
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
        this.googleFontListPromise = rpc("/website/google_font_metadata").then((data) => {
            this.googleFontList = data.familyMetadataList.map(({ family, fonts }) => {
                // Some families only provide a light, bold or italic variant.
                const variant = fonts["400"] ? "400" : Object.keys(fonts)[0];
                // Google marks italic variants with an "i" suffix, e.g. "400i".
                return {
                    family,
                    weight: parseInt(variant),
                    style: variant.endsWith("i") ? "italic" : "normal",
                };
            });
        });
        // Start the first batch when the dialog opens, before opening the list.
        this.firstFontsPromise = this.googleFontListPromise.then(() => this.loadFontOptions("", 0));
        // Clean up at destruction so late loaders cannot add styles afterwards.
        onWillDestroy(() => {
            for (const previewEl of document.head.querySelectorAll("[data-font-preview]")) {
                previewEl.remove();
            }
        });
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
                options: (term, offset = 0) =>
                    term || offset ? this.loadFontOptions(term, offset) : this.firstFontsPromise,
            },
        ];
    }
    async loadFontOptions(term, offset) {
        await this.googleFontListPromise;
        // The dialog may have closed while the metadata request was pending.
        if (this.scope.isDestroyed()) {
            return [];
        }
        const filtered = this.googleFontList.filter(({ family }) =>
            family.toLowerCase().includes(term.toLowerCase())
        );
        const fonts = filtered.slice(offset, offset + FONT_PREVIEW_BATCH_SIZE);
        const fontsToLoad = fonts.filter(({ family }) => !this.fontLoads.has(family));
        if (fontsToLoad.length) {
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
            )}&display=swap`;
            linkEl.dataset.fontPreview = true;
            const cssReady = new Promise((resolve) => {
                linkEl.onload = () => resolve(true);
                linkEl.onerror = () => resolve(false);
                document.head.appendChild(linkEl);
            });
            for (const { family, weight, style } of fontsToLoad) {
                this.fontLoads.set(
                    family,
                    cssReady.then(async (ready) => {
                        if (!ready || this.scope.isDestroyed()) {
                            return false;
                        }
                        try {
                            const faces = await document.fonts.load(
                                `${style} ${weight} 1rem ${JSON.stringify(family)}`,
                                family
                            );
                            return !!faces.length;
                        } catch {
                            return false;
                        }
                    })
                );
            }
        }
        // The stylesheet can load before its font files, so wait for both.
        const loaded = await Promise.all(fonts.map(({ family }) => this.fontLoads.get(family)));
        const options = fonts
            .filter((font, index) => loaded[index])
            .map(({ family, weight, style }) => ({
                label: family,
                data: {
                    style:
                        `font-family: ${JSON.stringify(family)}; font-size: 1rem; ` +
                        `font-weight: ${weight}; font-style: ${style}`,
                },
                onSelect: () => this.onGoogleFontSelect(family),
            }));
        options.hasMore = offset + FONT_PREVIEW_BATCH_SIZE < filtered.length;
        return options;
    }
    onGoogleFontSelect(fontFamily) {
        this.fileInput().value = "";
        this.state.uploadedFonts = [];
        this.state.uploadedFontName = undefined;
        this.state.uploadedFontFaces = undefined;
        const fontUrl = `https://fonts.googleapis.com/css?family=${encodeURIComponent(
            fontFamily
        )}:100,100i,200,200i,300,300i,400,400i,500,500i,600,600i,700,700i,800,800i,900,900i`;
        const linkId = `previewFont${fontFamily}`;
        let linkEl = document.getElementById(linkId);
        if (!linkEl) {
            linkEl = document.createElement("link");
            linkEl.id = linkId;
            linkEl.rel = "stylesheet";
            linkEl.dataset.fontPreview = true;
            document.head.appendChild(linkEl);
        }
        linkEl.onerror = () => {
            // An earlier selection failing must not clear the current one.
            if (this.state.googleFontFamily === fontFamily) {
                this.state.googleFontFamily = undefined;
            }
        };
        // Include the name: this stylesheet also applies to the dropdown entry.
        linkEl.href = `${fontUrl}&text=${encodeURIComponent(
            (this.state.previewText || this.defaultPreviewText) + fontFamily
        )}`;
        this.previewFontLinkEl = linkEl;
        this.fullPreviewFontUrl = fontUrl;
        this.previewFontIsSubset = true;
        this.state.googleFontFamily = fontFamily;
    }
    onPreviewTextInput() {
        if (this.state.googleFontFamily && this.previewFontIsSubset) {
            // Remove the text subset once to avoid fetching CSS on every edit.
            this.previewFontLinkEl.href = this.fullPreviewFontUrl;
            this.previewFontIsSubset = false;
        }
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
    dialog.add(AddFontDialog, {
        allFonts: fontsData.allFonts,
        googleFonts: fontsData.googleFonts,
        googleLocalFonts: fontsData.googleLocalFonts,
        uploadedLocalFonts: fontsData.uploadedLocalFonts,
        variable,
        customize,
        reloadEditor,
    });
}
