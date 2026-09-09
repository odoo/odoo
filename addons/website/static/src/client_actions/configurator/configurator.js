/** @odoo-module native */
import { getCSSVariableValue } from "@html_editor/utils/formatting";
import {
    Component,
    onMounted,
    onWillStart,
    reactive,
    useEffect,
    useEnv,
    useExternalListener,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { AutoComplete } from "@web/components/autocomplete";
import { Dropdown, useDropdownState } from "@web/components/dropdown";
import { browser } from "@web/core/browser/browser";
import { getActiveHotkey } from "@web/core/browser/hotkeys";
import { router } from "@web/core/browser/router";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { rpc } from "@web/core/network";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { delay } from "@web/core/utils/concurrency";
import { mixCssColors } from "@web/core/utils/format/colors";
import { escapeRegExp } from "@web/core/utils/format/strings";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { fuzzyLevenshteinLookup } from "@web/core/utils/search";
import { getDataURLFromFile, redirect } from "@web/core/utils/urls";
import { standardActionServiceProps } from "@web/webclient/actions";
import { svgToPNG, webpToPNG } from "@website/js/utils";

const sessionStorage = browser.sessionStorage;

const log = makeLogger("website.configurator");

export const ROUTES = {
    descriptionScreen: 2,
    paletteSelectionScreen: 3,
    featuresSelectionScreen: 4,
    themeSelectionScreen: 5,
};

export const WEBSITE_TYPES = {
    1: { id: 1, label: _t("a website"), name: "business" },
    2: { id: 2, label: _t("an online store"), name: "online_store" },
    3: { id: 3, label: _t("a blog"), name: "blog" },
    4: { id: 4, label: _t("an event website"), name: "event" },
    5: { id: 5, label: _t("an elearning platform"), name: "elearning" },
};

export const WEBSITE_PURPOSES = {
    1: { id: 1, label: _t("get leads"), name: "get_leads" },
    2: { id: 2, label: _t("develop the brand"), name: "develop_brand" },
    3: { id: 3, label: _t("sell more"), name: "sell_more" },
    4: { id: 4, label: _t("inform customers"), name: "inform_customers" },
    5: { id: 5, label: _t("schedule appointments"), name: "schedule_appointments" },
};

export const PALETTE_NAMES = [
    "default-light-1",
    "default-light-2",
    "default-light-4",
    "default-light-3",
    "default-light-5",
    "default-24",
    "default-light-7",
    "default-light-6",
    "default-light-11",
    "default-light-14",
    "default-light-8",
    "default-6",
    "default-7",
    "default-8",
    "default-9",
    "default-23",
    "default-25",
    "default-12",
    "default-14",
    "default-22",
    "default-15",
    "default-16",
    "default-17",
    "default-light-10",
    "default-19",
    "default-20",
    "default-5",
    "default-4",
    "default-light-9",
    "default-2",
    "default-light-13",
    "default-27",
    "default-light-12",
    "default-1",
    "default-28",
    "default-21",
];

export const CUSTOM_BG_COLOR_ATTRS = ["menu", "footer"];

const MAX_NBR_DISPLAY_MAIN_THEMES = 3;

/**
 * @param {Object} orm
 * @param {Object} state
 * @param {Number} resultNbrMax
 * @returns {Promise<Array>}
 */
async function getRecommendedThemes(
    orm,
    state,
    resultNbrMax = MAX_NBR_DISPLAY_MAIN_THEMES,
) {
    return orm.call("website", "configurator_recommended_themes", [], {
        industry_id: state.selectedIndustry.id,
        palette: state.selectedPalette,
        result_nbr_max: resultNbrMax,
    });
}

export class SkipButton extends Component {
    static template = "website.Configurator.SkipButton";
    static props = {
        skip: Function,
    };
}

export class WelcomeScreen extends Component {
    static template = "website.Configurator.WelcomeScreen";
    static components = { SkipButton };
    static props = {
        skip: Function,
        navigate: Function,
    };
    setup() {
        useLifecycleLog(log);
        this.state = useStore();
    }

    goToDescription() {
        this.props.navigate(ROUTES.descriptionScreen);
    }
}

export class DescriptionScreen extends Component {
    static template = "website.Configurator.DescriptionScreen";
    static components = { SkipButton, AutoComplete, Dropdown };
    static props = {
        navigate: Function,
        skip: Function,
    };
    setup() {
        useLifecycleLog(log);
        this.industrySelection = useRef("industrySelection");
        this.purposeSelectionRef = useRef("purposeSelection");
        this.state = useStore();
        this.orm = useService("orm");
        useAutofocus();

        this.splitRegex = /[|\s,]+/;

        this.dictionarySet = new Set();
        for (const industry of this.state.industries) {
            let industryWords = this._splitToSet(industry.label);
            if (industry.synonyms) {
                industryWords = industryWords.union(
                    this._splitToSet(industry.synonyms),
                );
            }
            this.dictionarySet = this.dictionarySet.union(industryWords);
        }
        log.pipeline("DescriptionScreen dictionary built", () => ({
            words: this.dictionarySet.size,
        }));

        onMounted(() => this.onMounted());

        useEffect(
            (selectedType, selectedIndustry) => {
                if (selectedType && !selectedIndustry) {
                    this.industrySelection.el?.querySelector("input")?.focus();
                }
                if (selectedIndustry) {
                    this.purposeSelectionRef.el?.focus();
                }
            },
            () => [this.state.selectedType, this.state.selectedIndustry],
        );

        this.typeDropdown = useDropdownState();
        this.purposeDropdown = useDropdownState();
        useEffect(
            (selectedType) => {
                if (selectedType) {
                    this.typeDropdown.close();
                } else {
                    this.typeDropdown.open();
                }
            },
            () => [this.state.selectedType],
        );
        useEffect(
            (selectedPurpose) => {
                if (selectedPurpose) {
                    this.purposeDropdown.close();
                } else {
                    this.purposeDropdown.open();
                }
            },
            () => [this.state.selectedPurpose],
        );
    }

    onMounted() {
        this.selectWebsitePurpose();
    }
    /**
     * @private
     * @param {string} label
     * @param {number} id
     */
    _setSelectedIndustry(label, id) {
        this.state.selectIndustry(label, id);
        this.checkDescriptionCompletion();
    }

    _splitToSet(string) {
        return new Set(string.toLowerCase().split(this.splitRegex));
    }

    get sources() {
        return [
            {
                options: (request) =>
                    request.length < 1 ? [] : this._autocompleteSearch(request),
            },
        ];
    }
    /**
     * @param {String} term
     */
    _autocompleteSearch(term) {
        const endSearch = log.perf("DescriptionScreen autocompleteSearch", { term });
        this.state.selectedIndustry = undefined;
        const termsSet = this._splitToSet(term);

        const correctedSet = new Set();
        for (const term of termsSet) {
            if (this.dictionarySet.has(term)) {
                correctedSet.add(term);
                continue;
            }
            const res = fuzzyLevenshteinLookup(term, this.dictionarySet);
            correctedSet.add(res[0] || term);
        }
        let terms = Array.from(correctedSet);
        const limit = 30;
        let matches = this.state.industries.filter((val, index) =>
            terms.every((term) => val.label.toLowerCase().includes(term)),
        );

        matches = matches.sort((x, y) => x.hitCountOrder - y.hitCountOrder);
        if (matches.length > limit) {
            matches = matches
                .sort((x, y) => x.wordCount - y.wordCount)
                .slice(0, limit)
                .sort((x, y) => x.hitCountOrder - y.hitCountOrder);
        } else {
            let synonymMatches = this.state.industries.filter((val, index) => {
                for (const candidate of [
                    ...(val.synonyms || "").split(this.splitRegex),
                ]) {
                    if (
                        terms.every((term) => candidate.toLowerCase().includes(term)) &&
                        !matches.includes(val)
                    ) {
                        return true;
                    }
                }
                return false;
            });
            synonymMatches = synonymMatches.sort(
                (x, y) => x.hitCountOrder - y.hitCountOrder,
            );
            matches = matches.concat(synonymMatches);
            if (matches.length > limit) {
                matches = matches.slice(0, limit);
            }
        }
        if (matches.length === 0) {
            log.logic("autocompleteSearch: no industry match, free label", { term });
            matches = [{ label: term, id: -1 }];
            terms = [term];
        }
        endSearch(() => ({ matches: matches.length, terms }));
        return matches.map((match) => ({
            label: match.label,
            labelTermOrder: this._getMatchTermOrder(match.label, terms),
            onSelect: () => this._setSelectedIndustry(match.label, match.id),
        }));
    }

    /**
     * @param {string} label
     * @param {string[]} terms
     * @returns {object}
     */
    _getMatchTermOrder(label, terms) {
        const sortedTerms = terms.sort((a, b) => b.length - a.length);
        const matchTermOrder = {
            labelBits: [],
            searchTermIndexes: [],
        };
        if (!label) {
            return matchTermOrder;
        }

        matchTermOrder.labelBits.push(label);
        for (const term of sortedTerms) {
            let bitIndex = 0;
            while (bitIndex < matchTermOrder.labelBits.length) {
                const currentBit = matchTermOrder.labelBits[bitIndex];
                const splitBits = currentBit.split(
                    new RegExp(`(${escapeRegExp(term)})`),
                );
                matchTermOrder.labelBits.splice(bitIndex, 1, ...splitBits);
                bitIndex += splitBits.length;
            }
        }
        const labelBits = [];
        for (const i in matchTermOrder.labelBits) {
            labelBits.push({
                bit: matchTermOrder.labelBits[i],
                id: i,
            });
            if (sortedTerms.includes(matchTermOrder.labelBits[i].toLowerCase())) {
                matchTermOrder.searchTermIndexes.push(i);
            }
        }
        matchTermOrder.labelBits = labelBits;
        return matchTermOrder;
    }

    selectWebsiteType(id) {
        this.state.selectWebsiteType(id);
        this.checkDescriptionCompletion();
    }

    selectWebsitePurpose(id) {
        this.state.selectWebsitePurpose(id);
        this.checkDescriptionCompletion();
    }

    checkDescriptionCompletion() {
        const { selectedType, selectedPurpose, selectedIndustry } = this.state;
        if (selectedType && selectedPurpose && selectedIndustry) {
            log.logic("description complete: go to palette", () => ({
                selectedType,
                selectedPurpose,
                industryId: selectedIndustry.id,
            }));
            if (selectedIndustry.id === -1) {
                log.logic("report configurator_missing_industry", () => ({
                    label: selectedIndustry.label,
                }));
                this.orm.call("website", "configurator_missing_industry", [], {
                    unknown_industry: selectedIndustry.label,
                });
            }
            this.props.navigate(ROUTES.paletteSelectionScreen);
        }
    }
    onAutocompleteInput({ inputValue }) {
        if (!inputValue) {
            this.state.selectIndustry();
        }
    }
}

export class PaletteSelectionScreen extends Component {
    static components = { SkipButton };
    static template = "website.Configurator.PaletteSelectionScreen";
    static props = {
        navigate: Function,
        skip: Function,
    };
    setup() {
        useLifecycleLog(log);
        this.state = useStore();
        this.logoInputRef = useRef("logoSelectionInput");
        this.notification = useService("notification");
        this.orm = useService("orm");

        onMounted(() => {
            if (this.state.logo) {
                log.logic("PaletteSelectionScreen mounted with logo: update palettes");
                this.updatePalettes();
            }
        });
    }

    uploadLogo() {
        this.logoInputRef.el.click();
    }

    /**
     * @param {Event} ev
     */
    async removeLogo(ev) {
        ev.stopPropagation();
        this.logoInputRef.el.value = "";
        if (this.state.logoAttachmentId) {
            const endRemove = log.perf("removeLogo remove attachment");
            await this._removeAttachments([this.state.logoAttachmentId]);
            endRemove();
        }
        this.state.changeLogo();
        this.state.setRecommendedPalette();
    }

    async changeLogo() {
        const logoSelectInput = this.logoInputRef.el;
        if (logoSelectInput.files.length === 1) {
            const previousLogoAttachmentId = this.state.logoAttachmentId;
            const file = logoSelectInput.files[0];
            if (file.size > 2500000) {
                log.logic("changeLogo rejected: file too large", () => ({
                    name: file.name,
                    size: file.size,
                }));
                this.notification.add(
                    _t(
                        "The logo is too large. Please upload a logo smaller than 2.5 MB.",
                    ),
                    {
                        title: file.name,
                        type: "warning",
                    },
                );
                return;
            }
            const endUpload = log.perf("changeLogo read+upload", () => ({
                name: file.name,
                size: file.size,
            }));
            const data = await getDataURLFromFile(file);
            const attachment = await rpc("/web_editor/attachment/add_data", {
                name: "logo",
                data: data.split(",")[1],
                is_image: true,
            });
            endUpload(() => ({ attachmentId: attachment.id, error: attachment.error }));
            if (!attachment.error) {
                if (previousLogoAttachmentId) {
                    log.logic("changeLogo replace previous attachment", {
                        previousLogoAttachmentId,
                    });
                    await this._removeAttachments([previousLogoAttachmentId]);
                }
                this.state.changeLogo(data, attachment.id);
                this.updatePalettes();
            } else {
                log.logic("changeLogo upload error", () => ({
                    error: attachment.error,
                }));
                this.notification.add(attachment.error, {
                    title: file.name,
                });
            }
        }
    }

    async updatePalettes() {
        let img = this.state.logo;
        const endConvert = log.perf("updatePalettes convert logo");
        if (img.startsWith("data:image/svg+xml")) {
            img = await svgToPNG(img);
        }
        if (img.startsWith("data:image/webp")) {
            img = await webpToPNG(img);
        }
        endConvert();
        img = img.split(",")[1];
        const endColors = log.perf("extract_image_primary_secondary_colors");
        const [color1, color2] = await this.orm.call(
            "base.document.layout",
            "extract_image_primary_secondary_colors",
            [img],
            { mitigate: 255 },
        );
        endColors({ color1, color2 });
        this.state.setRecommendedPalette(color1, color2);
    }

    selectPalette(paletteName) {
        log.logic("PaletteSelectionScreen selectPalette", { paletteName });
        this.state.selectPalette(paletteName);
        this.props.navigate(ROUTES.featuresSelectionScreen);
    }

    /**
     * @private
     * @param {Array<number>} ids
     */
    async _removeAttachments(ids) {
        return rpc("/html_editor/attachment/remove", { ids: ids });
    }
}

export class ApplyConfiguratorScreen extends Component {
    static template = "";
    static props = ["*"];
    setup() {
        useLifecycleLog(log);
        this.websiteService = useService("website");
    }

    async applyConfigurator(themeName) {
        log.logic("applyConfigurator", { themeName });
        if (!this.state.selectedIndustry) {
            log.logic("applyConfigurator back: no industry");
            return this.props.navigate(ROUTES.descriptionScreen);
        }
        if (!this.state.selectedPalette) {
            log.logic("applyConfigurator back: no palette");
            return this.props.navigate(ROUTES.paletteSelectionScreen);
        }
        if (!this.state.selectedPurpose && !this.state.formerSelectedPurpose) {
            log.logic("applyConfigurator back: no purpose");
            return this.props.navigate(ROUTES.descriptionScreen);
        }
        if (!this.state.selectedType) {
            log.logic("applyConfigurator back: no website type");
            return this.props.navigate(ROUTES.descriptionScreen);
        }

        const attemptConfiguratorApply = async (data, retryCount = 0) => {
            try {
                return await this.orm.silent.call(
                    "website",
                    "configurator_apply",
                    [],
                    data,
                );
            } catch (error) {
                log.logic("configurator_apply failed", () => ({
                    retryCount,
                    message: error?.message,
                }));
                await delay(5000);
                if (retryCount < 3) {
                    log.pipeline("configurator_apply retry", { retryCount });
                    return attemptConfiguratorApply(data, retryCount + 1);
                }
                log.logic("configurator_apply giving up", { retryCount });
                document.querySelector(".o_website_loader_container").remove();
                throw error;
            }
        };

        if (themeName !== undefined) {
            const selectedFeatures = Object.values(this.state.features)
                .filter((feature) => feature.selected)
                .map((feature) => feature.id);
            log.pipeline("applyConfigurator show loader", () => ({
                features: selectedFeatures.length,
            }));
            this.websiteService.showLoader({
                showTips: true,
                selectedFeatures: selectedFeatures,
                showWaitingMessages: true,
            });
            let selectedPalette = this.state.selectedPalette.name;
            if (!selectedPalette) {
                log.logic("applyConfigurator custom (recommended) palette");
                selectedPalette = [
                    this.state.selectedPalette.color1,
                    this.state.selectedPalette.color2,
                    this.state.selectedPalette.color3,
                    this.state.selectedPalette.color4,
                    this.state.selectedPalette.color5,
                ];
            }
            const endApply = log.perf("configurator_apply", { themeName });
            const resp = await attemptConfiguratorApply(
                this.getConfigurationData(selectedFeatures, selectedPalette, themeName),
            );
            endApply(() => ({ websiteId: resp.website_id }));

            this.props.clearStorage();

            this.websiteService.prepareOutLoader();
            log.pipeline("applyConfigurator redirect to preview", () => ({
                websiteId: resp.website_id,
            }));
            redirect(
                `/odoo/action-website.website_preview?website_id=${encodeURIComponent(
                    resp.website_id,
                )}`,
            );
        }
    }

    getConfigurationData(selectedFeatures, selectedPalette, themeName) {
        return {
            selected_features: selectedFeatures,
            industry_id: this.state.selectedIndustry.id,
            industry_name: this.state.selectedIndustry.label.toLowerCase(),
            selected_palette: selectedPalette,
            theme_name: themeName,
            website_purpose:
                WEBSITE_PURPOSES[
                    this.state.selectedPurpose || this.state.formerSelectedPurpose
                ].name,
            website_type: WEBSITE_TYPES[this.state.selectedType].name,
            logo_attachment_id: this.state.logoAttachmentId,
        };
    }
}

export class FeaturesSelectionScreen extends Component {
    static components = { SkipButton };
    static template = "website.Configurator.FeatureSelection";
    static props = {
        navigate: Function,
        skip: Function,
    };
    setup() {
        super.setup();
        useLifecycleLog(log);
        this.state = useStore();
    }

    /**
     * @return {int}
     */
    static nextStep() {
        return ROUTES.themeSelectionScreen;
    }

    async buildWebsite() {
        const industryId =
            this.state.selectedIndustry && this.state.selectedIndustry.id;
        log.logic("buildWebsite", () => ({
            industryId,
            type: this.state.selectedType,
            purpose: this.state.selectedPurpose,
            palette: this.state.selectedPalette,
        }));
        if (!industryId) {
            return this.props.navigate(ROUTES.descriptionScreen);
        }

        this.props.navigate(FeaturesSelectionScreen.nextStep());
    }

    onKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (["enter", "space"].includes(hotkey)) {
            ev.target.click();
        }
    }
}

