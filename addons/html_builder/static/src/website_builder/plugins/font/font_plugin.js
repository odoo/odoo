import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { Cache } from "@web/core/utils/cache";
import { loadCSS } from "@web/core/assets";
import { getCSSVariableValue } from "@html_builder/utils/utils_css";
import { showAddFontDialog } from "./add_font_dialog";

// TODO Website-specific
class FontPlugin extends Plugin {
    static id = "websiteFont";
    static shared = ["addFont", "deleteFont", "getFontsData"];
    static dependencies = ["savePlugin", "themeTab"];
    resources = {
        // Lists CSS variables that will be reset when a font is deleted if
        // they refer to that font.
        fontCssVariables: [
            "font",
            "headings-font",
            "h2-font",
            "h3-font",
            "h4-font",
            "h5-font",
            "h6-font",
            "display-1-font",
            "display-2-font",
            "display-3-font",
            "display-4-font",
            "buttons-font",
        ],
    };
    setup() {
        this.fontsCache = new Cache(this._fetchFonts.bind(this), JSON.stringify);
    }
    destroy() {
        super.destroy();
        this.fontsCache.invalidate();
    }
    async addFont() {
        const fontsData = await this.getFontsData();
        showAddFontDialog(this.services.dialog, fontsData, this.customizeFonts.bind(this));
    }
    async customizeFonts({ values = {}, googleFonts, googleLocalFonts, uploadedLocalFonts }) {
        if (googleFonts.length) {
            values["google-fonts"] = "('" + googleFonts.join("', '") + "')";
        } else {
            values["google-fonts"] = "null";
        }
        if (googleLocalFonts.length) {
            values["google-local-fonts"] = "(" + googleLocalFonts.join(", ") + ")";
        } else {
            values["google-local-fonts"] = "null";
        }
        if (uploadedLocalFonts.length) {
            values["uploaded-local-fonts"] = "(" + uploadedLocalFonts.join(", ") + ")";
        } else {
            values["uploaded-local-fonts"] = "null";
        }
        await this.dependencies.themeTab.makeSCSSCusto(
            "/website/static/src/scss/options/user_values.scss",
            values
        );
        this.fontsCache.invalidate();
        // TODO reloadEditor: true
        await this.dependencies.savePlugin.save(/* not in translation */);
    }
    async deleteFont(font) {
        const { googleFonts, googleLocalFonts, uploadedLocalFonts } = await this.getFontsData();
        const values = {};

        // Remove Google font
        const fontIndex = font.indexForType;
        const localFont = font.type;
        let fontName;
        if (localFont === "uploaded") {
            const font = uploadedLocalFonts[fontIndex].split(":");
            // Remove double quotes
            fontName = font[0].substring(1, font[0].length - 1);
            values["delete-font-attachment-id"] = font[1];
            uploadedLocalFonts.splice(fontIndex, 1);
        } else if (localFont === "google") {
            const googleFont = googleLocalFonts[fontIndex].split(":");
            // Remove double quotes
            fontName = googleFont[0].substring(1, googleFont[0].length - 1);
            values["delete-font-attachment-id"] = googleFont[1];
            googleLocalFonts.splice(fontIndex, 1);
        } else {
            fontName = googleFonts[fontIndex];
            googleFonts.splice(fontIndex, 1);
        }

        // Adapt font variable indexes to the removal
        const style = window.getComputedStyle(this.document.documentElement);
        this.getResource("fontCssVariables").forEach((variable) => {
            const value = getCSSVariableValue(variable, style);
            if (value.substring(1, value.length - 1) === fontName) {
                // If an element is using the google font being removed, reset
                // it to the theme default.
                values[variable] = "null";
            }
        });
        await this.customizeFonts({
            values: values,
            googleFonts: googleFonts,
            googleLocalFonts: googleLocalFonts,
            uploadedLocalFonts: uploadedLocalFonts,
        });
    }
    async getFontsData() {
        return this.fontsCache.read({});
    }
    async _fetchFonts() {
        const style = window.getComputedStyle(this.document.documentElement);
        const nbFonts = parseInt(getCSSVariableValue("number-of-fonts", style));
        // User fonts served by google server.
        const googleFontsProperty = getCSSVariableValue("google-fonts", style);
        let googleFonts = googleFontsProperty ? googleFontsProperty.split(/\s*,\s*/g) : [];
        googleFonts = googleFonts.map((font) => font.substring(1, font.length - 1)); // Unquote
        // Local user fonts.
        const googleLocalFontsProperty = getCSSVariableValue("google-local-fonts", style);
        const googleLocalFonts = googleLocalFontsProperty
            ? googleLocalFontsProperty.slice(1, -1).split(/\s*,\s*/g)
            : [];
        const uploadedLocalFontsProperty = getCSSVariableValue("uploaded-local-fonts", style);
        const uploadedLocalFonts = uploadedLocalFontsProperty
            ? uploadedLocalFontsProperty.slice(1, -1).split(/\s*,\s*/g)
            : [];
        // If a same font exists both remotely and locally, we remove the remote
        // font to prioritize the local font. The remote one will never be
        // displayed or loaded as long as the local one exists.
        googleFonts = googleFonts.filter((font) => {
            const localFonts = googleLocalFonts.map((localFont) => localFont.split(":")[0]);
            return localFonts.indexOf(`'${font}'`) === -1;
        });
        const allFonts = [];

        const fontsToLoad = [];
        for (const font of googleFonts) {
            const fontURL = `https://fonts.googleapis.com/css?family=${encodeURIComponent(
                font
            ).replace(/%20/g, "+")}`;
            fontsToLoad.push(fontURL);
        }
        for (const font of googleLocalFonts) {
            const attachmentId = font.split(/\s*:\s*/)[1];
            const fontURL = `/web/content/${encodeURIComponent(attachmentId)}`;
            fontsToLoad.push(fontURL);
        }
        const proms = fontsToLoad.map(async (fontURL) => loadCSS(fontURL));

        const _fonts = [];
        const themeFontsNb =
            nbFonts - (googleLocalFonts.length + googleFonts.length + uploadedLocalFonts.length);
        const localFontsOffset = nbFonts - googleLocalFonts.length - uploadedLocalFonts.length;
        const uploadedFontsOffset = nbFonts - uploadedLocalFonts.length;

        for (let fontNb = 0; fontNb < nbFonts; fontNb++) {
            const realFontNb = fontNb + 1;
            const fontKey = getCSSVariableValue(`font-number-${realFontNb}`, style);
            allFonts.push(fontKey);
            let fontName = fontKey.slice(1, -1); // Unquote
            let fontFamily = fontName;
            const isSystemFonts = fontName === "SYSTEM_FONTS";
            if (isSystemFonts) {
                fontName = _t("System Fonts");
                fontFamily = "var(--o-system-fonts)";
            }

            let type = "cloud";
            let indexForType = fontNb - themeFontsNb;
            if (fontNb >= localFontsOffset) {
                if (fontNb < uploadedFontsOffset) {
                    type = "google";
                    indexForType = fontNb - localFontsOffset;
                } else {
                    type = "uploaded";
                    indexForType = fontNb - uploadedFontsOffset;
                }
            }
            _fonts.push({
                type,
                indexForType,
                fontFamily,
                string: fontName,
            });
        }
        await Promise.all(proms);
        return {
            allFonts,
            googleFonts,
            googleLocalFonts,
            uploadedLocalFonts,
            _fonts,
        };
    }
}
registry.category("website-plugins").add(FontPlugin.id, FontPlugin);
