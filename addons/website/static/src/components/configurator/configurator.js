/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { _lt, _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { renderToString } from "@web/core/utils/render";
import { ColorpickerWidget } from "web.Colorpicker";
import rpc from "web.rpc";
import session from "web.session";
import utils from "web.utils";
import { svgToPNG } from "website.utils";
import weUtils from "web_editor.utils";

const { App, Component, onMounted, reactive, useEnv, useRef, useState, whenReady } = owl;

const ROUTES = {
    descriptionScreen: 2,
    paletteSelectionScreen: 3,
    featuresSelectionScreen: 4,
    themeSelectionScreen: 5,
};

const WEBSITE_TYPES = {
    1: { id: 1, label: _lt("a business website"), name: "business" },
    2: { id: 2, label: _lt("an online store"), name: "online_store" },
    3: { id: 3, label: _lt("a blog"), name: "blog" },
    4: { id: 4, label: _lt("an event website"), name: "event" },
    5: { id: 5, label: _lt("an elearning platform"), name: "elearning" },
};

const WEBSITE_PURPOSES = {
    1: { id: 1, label: _lt("get leads"), name: "get_leads" },
    2: { id: 2, label: _lt("develop the brand"), name: "develop_brand" },
    3: { id: 3, label: _lt("sell more"), name: "sell_more" },
    4: { id: 4, label: _lt("inform customers"), name: "inform_customers" },
    5: { id: 5, label: _lt("schedule appointments"), name: "schedule_appointments" },
};

const PALETTE_NAMES = [
    "default-1",
    "default-2",
    "default-3",
    "default-4",
    "default-5",
    "default-6",
    "default-7",
    "default-8",
    "default-9",
    "default-10",
    "default-11",
    "default-12",
    "default-13",
    "default-14",
    "default-15",
    "default-16",
    "default-17",
    "default-18",
    "default-19",
    "default-20",
];

// Attributes for which background color should be retrieved
// from CSS and added in each palette.
const CUSTOM_BG_COLOR_ATTRS = ["menu", "footer"];

const SESSION_STORAGE_ITEM_NAME = "websiteConfigurator" + session.website_id;

//-----------------------------------------------------------------------------
// Components
//-----------------------------------------------------------------------------

class SkipButton extends Component {
    async skip() {
        await skipConfigurator();
    }
}

SkipButton.template = "website.Configurator.SkipButton";

class WelcomeScreen extends Component {
    setup() {
        this.store = useStore();
        this.router = useRouter();
    }

    goToDescription() {
        this.router.navigate(ROUTES.descriptionScreen);
    }
}

Object.assign(WelcomeScreen, {
    components: { SkipButton },
    template: "website.Configurator.WelcomeScreen",
});

class DescriptionScreen extends Component {
    setup() {
        this.industrySelection = useRef("industrySelection");
        this.store = useStore();
        this.router = useRouter();
        this.labelToId = {};
        this.autocompleteHasResults = true;

        onMounted(() => this.onMounted());
    }

    onMounted() {
        this.selectWebsitePurpose();
        $(this.industrySelection.el).autocomplete({
            appendTo: ".o_configurator_industry_wrapper",
            delay: 400,
            minLength: 1,
            source: this.autocompleteSearch.bind(this),
            select: this.selectIndustry.bind(this),
            open: this.customizeNoResultMenuStyle.bind(this),
            focus: this.disableKeyboardNav.bind(this),
            classes: {
                "ui-autocomplete":
                    "custom-ui-autocomplete shadow-lg border-0 o_configurator_show_fast",
            },
        });
        if (this.store.selectedIndustry) {
            this.industrySelection.el.value = this.store.selectedIndustry.label;
            this.industrySelection.el.parentNode.dataset.value = this.store.selectedIndustry.label;
            this.labelToId[this.store.selectedIndustry.label] = this.store.selectedIndustry.id;
        }
    }

    /**
     * Clear the input and its parent label and set the selected industry to undefined.
     */
    clearIndustrySelection() {
        this.industrySelection.el.value = "";
        this.industrySelection.el.parentNode.dataset.value = "";
        this.store.selectIndustry();
    }

    /**
     * Set the input's parent label value to automatically adapt input size
     * and update the selected industry.
     *
     * @param {String} label an industry label
     */
    setSelectedIndustry(label) {
        this.industrySelection.el.parentNode.dataset.value = label;
        const id = this.labelToId[label];
        this.store.selectIndustry(label, id);
        this.checkDescriptionCompletion();
    }

    /**
     * Called each time the suggestion menu is opened or updated. If there are no
     * results to display the style of the "No result found" message is customized.
     */
    customizeNoResultMenuStyle() {
        if (!this.autocompleteHasResults) {
            const noResultLinkEl = this.industrySelection.el.parentElement.getElementsByTagName(
                "a"
            )[0];
            noResultLinkEl.classList.add("o_no_result");
        }
    }

    /**
     * Disables keyboard navigation when there are no results to avoid selecting the
     * "No result found" message by pressing the down arrow key.
     *
     * @param {Event} ev
     */
    disableKeyboardNav(ev) {
        if (!this.autocompleteHasResults) {
            ev.preventDefault();
        }
    }

    /**
     * Called each time the autocomplete input's value changes. Only industries containing
     * the input value are kept. Industries starting with the input value are put in first
     * position then the order is the alphabetical one. The result size is limited to 15.
     *
     * @param {Object} request object with a single 'term' property which is the input current value
     * @param {Function} response callback which takes the data to suggest as argument
     */
    autocompleteSearch(request, response) {
        const lcTerm = request.term.toLowerCase();
        const limit = 15;
        const matches = this.store.industries.filter((val) => val.label.startsWith(lcTerm));
        let results = matches.slice(0, limit);
        this.labelToId = {};
        let labels = results.map((val) => val.label);
        if (labels.length < limit) {
            const relaxedMatches = this.store.industries
                .filter((val) => val.label.includes(lcTerm) && !labels.includes(val.label))
                .slice(0, limit - labels.length);
            results = results.concat(relaxedMatches);
        }
        this.autocompleteHasResults = !!results.length;
        if (this.autocompleteHasResults) {
            labels = results.map((val) => val.label);
            results.forEach((r) => {
                this.labelToId[r.label] = r.id;
            });
        } else {
            labels = [_t("No result found, broaden your search.")];
        }
        response(labels);
    }

    /**
     * Called when a menu option is selected. Update the selected industry or
     * clear the input if the option is the "No result found" message.
     *
     * @param {Event} ev
     * @param {Object} ui an object with label and value properties for
     *      the selected option.
     */
    selectIndustry(ev, ui) {
        if (this.autocompleteHasResults) {
            this.setSelectedIndustry(ui.item.label);
        } else {
            this.clearIndustrySelection();
            ev.preventDefault();
        }
    }

    /**
     * Called on industrySelection input blur. Updates the selected industry or
     * clears the input if its current value is not a valid industry.
     *
     * @param {Event} ev
     */
    blurIndustrySelection(ev) {
        if (this.labelToId[ev.target.value] !== undefined) {
            this.setSelectedIndustry(ev.target.value);
        } else {
            this.clearIndustrySelection();
        }
    }

    selectWebsiteType(id) {
        this.store.selectWebsiteType(id);
        setTimeout(() => {
            this.industrySelection.el.focus();
        });
        this.checkDescriptionCompletion();
    }

    selectWebsitePurpose(id) {
        this.store.selectWebsitePurpose(id);
        this.checkDescriptionCompletion();
    }

    checkDescriptionCompletion() {
        const { selectedType, selectedPurpose, selectedIndustry } = this.store;
        if (selectedType && selectedPurpose && selectedIndustry) {
            this.router.navigate(ROUTES.paletteSelectionScreen);
        }
    }
}

Object.assign(DescriptionScreen, {
    components: { SkipButton },
    template: "website.Configurator.DescriptionScreen",
});

class PaletteSelectionScreen extends Component {
    setup() {
        this.store = useStore();
        this.router = useRouter();
        this.logoInputRef = useRef("logoSelectionInput");
        this.notification = useService("notification");

        onMounted(() => {
            if (this.store.logo) {
                this.updatePalettes();
            }
        });
    }

    uploadLogo() {
        this.logoInputRef.el.click();
    }

    async changeLogo() {
        const logoSelectInput = this.logoInputRef.el;
        if (logoSelectInput.files.length === 1) {
            const file = logoSelectInput.files[0];
            const data = await utils.getDataURLFromFile(file);
            const attachment = await this.rpc({
                route: "/web_editor/attachment/add_data",
                params: {
                    name: "logo",
                    data: data.split(",")[1],
                    is_image: true,
                },
            });
            if (!attachment.error) {
                this.store.changeLogo(data, attachment.id);
                this.updatePalettes();
            } else {
                this.notification.notify({
                    title: file.name,
                    message: attachment.error,
                });
            }
        }
    }

    async updatePalettes() {
        let img = this.store.logo;
        if (img.startsWith("data:image/svg+xml")) {
            img = await svgToPNG(img);
        }
        img = img.split(",")[1];
        const [color1, color2] = await rpc.query({
            model: "base.document.layout",
            method: "extract_image_primary_secondary_colors",
            args: [img],
            kwargs: { mitigate: 255 },
        });
        this.store.setRecommendedPalette(color1, color2);
    }

    selectPalette(paletteName) {
        this.store.selectPalette(paletteName);
        this.router.navigate(ROUTES.featuresSelectionScreen);
    }
}

Object.assign(PaletteSelectionScreen, {
    components: { SkipButton },
    template: "website.Configurator.PaletteSelectionScreen",
});

class FeaturesSelectionScreen extends Component {
    setup() {
        this.store = useStore();
        this.router = useRouter();
    }

    async buildWebsite() {
        const industryId = this.store.selectedIndustry && this.store.selectedIndustry.id;
        if (!industryId) {
            return this.router.navigate(ROUTES.descriptionScreen);
        }
        const params = {
            industry_id: industryId,
            palette: this.store.selectedPalette,
        };
        const themes = await rpc.query({
            model: "website",
            method: "configurator_recommended_themes",
            kwargs: params,
        });

        if (themes.length) {
            this.store.updateRecommendedThemes(themes);
            this.router.navigate(ROUTES.themeSelectionScreen);
        } else {
            await applyConfigurator(this, "theme_default");
        }
    }
}

Object.assign(FeaturesSelectionScreen, {
    components: { SkipButton },
    template: "website.Configurator.FeatureSelection",
});

class ThemeSelectionScreen extends Component {
    setup() {
        this.store = useStore();
        this.router = useRouter();
        this.themeSVGPreviews = [
            useRef("ThemePreview1"),
            useRef("ThemePreview2"),
            useRef("ThemePreview3"),
        ];

        onMounted(() => {
            this.store.themes.forEach((theme, index) => {
                this.themeSVGPreviews[index].el.appendChild(stringToElement(theme.svg));
            });
        });
    }

    async chooseTheme(themeName) {
        await applyConfigurator(this, themeName);
    }
}

ThemeSelectionScreen.template = "website.Configurator.ThemeSelectionScreen";

class Configurator extends Component {
    setup() {
        this.router = useRouter();
    }
}

Object.assign(Configurator, {
    components: {
        WelcomeScreen,
        DescriptionScreen,
        PaletteSelectionScreen,
        FeaturesSelectionScreen,
        ThemeSelectionScreen,
    },
    template: "website.Configurator.Configurator",
});

//-----------------------------------------------------------------------------
// Router
//-----------------------------------------------------------------------------

class Router {
    constructor() {
        this.location = window.location.pathname;
    }

    navigate(id) {
        this.location = `/website/configurator${id ? "/" + id : ""}`;
        history.pushState({}, "", window.location.origin + this.location);
    }
}

const useRouter = () => {
    const env = useEnv();
    return useState(env.router);
};

//-----------------------------------------------------------------------------
// Store
//-----------------------------------------------------------------------------

class Store {
    constructor() {
        this.defaultColors = {};
        this.features = {};
        this.logoAttachmentId = undefined;
        this.palettes = {};
        this.recommendedPalette = undefined;
        this.selectedType = undefined;
        this.selectedPurpose = undefined;
        this.selectedIndustry = undefined;
        this.selectedPalette = undefined;
        this.themes = [];
    }

    async start() {
        // Load values from python and iap
        const results = await rpc.query({
            model: "website",
            method: "configurator_init",
        });
        this.industries = results.industries;
        this.logo = results.logo ? "data:image/png;base64," + results.logo : false;

        // Load palettes from the current CSS
        const style = window.getComputedStyle(document.documentElement);

        PALETTE_NAMES.forEach((paletteName) => {
            const palette = {
                name: paletteName,
            };
            for (let j = 1; j <= 5; j += 1) {
                palette[`color${j}`] = weUtils.getCSSVariableValue(
                    `o-palette-${paletteName}-o-color-${j}`,
                    style
                );
            }
            CUSTOM_BG_COLOR_ATTRS.forEach((attr) => {
                palette[attr] = weUtils.getCSSVariableValue(
                    `o-palette-${paletteName}-${attr}-bg`,
                    style
                );
            });
            this.palettes[paletteName] = palette;
        });

        const localState = JSON.parse(window.sessionStorage.getItem(SESSION_STORAGE_ITEM_NAME));
        if (localState) {
            Object.assign(this, localState);
            if (localState.selectedIndustry && localState.selectedPalette) {
                const params = {
                    industry_id: localState.selectedIndustry.id,
                    palette: localState.selectedPalette,
                };
                this.themes = await rpc.query({
                    model: "website",
                    method: "configurator_recommended_themes",
                    kwargs: params,
                });
            }
        } else {
            for (const feature of results.features) {
                this.features[feature.id] = {
                    ...feature,
                    selected: feature.module_state === "installed",
                };
                const wtp = this.features[feature.id].website_config_preselection;
                this.features[feature.id].website_config_preselection = wtp ? wtp.split(",") : [];
            }

            // Palette color used by default as background color for menu and footer.
            // Needed to build the recommended palette.
            CUSTOM_BG_COLOR_ATTRS.forEach((attr) => {
                const color = weUtils.getCSSVariableValue(`o-default-${attr}-bg`, style);
                const match = color.match(/o-color-(?<idx>[1-5])/);
                const colorIdx = parseInt(match.groups["idx"]);
                this.defaultColors[attr] = `color${colorIdx}`;
            });
        }
    }

    //-------------------------------------------------------------------------
    // Getters
    //-------------------------------------------------------------------------

    getWebsiteTypes() {
        return Object.values(WEBSITE_TYPES);
    }

    getSelectedType(id) {
        return id && WEBSITE_TYPES[id];
    }

    getWebsitePurpose() {
        return Object.values(WEBSITE_PURPOSES);
    }

    getSelectedPurpose(id) {
        return id && WEBSITE_PURPOSES[id];
    }

    getFeatures() {
        return Object.values(this.features);
    }

    getPalettes() {
        return Object.values(this.palettes);
    }

    getThemeName(idx) {
        return this.themes.length > idx && this.themes[idx].name;
    }

    /**
     * @returns {string | false}
     */
    getSelectedPaletteName() {
        const palette = this.selectedPalette;
        return palette ? palette.name || "recommendedPalette" : false;
    }

    //-------------------------------------------------------------------------
    // Actions
    //-------------------------------------------------------------------------

    selectWebsiteType(id) {
        for (const feature of this.getFeatures()) {
            if (feature.module_state !== "installed") {
                feature.selected = feature.website_config_preselection.includes(
                    WEBSITE_TYPES[id].name
                );
            }
        }
        this.selectedType = id;
        this.updateStorage();
    }

    selectWebsitePurpose(id) {
        for (const feature of this.getFeatures()) {
            if (feature.module_state !== "installed") {
                // need to check id, since we set to undefined in mount() to avoid the auto next screen on back button
                feature.selected |=
                    id && feature.website_config_preselection.includes(WEBSITE_PURPOSES[id].name);
            }
        }
        this.selectedPurpose = id;
        this.updateStorage();
    }

    selectIndustry(label, id) {
        if (!label || !id) {
            this.selectedIndustry = undefined;
        } else {
            this.selectedIndustry = { id, label };
        }
        this.updateStorage();
    }

    changeLogo(data, attachmentId) {
        this.logo = data;
        this.logoAttachmentId = attachmentId;
        this.updateStorage();
    }

    selectPalette(paletteName) {
        if (paletteName === "recommendedPalette") {
            this.selectedPalette = this.recommendedPalette;
        } else {
            this.selectedPalette = this.palettes[paletteName];
        }
        this.updateStorage();
    }

    toggleFeature(featureId) {
        const feature = this.features[featureId];
        const isModuleInstalled = feature.module_state === "installed";
        feature.selected = !feature.selected || isModuleInstalled;
        this.updateStorage();
    }

    setRecommendedPalette(color1, color2) {
        if (color1 && color2) {
            if (color1 === color2) {
                color2 = ColorpickerWidget.mixCssColors("#FFFFFF", color1, 0.2);
            }
            const recommendedPalette = {
                color1: color1,
                color2: color2,
                color3: ColorpickerWidget.mixCssColors("#FFFFFF", color2, 0.9),
                color4: "#FFFFFF",
                color5: ColorpickerWidget.mixCssColors(color1, "#000000", 0.75),
            };
            CUSTOM_BG_COLOR_ATTRS.forEach((attr) => {
                recommendedPalette[attr] = recommendedPalette[this.defaultColors[attr]];
            });
            this.recommendedPalette = recommendedPalette;
        } else {
            this.recommendedPalette = undefined;
        }
        this.updateStorage();
    }

    updateRecommendedThemes(themes) {
        this.themes = themes.slice(0, 3);
        this.updateStorage();
    }

    /**
     * @private
     */
    updateStorage() {
        const newState = JSON.stringify({
            defaultColors: this.defaultColors,
            features: this.features,
            logo: this.logo,
            logoAttachmentId: this.logoAttachmentId,
            selectedIndustry: this.selectedIndustry,
            selectedPalette: this.selectedPalette,
            selectedPurpose: this.selectedPurpose,
            selectedType: this.selectedType,
            recommendedPalette: this.recommendedPalette,
        });
        window.sessionStorage.setItem(SESSION_STORAGE_ITEM_NAME, newState);
    }
}

const useStore = () => {
    const env = useEnv();
    return useState(env.store);
};

//-----------------------------------------------------------------------------
// Helpers
//-----------------------------------------------------------------------------

const applyConfigurator = async ({ store, router }, themeName) => {
    if (!store.selectedIndustry) {
        return router.navigate(ROUTES.descriptionScreen);
    }
    if (!store.selectedPalette) {
        return router.navigate(ROUTES.paletteSelectionScreen);
    }
    if (themeName !== undefined) {
        const loader = renderToString("website.ThemePreview.Loader", {
            showTips: true,
        });
        document.body.appendChild(stringToElement(loader));
        const selectedFeatures = store
            .getFeatures()
            .filter((feature) => feature.selected)
            .map((feature) => feature.id);
        let selectedPalette = store.selectedPalette.name;
        if (!selectedPalette) {
            selectedPalette = [
                store.selectedPalette.color1,
                store.selectedPalette.color2,
                store.selectedPalette.color3,
                store.selectedPalette.color4,
                store.selectedPalette.color5,
            ];
        }
        const data = {
            selected_features: selectedFeatures,
            industry_id: store.selectedIndustry.id,
            selected_palette: selectedPalette,
            theme_name: themeName,
            website_purpose: WEBSITE_PURPOSES[store.selectedPurpose].name,
            website_type: WEBSITE_TYPES[store.selectedType].name,
            logo_attachment_id: store.logoAttachmentId,
        };
        const res = await rpc.query({
            model: "website",
            method: "configurator_apply",
            kwargs: { ...data },
        });
        exitConfigurator(res.url);
    }
};

const exitConfigurator = (url) => {
    window.sessionStorage.removeItem(SESSION_STORAGE_ITEM_NAME);
    window.location = url;
};

/**
 * This is the exact same implementation existing in '@web/core/assets.js',
 * with the only exception that we need the 'ThemePreview.Loader' template
 * which is still legacy. The only modified part of this function allows
 * non-owl templates to be parsed as well.
 *
 * This must be replaced by the actual 'loadBundleTemplates' in web/core/assets
 * when the template is converted.
 */
const loadBundleTemplates = async () => {
    const bundleURL = new URL(`/web/webclient/qweb/${Date.now()}`, window.location.origin);
    bundleURL.searchParams.set("bundle", "website.website_configurator_assets_qweb");
    const templates = await (await browser.fetch(bundleURL.href)).text();
    const doc = new DOMParser().parseFromString(templates, "text/xml");
    for (const template of [...doc.querySelector("templates").children]) {
        if (template.hasAttribute("owl")) {
            template.removeAttribute("owl");
        }
    }
    return doc;
}

const makeEnvironment = async () => {
    const env = {
        store: reactive(new Store()),
        router: reactive(new Router()),
        services: Component.env.services,
    };
    await Promise.all([session.is_bound, env.store.start()]);
    return env;
};

const skipConfigurator = async () => {
    await rpc.query({
        model: "website",
        method: "configurator_skip",
    });
    exitConfigurator("/web#action=website.theme_install_kanban_action")
};

const stringToElement = (string) => {
    const el = document.createElement("div");
    el.innerHTML = string;
    return el.children[0];
};

//-----------------------------------------------------------------------------
// Setup
//-----------------------------------------------------------------------------

const setup = async () => {
    const env = await makeEnvironment();
    if (!env.store.industries) {
        await skipConfigurator();
    } else {
        const templates = await loadBundleTemplates();
        const app = new App(Configurator, {
            env,
            dev: env.debug,
            templates,
            translatableAttributes: ["label", "title", "placeholder", "alt", "data-tooltip"],
            translateFn: _t,
        });
        renderToString.app = app;
        await app.mount(document.body);
    }
};

whenReady(setup);