export class ThemeSelectionScreen extends ApplyConfiguratorScreen {
    static template = "website.Configurator.ThemeSelectionScreen";
    setup() {
        super.setup();

        this.uiService = useService("ui");
        this.orm = useService("orm");
        this.maxNbrDisplayExtraThemes = 100;
        const env = useEnv();
        env.store["extraThemesLoaded"] = false;
        env.store["extraThemes"] = [];
        this.state = useState(env.store);
        this.themeSVGPreviews = [
            useRef("ThemePreview1"),
            useRef("ThemePreview2"),
            useRef("ThemePreview3"),
        ];
        this.extraThemesButtonRef = useRef("extraThemesButton");
        this.extraThemeSVGPreviews = [];
        for (let i = 0; i < this.maxNbrDisplayExtraThemes; i++) {
            this.extraThemeSVGPreviews.push(useRef(`ExtraThemePreview${i}`));
        }
        onWillStart(async () => {
            const endThemes = log.perf("configurator_recommended_themes");
            const themes = await getRecommendedThemes(this.orm, this.state);
            endThemes(() => ({ themes: themes.length }));
            if (!themes.length) {
                log.logic("no recommended theme: apply theme_default");
                await this.applyConfigurator("theme_default");
            } else {
                this.state.updateRecommendedThemes(themes);
            }
        });

        onMounted(() => {
            this.blockUiDuringImageLoading(this.state.themes, this.themeSVGPreviews);
        });

        useEffect(
            () =>
                this.blockUiDuringImageLoading(
                    this.state.extraThemes,
                    this.extraThemeSVGPreviews,
                ),
            () => [this.state.extraThemes],
        );
    }

