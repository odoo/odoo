import { Plugin } from "@html_editor/plugin";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { Cache } from "@web/core/utils/cache";
import { loadCSS } from "@web/core/assets";
import { BuilderFontSizeSelector } from "./font_size_selector";
import { withSequence } from "@html_editor/utils/resource";

export class BuilderFontPlugin extends Plugin {
    static id = "builderFont";
    static shared = ["getFontsCache", "getFontsData"];
    static dependencies = ["toolbar"];
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
        font_items: [
            ...[
                { name: _t("Header 1 Display 2"), tagName: "h1", extraClass: "display-2" },
                { name: _t("Header 1 Display 3"), tagName: "h1", extraClass: "display-3" },
                { name: _t("Header 1 Display 4"), tagName: "h1", extraClass: "display-4" },
            ].map((item) => withSequence(15, item)),
            withSequence(43, { name: _t("Light"), tagName: "p", extraClass: "lead" }),
            withSequence(46, { name: _t("Small"), tagName: "p", extraClass: "small" }),
        ],
    };
    setup() {
        this.fontsCache = new Cache(this._fetchFonts.bind(this), JSON.stringify);
        const buttonGroups = this.dependencies.toolbar.getToolbarInfo().buttonGroups;
        for (const buttonGroup of buttonGroups) {
            if (buttonGroup.id !== "font") {
                continue;
            }
            for (const button of buttonGroup.buttons) {
                if (button.id === "font-size") {
                    button.Component = BuilderFontSizeSelector;
                }
            }
        }
    }
    destroy() {
        super.destroy();
        this.fontsCache.invalidate();
    }
    getFontsCache() {
        return this.fontsCache;
    }
    async getFontsData() {
        return this.fontsCache.read({});
    }
    async _fetchFonts() {
        const style = getHtmlStyle(this.document);
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
            const fontFamilyValue = `'${fontName}'`;
            let styleFontFamily = fontName;
            const isSystemFonts = fontName === "SYSTEM_FONTS";
            if (isSystemFonts) {
                fontName = _t("System Fonts");
                styleFontFamily = "var(--o-system-fonts)";
            }

            let type = isSystemFonts ? "system" : "cloud";
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
                fontFamilyValue,
                styleFontFamily,
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
registry.category("builder-plugins").add(BuilderFontPlugin.id, BuilderFontPlugin);
