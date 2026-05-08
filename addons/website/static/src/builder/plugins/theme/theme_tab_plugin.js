import { reactive } from "@web/owl2/utils";
import { Plugin } from "@html_editor/plugin";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { withSequence } from "@html_editor/utils/resource";
import { ThemeAdvancedOption } from "./theme_advanced_option";
import { ThemeShadowOption } from "./theme_shadow_option";
import { ThemeButtonOption } from "./theme_button_option";
import { ThemeColorsOption } from "./theme_colors_option";
import { ThemeHeadingsOption } from "./theme_headings_option";
import { setBuilderCSSVariables } from "@html_builder/utils/utils_css";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    convertCSSColorToRgba,
    convertRgbaToCSSColor,
    convertHslToRgb,
    convertRgbToHsl,
} from "@web/core/utils/colors";
import { BuilderAction } from "@html_builder/core/builder_action";
import { CustomizeWebsiteVariableAction } from "../customize_website_plugin";
import { EditHeadBodyDialog } from "@website/components/edit_head_body_dialog/edit_head_body_dialog";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { ImageSize } from "@html_builder/plugins/image/image_size";

/**
 * @typedef { Object } ThemeTabShared
 * @property { ThemeTabPlugin['buildGray'] } buildGray
 * @property { ThemeTabPlugin['buildPolarGray'] } buildPolarGray
 * @property { ThemeTabPlugin['refreshGrays'] } refreshGrays
 * @property { ThemeTabPlugin['getGrays'] } getGrays
 * @property { ThemeTabPlugin['getGrayParams'] } getGrayParams
 * @property { ThemeTabPlugin['setGrays'] } setGrays
 * @property { ThemeTabPlugin['setGrayParams'] } setGrayParams
 * @property { ThemeTabPlugin['isGrayscaleCustomMode'] } isGrayscaleCustomMode
 * @property { ThemeTabPlugin['setGrayscaleCustomMode'] } setGrayscaleCustomMode
 */

/**
 * @typedef {import("@html_builder/core/builder_options_plugin").BuilderOptionContainer[]} theme_options
 */

export const GRAY_PARAMS = {
    EXTRA_SATURATION: "gray-extra-saturation",
    HUE: "gray-hue",
};

export const OPTION_POSITIONS = {
    COLORS: 10,
    SETTINGS: 20,
    PARAGRAPH: 30,
    HEADINGS: 40,
    BUTTON: 50,
    LINK: 60,
    INPUT: 70,
    SHADOW: 80,
    ADVANCED: 90,
};