    get showViewMoreThemesButton() {
        return (
            !this.state.extraThemesLoaded &&
            this.state.themes.length === MAX_NBR_DISPLAY_MAIN_THEMES
        );
    }

    /**
     * @param {Array<Object>} themes
     * @param {Array} themeSVGPreviews
     */
    blockUiDuringImageLoading(themes, themeSVGPreviews) {
        if (!themes.length) {
            log.logic("blockUiDuringImageLoading skip: no themes");
            return;
        }
        const proms = [];
        const endImages = log.perf("blockUiDuringImageLoading", () => ({
            themes: themes.length,
        }));
        this.uiService.block({ delay: 700 });
        themes.forEach((theme, idx) => {
            const svgEl = new DOMParser().parseFromString(
                theme.svg,
                "image/svg+xml",
            ).documentElement;
            for (const imgEl of svgEl.querySelectorAll("image")) {
                proms.push(
                    new Promise((resolve, reject) => {
                        imgEl.addEventListener(
                            "load",
                            () => {
                                resolve(imgEl);
                            },
                            { once: true },
                        );
                        imgEl.addEventListener(
                            "error",
                            () => {
                                reject(imgEl);
                            },
                            { once: true },
                        );
                    }),
                );
            }
            themeSVGPreviews[idx].el.appendChild(svgEl);
        });
        log.pipeline("theme previews appended, waiting images", () => ({
            themes: themes.length,
            images: proms.length,
        }));
        Promise.allSettled(proms).then(() => {
            endImages(() => ({ images: proms.length }));
            this.uiService.unblock();
        });
    }

    async chooseTheme(themeName) {
        log.logic("chooseTheme", { themeName });
        await this.applyConfigurator(themeName);
    }

    async getMoreThemes() {
        this.uiService.block();
        const endMore = log.perf("getMoreThemes");
        const themes = await getRecommendedThemes(
            this.orm,
            this.state,
            this.maxNbrDisplayExtraThemes,
        );
        endMore(() => ({ themes: themes.length }));
        const mainThemeNames = this.state.themes.map((theme) => theme.name);
        this.state.extraThemes = themes.filter(
            (extraTheme) => !mainThemeNames.includes(extraTheme.name),
        );
        this.state.extraThemesLoaded = true;
        log.pipeline("getMoreThemes extra themes", () => ({
            fetched: themes.length,
            main: mainThemeNames.length,
        }));
        this.uiService.unblock();
    }

    getExtraThemeName(idx) {
        return this.state.extraThemes.length > idx && this.state.extraThemes[idx].name;
    }
}

export class Store {
    async start(getInitialState) {
        const endStart = log.perf("Store start");
        Object.assign(this, await getInitialState());
        endStart();
    }

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

    selectWebsiteType(id) {
        log.logic("Store selectWebsiteType", { id });
        Object.values(this.features)
            .filter((feature) => feature.module_state !== "installed")
            .forEach((feature) => {
                feature.selected = feature.website_config_preselection.includes(
                    WEBSITE_TYPES[id].name,
                );
            });
        this.selectedType = id;
    }