export class ThemeTabPlugin extends Plugin {
    static id = "themeTab";
    static shared = [
        "getGrayParams", "getGrays", "setGrays", "setGrayParams",
        "buildGray", "buildPolarGray", "refreshGrays",
        "isGrayscaleCustomMode", "setGrayscaleCustomMode",
    ];
    grayParams = {};
    grays = reactive({});
    grayscaleCustomMode = reactive({ value: false });

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            CustomizeGrayAction,
            ToggleGrayscaleCustomAction,
            ChangeColorPaletteAction,
            EditCustomCodeAction,
            ConfigureApiKeyAction,
        },
        theme_options: [
            withSequence(
                OPTION_POSITIONS.SETTINGS,
                this.getThemeOptionBlock(
                    "website-settings",
                    "",
                    [
                        ThemeColorsOption,
                        class ThemeWebsiteSettingsOption extends BaseOptionComponent {
                            static template = "website.ThemeWebsiteSettingsOption";
                            static components = { ImageSize };
                        },
                    ],
                    this.document.querySelector("#wrapwrap"),
                    true
                )
            ),
            withSequence(
                OPTION_POSITIONS.PARAGRAPH,
                this.getThemeOptionBlock(
                    "theme-paragraph",
                    _t("Paragraph"),
                    class ThemeParagraphOption extends BaseOptionComponent {
                        static template = "website.ThemeParagraphOption";
                    }
                )
            ),
            withSequence(
                OPTION_POSITIONS.HEADINGS,
                this.getThemeOptionBlock("theme-headings", _t("Headings"), ThemeHeadingsOption)
            ),
            withSequence(
                OPTION_POSITIONS.BUTTON,
                this.getThemeOptionBlock("theme-button", _t("Button"), ThemeButtonOption)
            ),
            withSequence(
                OPTION_POSITIONS.LINK,
                this.getThemeOptionBlock(
                    "theme-link",
                    _t("Link"),
                    class ThemeLinkOption extends BaseOptionComponent {
                        static template = "website.ThemeLinkOption";
                    }
                )
            ),
            withSequence(
                OPTION_POSITIONS.INPUT,
                this.getThemeOptionBlock(
                    "theme-input",
                    _t("Input Fields"),
                    class ThemeInputOption extends BaseOptionComponent {
                        static template = "website.ThemeInputOption";
                    }
                )
            ),
            withSequence(
                OPTION_POSITIONS.SHADOW,
                this.getThemeOptionBlock("theme-shadow", _t("Shadow"), ThemeShadowOption)
            ),
            withSequence(
                OPTION_POSITIONS.ADVANCED,
                this.getThemeOptionBlock("theme-advanced", _t("Advanced"), ThemeAdvancedOption)
            ),
        ],
    };

    setup() {
        // If the gray palette has been generated by Odoo standard option,
        // the hue of all gray is the same and the saturation has been
        // increased/decreased by the same amount for all grays in
        // comparaison with BS grays. However the system supports any
        // gray palette.

        const hues = [];
        const saturationDiffs = [];
        let oneHasNoSaturation = false;
        const style = this.window.getComputedStyle(this.document.body);
        const baseStyle = getComputedStyle(document.body);
        for (let id = 100; id <= 900; id += 100) {
            const gray = getCSSVariableValue(`${id}`, style);
            this.grays[id] = gray;
            const grayRGB = convertCSSColorToRgba(gray);
            const grayHSL = convertRgbToHsl(grayRGB.red, grayRGB.green, grayRGB.blue);

            const baseGray = getCSSVariableValue(`base-${id}`, baseStyle);
            const baseGrayRGB = convertCSSColorToRgba(baseGray);
            const baseGrayHSL = convertRgbToHsl(
                baseGrayRGB.red,
                baseGrayRGB.green,
                baseGrayRGB.blue
            );

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
        this.grayParams[GRAY_PARAMS.HUE] = !hues.length
            ? 0
            : Math.round(
                  (Math.atan2(
                      hues
                          .map((hue) => Math.sin((hue * Math.PI) / 180))
                          .reduce((memo, value) => memo + value, 0) / hues.length,
                      hues
                          .map((hue) => Math.cos((hue * Math.PI) / 180))
                          .reduce((memo, value) => memo + value, 0) / hues.length
                  ) *
                      180) /
                      Math.PI +
                      360
              ) % 360;

        // Average of found saturation diffs, or all grays have no
        // saturation, or all grays are fully saturated.
        this.grayParams[GRAY_PARAMS.EXTRA_SATURATION] = saturationDiffs.length
            ? saturationDiffs.reduce((memo, value) => memo + value, 0) / saturationDiffs.length
            : oneHasNoSaturation
            ? -100
            : 100;

        // Initialize grayscale custom mode from the compiled CSS var.
        this.grayscaleCustomMode.value =
            getCSSVariableValue("grayscale-custom", style) === "true";
    }
    getGrayParams() {
        return this.grayParams;
    }
    getGrays() {
        return this.grays;
    }
    setGrayParams(key, value) {
        this.grayParams[key] = value;
    }
    setGrays(key, value) {
        this.grays[key] = value;
    }
    refreshGrays() {
        // Re-read 100-900 CSS vars from the compiled bundle and sync the
        // reactive grays object so the preview strip updates immediately.
        const style = this.window.getComputedStyle(this.document.body);
        for (let i = 1; i < 10; i++) {
            const key = (100 * i).toString();
            this.grays[key] = getCSSVariableValue(key, style);
        }
    }
    isGrayscaleCustomMode() {
        return this.grayscaleCustomMode.value;
    }
    setGrayscaleCustomMode(value) {
        this.grayscaleCustomMode.value = value;
    }
    buildGray(id) {
        // Getting base grays defined in color_palette.scss
        const gray = getCSSVariableValue(`base-${id}`, getComputedStyle(document.documentElement));
        const grayRGB = convertCSSColorToRgba(gray);
        const hsl = convertRgbToHsl(grayRGB.red, grayRGB.green, grayRGB.blue);
        const adjustedGrayRGB = convertHslToRgb(
            this.grayParams[GRAY_PARAMS.HUE],
            Math.min(
                Math.max(hsl.saturation + this.grayParams[GRAY_PARAMS.EXTRA_SATURATION], 0),
                100
            ),
            hsl.lightness
        );
        return convertRgbaToCSSColor(
            adjustedGrayRGB.red,
            adjustedGrayRGB.green,
            adjustedGrayRGB.blue
        );
    }
    buildPolarGray(id) {
        // Compute the gray step for the given id (100-900) by linearly
        // interpolating between the palette's two polar colors (o-color-4 and
        // o-color-5), ordered by lightness so id=100 is always the lightest shade.
        // Use hb-cp- vars which are guaranteed to be set by setBuilderCSSVariables.
        const style = getComputedStyle(document.documentElement);
        const c4 = getCSSVariableValue("hb-cp-o-color-4", style);
        const c5 = getCSSVariableValue("hb-cp-o-color-5", style);
        const c4RGB = convertCSSColorToRgba(c4);
        const c5RGB = convertCSSColorToRgba(c5);
        const c4L = convertRgbToHsl(c4RGB.red, c4RGB.green, c4RGB.blue).lightness;
        const c5L = convertRgbToHsl(c5RGB.red, c5RGB.green, c5RGB.blue).lightness;
        const [lightRGB, darkRGB] = c4L >= c5L ? [c4RGB, c5RGB] : [c5RGB, c4RGB];
        const t = parseInt(id) / 1000; // 0.1 (100) … 0.9 (900)
        return convertRgbaToCSSColor(
            Math.round(lightRGB.red   * (1 - t) + darkRGB.red   * t),
            Math.round(lightRGB.green * (1 - t) + darkRGB.green * t),
            Math.round(lightRGB.blue  * (1 - t) + darkRGB.blue  * t)
        );
    }

    getThemeOptionBlock(id, name, options, el = null, hasOverlayOptions = false) {
        let divEl = null;
        // TODO Have a specific kind of options container that takes the
        // specific parameters like name, no element, no selector...
        if (!el) {
            divEl = this.document.createElement("div");
            divEl.dataset.name = name;
            this.document.body.appendChild(divEl); // Currently editingElement needs to be isConnected
            el = divEl;
        }

        const optionsArray = Array.isArray(options) ? options : [options];
        optionsArray.forEach((option) => {
            option.selector = "*";
        });

        return {
            id: id,
            element: el,
            hasOverlayOptions,
            headerMiddleButton: false,
            isClonable: false,
            isRemovable: false,
            options: optionsArray,
            optionsContainerTopButtons: [],
        };
    }
}

export class CustomizeGrayAction extends BuilderAction {
    static id = "customizeGray";
    static dependencies = ["customizeWebsite", "themeTab"];
    setup() {
        this.preview = false;
        this.dependencies.customizeWebsite.withCustomHistory(this);
    }
    getValue({ params: { mainParam: grayParamName } }) {
        return this.dependencies.themeTab.getGrayParams()[grayParamName];
    }
    async apply({ params: { mainParam: grayParamName }, value }) {
        // Gray parameters are used *on the JS side* to compute the grays that
        // will be saved in the database. We indeed need those grays to be
        // computed here for faster previews so this allows to not duplicate
        // most of the logic. Also, this gives flexibility to maybe allow full
        // customization of grays in custo and themes. Also, this allows to ease
        // migration if the computation here was to change: the user grays would
        // still be unchanged as saved in the database.

        this.dependencies.themeTab.setGrayParams(grayParamName, parseInt(value));
        for (let i = 1; i < 10; i++) {
            const key = (100 * i).toString();
            this.dependencies.themeTab.setGrays(key, this.dependencies.themeTab.buildGray(key));
        }

        // Save all computed (JS side) grays in database
        await this.dependencies.customizeWebsite.customizeWebsiteColors(
            this.dependencies.themeTab.getGrays(),
            {
                colorType: "gray",
            }
        );
        setBuilderCSSVariables(getHtmlStyle(this.document));
    }
}
export class ToggleGrayscaleCustomAction extends BuilderAction {
    static id = "toggleGrayscaleCustom";
    static dependencies = ["customizeWebsite", "themeTab"];
    setup() {
        this.preview = false;
        this.dependencies.customizeWebsite.withCustomHistory(this);
    }
    isApplied() {
        // Read from the compiled CSS var so the builder framework's re-evaluation
        // cycle (triggered after every bundle reload) picks up the correct state.
        // --grayscale-custom is set to true/false by $o-grayscale-is-custom in SCSS.
        return this.dependencies.customizeWebsite.getWebsiteVariableValue("grayscale-custom") === "true";
    }
    async apply() {
        // Switching TO custom mode: seed the DB with polar-derived grays so the
        // hue/sat sliders have a meaningful starting point.
        const grays = {};
        for (let i = 1; i < 10; i++) {
            const key = (100 * i).toString();
            const color = this.dependencies.themeTab.buildPolarGray(key);
            grays[key] = color;
            this.dependencies.themeTab.setGrays(key, color);
        }
        await this.dependencies.customizeWebsite.customizeWebsiteColors(grays, {
            colorType: "gray",
        });
        this.dependencies.themeTab.setGrayscaleCustomMode(true);
        setBuilderCSSVariables(getHtmlStyle(this.document));
    }
    async clean() {
        // Switching TO polar mode: clear all saved grays so SCSS derives them
        // from the palette's polar colors again.
        const grays = {};
        for (let i = 1; i < 10; i++) {
            const key = (100 * i).toString();
            grays[key] = null;
        }
        await this.dependencies.customizeWebsite.customizeWebsiteColors(grays, {
            colorType: "gray",
        });
        // Sync the reactive grays object so the preview strip re-renders.
        this.dependencies.themeTab.refreshGrays();
        setBuilderCSSVariables(getHtmlStyle(this.document));
    }
}
export class ChangeColorPaletteAction extends CustomizeWebsiteVariableAction {
    static id = "changeColorPalette";
    // themeTab is needed to refresh the gray preview after palette reset.
    static dependencies = ["customizeWebsite", "themeTab"];
    setup() {
        this.preview = false;
        this.dependencies.customizeWebsite.withCustomHistory(this);
    }
    async load() {
        const style = this.window.getComputedStyle(this.document.body);
        const hasCustomizedColors = getCSSVariableValue("has-customized-colors", style);
        if (hasCustomizedColors && hasCustomizedColors !== "false") {
            return new Promise((resolve) => {
                this.services.dialog.add(ConfirmationDialog, {
                    body: _t(
                        "Changing the color palette will reset all your color customizations, are you sure you want to proceed?"
                    ),
                    confirmLabel: _t("Apply New Palette"),
                    confirm: () => resolve(true),
                    cancel: () => resolve(false),
                });
            });
        }
        return true;
    }
    async apply(context) {
        if (!context.loadResult) {
            return;
        }
        await super.apply(context);
        // Palette change resets user_gray_color_palette → polar mode is restored.
        // Refresh preview so the strip immediately reflects the new palette colors.
        this.dependencies.themeTab.setGrayscaleCustomMode(false);
        this.dependencies.themeTab.refreshGrays();
        setBuilderCSSVariables(getHtmlStyle(this.document));
    }
}

export class EditCustomCodeAction extends BuilderAction {
    static id = "editCustomCode";
    setup() {
        this.canTimeout = false;
    }
    apply() {
        this.services.dialog.add(EditHeadBodyDialog);
    }
}

export class ConfigureApiKeyAction extends BuilderAction {
    static id = "configureApiKey";
    static dependencies = ["googleMapsOption"];
    setup() {
        this.canTimeout = false;
    }
    apply() {
        this.dependencies.googleMapsOption.configureGMapsAPI("", true);
    }
}

registry.category("website-plugins").add(ThemeTabPlugin.id, ThemeTabPlugin);