    selectWebsitePurpose(id) {
        log.logic("Store selectWebsitePurpose", { id });
        if (!id && this.selectedPurpose) {
            this.formerSelectedPurpose = this.selectedPurpose;
        }
        Object.values(this.features)
            .filter((feature) => feature.module_state !== "installed")
            .forEach((feature) => {
                feature.selected =
                    feature.selected ||
                    (id &&
                        feature.website_config_preselection.includes(
                            WEBSITE_PURPOSES[id].name,
                        ));
            });
        this.selectedPurpose = id;
    }

    selectIndustry(label, id) {
        if (!label || !id) {
            this.selectedIndustry = undefined;
        } else {
            this.selectedIndustry = { id, label };
        }
    }

    changeLogo(data, attachmentId) {
        this.logo = data;
        this.logoAttachmentId = attachmentId;
    }

    selectPalette(paletteName) {
        log.logic("Store selectPalette", { paletteName });
        if (paletteName === "recommendedPalette") {
            this.selectedPalette = this.recommendedPalette;
        } else {
            this.selectedPalette = this.palettes[paletteName];
        }
    }

    toggleFeature(featureId) {
        const feature = this.features[featureId];
        const isModuleInstalled = feature.module_state === "installed";
        log.logic("Store toggleFeature", { featureId, isModuleInstalled });
        feature.selected = !feature.selected || isModuleInstalled;
    }

    setRecommendedPalette(color1, color2) {
        log.logic("Store setRecommendedPalette", { color1, color2 });
        if (color1 && color2) {
            if (color1 === color2) {
                color2 = mixCssColors("#FFFFFF", color1, 0.2);
            }
            const recommendedPalette = {
                color1: color1,
                color2: color2,
                color3: mixCssColors("#FFFFFF", color2, 0.9),
                color4: "#FFFFFF",
                color5: mixCssColors(color1, "#000000", 0.125),
            };
            CUSTOM_BG_COLOR_ATTRS.forEach((attr) => {
                recommendedPalette[attr] = recommendedPalette[this.defaultColors[attr]];
            });
            this.recommendedPalette = recommendedPalette;
        } else {
            this.recommendedPalette = undefined;
        }
        this.selectedPalette = this.recommendedPalette;
    }

    updateRecommendedThemes(themes) {
        this.themes = themes.slice(0, MAX_NBR_DISPLAY_MAIN_THEMES);
    }
}

export function useStore() {
    const env = useEnv();
    return useState(env.store);
}

export class Configurator extends Component {
    static components = {
        WelcomeScreen,
        DescriptionScreen,
        PaletteSelectionScreen,
        FeaturesSelectionScreen,
        ThemeSelectionScreen,
    };
    static template = "website.Configurator.Configurator";
    static props = { ...standardActionServiceProps };

    setup() {
        useLifecycleLog(log);
        this.orm = useService("orm");
        this.action = useService("action");
        this.website = useService("website");

        useExternalListener(window, "popstate", (ev) => {
            if (ev.state && "configuratorStep" in ev.state) {
                log.logic("popstate restore step", () => ({
                    step: ev.state.configuratorStep,
                }));
                this.state.currentStep = ev.state.configuratorStep;
            }
        });

        const initialStep = router.current.step;
        const store = reactive(new Store(), () => this.updateStorage(store));

        this.state = useState({
            currentStep: initialStep,
        });

        useSubEnv({ store });

        onWillStart(async () => {
            const endWebsite = log.perf("get_current_website");
            this.websiteId = (await this.orm.call("website", "get_current_website"))[0];
            endWebsite(() => ({ websiteId: this.websiteId }));

            await store.start(() => this.getInitialState());
            this.updateStorage(store);
            if (!store.industries || store.configurator_done) {
                log.logic("willStart: nothing to configure, skip", () => ({
                    industries: Boolean(store.industries),
                    done: store.configurator_done,
                }));
                await this.skipConfigurator();
            }
        });

        onMounted(() => {
            setTimeout(() => {
                router.cancelPushes();
                this.updateBrowserUrl();
            });
        });
    }

    get pathname() {
        return `/website/configurator${
            this.state.currentStep
                ? `/${encodeURIComponent(this.state.currentStep)}`
                : ""
        }`;
    }

    get storageItemName() {
        return `websiteConfigurator${this.websiteId}`;
    }

    updateBrowserUrl() {
        history.pushState(
            { skipRouteChange: true, configuratorStep: this.state.currentStep },
            "",
            this.pathname,
        );
    }

    get currentComponent() {
        if (this.state.currentStep === ROUTES.descriptionScreen) {
            return DescriptionScreen;
        } else if (this.state.currentStep === ROUTES.paletteSelectionScreen) {
            return PaletteSelectionScreen;
        } else if (this.state.currentStep === ROUTES.featuresSelectionScreen) {
            return FeaturesSelectionScreen;
        } else if (this.state.currentStep === ROUTES.themeSelectionScreen) {
            return ThemeSelectionScreen;
        }
        return WelcomeScreen;
    }

    get componentProps() {
        const props = {
            skip: this.skipConfigurator.bind(this),
            navigate: this.navigate.bind(this),
        };
        if (this.state.currentStep === ROUTES.themeSelectionScreen) {
            props.clearStorage = this.clearStorage.bind(this);
        }
        return props;
    }

    navigate(step, reload = false) {
        log.lifecycle("navigate", () => ({
            from: this.state.currentStep,
            to: step,
            reload,
        }));
        this.state.currentStep = step;
        if (reload) {
            redirect(this.pathname);
        } else {
            this.updateBrowserUrl();
        }
    }

    clearStorage() {
        log.lifecycle("clearStorage", () => ({ key: this.storageItemName }));
        sessionStorage.removeItem(this.storageItemName);
    }

    async getInitialState() {
        const endInit = log.perf("configurator_init");
        const results = await this.orm.call("website", "configurator_init");
        endInit(() => ({
            industries: results.industries?.length,
            features: results.features?.length,
            done: results.configurator_done,
        }));
        const r = {
            industries: results.industries,
            logo: results.logo ? "data:image/png;base64," + results.logo : false,
            configurator_done: results.configurator_done,
        };
        r.industries = r.industries.map((industry, index) => ({
            ...industry,
            wordCount: industry.label.split(" ").length,
            hitCountOrder: index,
        }));

        const palettes = {};
        const style = window.getComputedStyle(document.documentElement);

        PALETTE_NAMES.forEach((paletteName) => {
            const palette = {
                name: paletteName,
            };
            for (let j = 1; j <= 5; j += 1) {
                palette[`color${j}`] = getCSSVariableValue(
                    `o-palette-${paletteName}-o-color-${j}`,
                    style,
                );
            }
            CUSTOM_BG_COLOR_ATTRS.forEach((attr) => {
                palette[attr] = getCSSVariableValue(
                    `o-palette-${paletteName}-${attr}-bg`,
                    style,
                );
            });
            palettes[paletteName] = palette;
        });
        log.pipeline("getInitialState palettes read", () => ({
            palettes: PALETTE_NAMES.length,
        }));

        const localState = JSON.parse(sessionStorage.getItem(this.storageItemName));
        if (localState) {
            log.logic("getInitialState restore from sessionStorage", () => ({
                industry: Boolean(localState.selectedIndustry),
                palette: Boolean(localState.selectedPalette),
            }));
            let themes = [];
            if (localState.selectedIndustry && localState.selectedPalette) {
                const endThemes = log.perf("getInitialState recommended themes");
                themes = await getRecommendedThemes(this.orm, localState);
                endThemes(() => ({ themes: themes.length }));
            }
            return Object.assign(r, { ...localState, palettes, themes });
        }

        const features = {};
        results.features.forEach((feature) => {
            features[feature.id] = Object.assign({}, feature, {
                selected: feature.module_state === "installed",
            });
            const wtp = features[feature.id]["website_config_preselection"];
            features[feature.id]["website_config_preselection"] = wtp
                ? wtp.split(",")
                : [];
        });

        log.pipeline("getInitialState fresh state", () => ({
            features: Object.keys(features).length,
        }));
        const defaultColors = {};
        CUSTOM_BG_COLOR_ATTRS.forEach((attr) => {
            const color = getCSSVariableValue(`o-default-${attr}-bg`, style);
            const match = color.match(/o-color-(?<idx>[1-5])/);
            const colorIdx = parseInt(match.groups["idx"]);
            defaultColors[attr] = `color${colorIdx}`;
        });

        return Object.assign(r, {
            selectedType: undefined,
            selectedPurpose: undefined,
            formerSelectedPurpose: undefined,
            selectedIndustry: undefined,
            selectedPalette: undefined,
            recommendedPalette: undefined,
            defaultColors: defaultColors,
            palettes: palettes,
            features: features,
            themes: [],
            logoAttachmentId: undefined,
        });
    }

    updateStorage(state) {
        const newState = JSON.stringify({
            defaultColors: state.defaultColors,
            features: state.features,
            logo: state.logo,
            logoAttachmentId: state.logoAttachmentId,
            selectedIndustry: state.selectedIndustry,
            selectedPalette: state.selectedPalette,
            selectedPurpose: state.selectedPurpose,
            formerSelectedPurpose: state.formerSelectedPurpose,
            selectedType: state.selectedType,
            recommendedPalette: state.recommendedPalette,
        });
        sessionStorage.setItem(this.storageItemName, newState);
    }

    async skipConfigurator() {
        log.logic("skipConfigurator");
        this.website.showLoader({ showTips: true });
        const endSkip = log.perf("configurator_skip");
        const redirectUrl = await this.orm.call("website", "configurator_skip");
        endSkip();
        this.clearStorage();
        await this.action.doAction(redirectUrl);
    }
}

registry.category("actions").add("website_configurator", Configurator);
