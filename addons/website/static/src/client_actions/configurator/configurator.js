import { useEnv, useLayoutEffect, useRef, useSubEnv } from "@web/owl2/utils";
import { browser } from "@web/core/browser/browser";
const sessionStorage = browser.sessionStorage;
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { delay } from "@web/core/utils/concurrency";
import { getDataURLFromFile, redirect } from "@web/core/utils/urls";
import { getCSSVariableValue } from "@html_editor/utils/formatting";
import { _t } from "@web/core/l10n/translation";
import { svgToPNG, webpToPNG } from "@website/js/utils";
import { escapeRegExp } from "@web/core/utils/strings";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { clamp } from "@web/core/utils/numbers";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { mixCssColors } from "@web/core/utils/colors";
import { router } from "@web/core/browser/router";
import { Component, onMounted, onWillStart, proxy, useEffect, useListener } from "@odoo/owl";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { fuzzyLevenshteinLookup } from "@web/core/utils/search";
import { isBrowserSafari } from "@web/core/browser/feature_detection";

export const ROUTES = {
    descriptionScreen: 1,
    paletteSelectionScreen: 2,
    themeSelectionScreen: 3,
};

export const WEBSITE_TYPES = {
    1: { id: 1, label: _t("a website"), name: "business" },
    2: { id: 2, label: _t("an eCommerce"), name: "eCommerce" },
    3: { id: 3, label: _t("a blog"), name: "blog" },
    4: { id: 4, label: _t("an event website"), name: "event" },
    5: { id: 5, label: _t("an elearning platform"), name: "elearning" },
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

const MAX_NBR_DISPLAY_MAIN_THEMES = 6;
const DESKTOP_PREVIEW_WIDTH = 1440;

function getUserLanguageName() {
    const locale = user.lang || "en-US";
    const language = new Intl.Locale(locale).language;
    return new Intl.DisplayNames([locale], { type: "language" }).of(language) || "English";
}

function getCSSPalettes(style, paletteNames = PALETTE_NAMES, bgColorAttrs = CUSTOM_BG_COLOR_ATTRS) {
    const palettes = {};
    for (const paletteName of paletteNames) {
        const palette = {
            name: paletteName,
        };
        for (let j = 1; j <= 5; j++) {
            palette[`color${j}`] = getCSSVariableValue(
                `o-palette-${paletteName}-o-color-${j}`,
                style
            );
        }
        for (const attr of bgColorAttrs) {
            palette[attr] = getCSSVariableValue(`o-palette-${paletteName}-${attr}-bg`, style);
        }
        palettes[paletteName] = palette;
    }
    return palettes;
}

/**
 * Returns a list of maximum "resultNbrMax" themes for the wanted website.
 *
 * @param {Object} orm - The orm used for the server call.
 * @param {Object} state - The state that contains the wanted website.
 * @param {Number} resultNbrMax - The number of different wanted themes.
 * @param {Boolean} skipAi - Whether AI theme ranking should be skipped.
 * @returns {Promise<Array>} A list of theme suggestion objects. The length of
 * the list is at most 'resultNbrMax'.
 */
async function getRecommendedThemes(
    orm,
    state,
    resultNbrMax = MAX_NBR_DISPLAY_MAIN_THEMES,
    skipAi = false
) {
    return orm.call("website", "configurator_recommended_themes", [], {
        industry_id: state.selectedIndustry?.id || -1,
        industry_name: state.selectedIndustry?.label || "",
        result_nbr_max: resultNbrMax,
        website_type: WEBSITE_TYPES[state.selectedType]?.name || "business",
        positioning: state.selectedPositioning || state.formerSelectedPositioning || "",
        skip_ai: skipAi,
    });
}

async function getIndustryImages(orm, industryId, theme = "") {
    if (!industryId || industryId <= 0) {
        return {};
    }
    try {
        return await orm.call("website", "configurator_get_images", [], {
            industry_id: industryId,
            theme,
        });
    } catch {
        return {};
    }
}

function updateRecommendedThemes(state, themes) {
    state.themes = themes.slice(0, MAX_NBR_DISPLAY_MAIN_THEMES);
}

function getPreviewHeadersKey(state) {
    return JSON.stringify([
        state.selectedIndustry?.label || "general",
        WEBSITE_TYPES[state.selectedType]?.name || "business",
        state.selectedPositioning || state.formerSelectedPositioning || "general",
    ]);
}

/**
 * Generate and cache homepage preview headings text for the selected business context.
 *
 * @param {Object} state
 * @returns {Promise<string[]>}
 */
async function ensurePreviewHeaders(state) {
    const industry = state.selectedIndustry?.label || "general";
    const type = WEBSITE_TYPES[state.selectedType]?.name || "business";
    const positioning = state.selectedPositioning || state.formerSelectedPositioning || "general";
    const key = getPreviewHeadersKey(state);
    if (state.previewHeadersKey === key) {
        return state.previewHeaders || [];
    }

    state.previewHeaders = [];
    state.previewHeadersKey = key;
    state.previewHeadersLoading = true;
    try {
        const prompt = `For a ${industry} ${type} business with a ${positioning} positioning, return only a JSON array of 6 short homepage hero titles. Each item must be a plain string of not more than 4 words, with no numbering and no explanation.`;
        const response = await rpc("/html_editor/generate_text", {
            prompt,
            conversation_history: [],
        });
        const match = response?.match(/\[[\s\S]*\]/);
        const parsed = match && JSON.parse(match[0]);
        const generatedHeaders = (
            Array.isArray(parsed) && parsed.length === 6
                ? parsed.filter((item) => typeof item === "string").map((item) => item.trim())
                : []
        ).filter(Boolean);
        if (state.previewHeadersKey === key && generatedHeaders.length === 6) {
            state.previewHeaders = generatedHeaders;
        }
    } catch {
        // Keep the preview HTML unchanged if the AI did not answer correctly.
    } finally {
        if (state.previewHeadersKey === key) {
            state.previewHeadersLoading = false;
        }
    }

    return state.previewHeaders || [];
}

//------------------------------------------------------------------------------
// Components
//------------------------------------------------------------------------------

export class SkipButton extends Component {
    static template = "website.Configurator.SkipButton";
    static props = {
        skip: Function,
        className: { type: String, optional: true },
    };
}

export class DescriptionScreen extends Component {
    static template = "website.Configurator.DescriptionScreen";
    static components = { SkipButton, AutoComplete };
    static props = {
        navigate: Function,
        skip: Function,
    };
    setup() {
        this.industrySelection = useRef("industrySelection");
        this.purposeSelectionRef = useRef("purposeSelection");
        this.state = useStore();
        this.orm = useService("orm");
        useAutofocus();

        this.splitRegex = /[|\s,]+/;

        // Get all words from the industry names and synonyms
        this.dictionarySet = new Set();
        for (const industry of this.state.industries) {
            let industryWords = this._splitToSet(industry.label);
            if (industry.synonyms) {
                industryWords = industryWords.union(this._splitToSet(industry.synonyms));
            }
            this.dictionarySet = this.dictionarySet.union(industryWords);
        }

        onMounted(() => this.onMounted());

        // Autofocus the next field once the current one is confirmed.
        useLayoutEffect(
            (selectedType, selectedIndustry) => {
                if (selectedType && !selectedIndustry) {
                    this.industrySelection.el?.querySelector("input").focus();
                }
                if (selectedIndustry) {
                    this.purposeSelectionRef.el?.focus();
                }
            },
            () => [this.state.selectedType, this.state.selectedIndustry]
        );

        this.safariHackFocusedOutDropdown = null;
        this.fetchImagesRequestId = 0;
    }

    onMounted() {
        this.selectPositioning();
    }

    _setSelectedIndustry(label, id) {
        this.state.selectIndustry(label, id);
        this.setImages({});
        this.fetchIndustryImages(id);
        this.fetchPositionings(label);
    }

    setImages(images) {
        this.state.images = images || {};
    }

    async fetchIndustryImages(industryId) {
        const requestId = ++this.fetchImagesRequestId;
        if (!industryId || industryId <= 0) {
            return;
        }
        const images = await getIndustryImages(this.orm, industryId);
        if (
            requestId === this.fetchImagesRequestId &&
            this.state.selectedIndustry?.id === industryId
        ) {
            this.setImages(images);
        }
    }

    async fetchPositionings(industryLabel) {
        const userLanguage = getUserLanguageName();
        const fallback = [
            "premium",
            "affordable",
            "professional",
            "modern",
            "community-focused",
            "innovative",
        ];
        this.state.positionings = [];
        this.state.selectedPositioning = undefined;
        this.state.positioningsLoading = true;
        try {
            const prompt = `${_t(
                "Design a website for my %(industry)s business with a _______ positioning.",
                { industry: industryLabel }
            )} Return only a JSON array of 6 possibilities in ${userLanguage} to fill in the blank.`;
            const response = await rpc("/html_editor/generate_text", {
                prompt,
                conversation_history: [],
            });
            const match = response?.match(/\[[\s\S]*\]/);
            const parsed = match && JSON.parse(match[0]);
            this.state.positionings =
                Array.isArray(parsed) && parsed.every((item) => typeof item === "string")
                    ? parsed
                    : fallback;
        } catch {
            this.state.positionings = fallback;
        }
        this.state.positioningsLoading = false;
    }

    get previewImages() {
        return Object.values(this.state.images || {})
            .slice(0, 10)
            .map((url, slot) => ({ url, slot }));
    }

    _splitToSet(string) {
        return new Set(string.toLowerCase().split(this.splitRegex));
    }

    get sources() {
        return [
            {
                options: (request) => (request.length < 1 ? [] : this._autocompleteSearch(request)),
            },
        ];
    }
    /**
     * Called each time the autocomplete input's value changes. Only industries
     * having a label or a synonym containing all terms of the input value are
     * kept.
     * The order received from IAP is kept (expected to be on descending hit
     * count) unless there are 7 or less matches in which case the results are
     * sorted alphabetically.
     * The result size is limited to 30.
     *
     * @param {String} term input current value
     */
    _autocompleteSearch(term) {
        if (this.state.selectedIndustry) {
            this.state.selectIndustry();
        }
        this.setImages({});
        const termsSet = this._splitToSet(term);

        //-------words correction--------
        // Check and correct all the terms
        const correctedSet = new Set();
        for (const term of termsSet) {
            if (this.dictionarySet.has(term)) {
                correctedSet.add(term);
                continue;
            }
            const res = fuzzyLevenshteinLookup(term, this.dictionarySet);
            correctedSet.add(res[0] || term);
        }
        const terms = Array.from(correctedSet);
        const limit = 30;
        // `this.state.industries` is already sorted by hit count (from IAP).
        // That order should be kept after manipulating the recordset.
        let matches = this.state.industries.filter((val, index) =>
            // To match, every term should be contained in the label
            terms.every((term) => val.label.toLowerCase().includes(term))
        );

        matches = matches.sort((x, y) => x.hitCountOrder - y.hitCountOrder);
        if (matches.length > limit) {
            // Keep matches with the least number of words so that e.g.
            // "restaurant" remains available even if there are 30 specific
            // sub-types that have a higher hit count.
            matches = matches
                .sort((x, y) => x.wordCount - y.wordCount)
                .slice(0, limit)
                .sort((x, y) => x.hitCountOrder - y.hitCountOrder);
        } else {
            let synonymMatches = this.state.industries.filter((val, index) => {
                // To match, every term should be contained in the synonym
                for (const candidate of [...(val.synonyms || "").split(/[|,]/)]) {
                    // Check if industry label has already matched
                    if (
                        terms.every((term) => candidate.toLowerCase().includes(term)) &&
                        !matches.includes(val)
                    ) {
                        return true;
                    }
                }
                return false;
            });
            synonymMatches = synonymMatches.sort((x, y) => x.hitCountOrder - y.hitCountOrder);
            matches = matches.concat(synonymMatches);
            if (matches.length > limit) {
                matches = matches.slice(0, limit);
            }
        }
        if (!matches.some((industry) => industry.label.toLowerCase() === term.toLowerCase())) {
            matches.push({ label: term, id: -1 });
        }
        return matches.map((match) => ({
            label: match.label,
            labelTermOrder: this._getMatchTermOrder(match.label, terms),
            onSelect: () => this._setSelectedIndustry(match.label, match.id),
        }));
    }

    /**
     * Splits the string parameter 'label' into bits based on the location
     * of the 'terms' typed by the user.
     *
     * @param {string} label
     * @param {string[]} terms
     * @returns {object}
     * The return object 'matchTermOrder' contains two lists:
     * - 'labelBits' store all the segments of the split 'label'
     * - 'searchTermIndexes' keeps the indexes of the bits that matches with the 'terms'
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
                const splitBits = currentBit.split(new RegExp(`(${escapeRegExp(term)})`, "i"));
                matchTermOrder.labelBits.splice(bitIndex, 1, ...splitBits);
                bitIndex += splitBits.length;
            }
        }
        // Saves the indexes of the segments matching the terms
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

    selectPositioning(positioning) {
        if (!positioning && this.state.selectedPositioning) {
            this.state.formerSelectedPositioning = this.state.selectedPositioning;
        }
        this.state.selectedPositioning = positioning;
        this.checkDescriptionCompletion();
    }

    checkDescriptionCompletion() {
        const { selectedType, selectedPositioning, selectedIndustry } = this.state;
        if (selectedType && selectedPositioning && selectedIndustry) {
            if (selectedIndustry.id === -1) {
                this.orm.call("website", "configurator_missing_industry", [], {
                    unknown_industry: selectedIndustry.label,
                });
            }
            this.state.styleRecommendation = undefined;
            this.state.aiRecommendedPalette = undefined;
            this.state.themes = [];
            this.state.extraThemes = [];
            this.state.extraThemesLoaded = false;
            this.props.navigate(ROUTES.paletteSelectionScreen);
        }
    }

    onConfiguratorScreenFocusin(ev) {
        // On safari, hide the previously focused out dropdown if focusin is
        // outside of it
        if (isBrowserSafari() && this.safariHackFocusedOutDropdown) {
            if (ev.target.closest(".dropdown") !== this.safariHackFocusedOutDropdown) {
                window.Dropdown.getOrCreateInstance(this.safariHackFocusedOutDropdown).hide();
            }
            this.safariHackFocusedOutDropdown = null;
        }
    }
    /**
     * Hide the dropdown once the focus isn't contained within it anymore.
     *
     * @param {FocusEvent} ev
     */
    onDropdownFocusout(ev) {
        // On safari, we are missing relatedTarget because we can't focus on a
        // button, so we delay dropdown hiding to focusin of next element
        if (isBrowserSafari()) {
            this.safariHackFocusedOutDropdown = ev.currentTarget;
            return;
        }
        if (ev.relatedTarget?.closest(".dropdown") !== ev.currentTarget) {
            window.Dropdown.getOrCreateInstance(ev.currentTarget).hide();
        }
    }

    onAutocompleteInput({ inputValue }) {
        if (!inputValue) {
            this.state.selectIndustry(); // reset
            this.setImages({});
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
        this.state = useStore();
        this.logoInputRef = useRef("logoSelectionInput");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.hoverState = proxy({ palette: null });

        if (this.state.logo) {
            this.updatePalettes();
        }
        ensurePreviewHeaders(this.state);
        this.prefetchThemes();
        this.fetchStyleRecommendation();
    }

    prefetchThemes() {
        if (this.state.themes.length) {
            return;
        }
        getRecommendedThemes(this.env.services.orm, this.state)
            .then((themes) => {
                if (themes.length) {
                    updateRecommendedThemes(this.state, themes);
                }
            })
            .catch(() => {});
    }

    async fetchStyleRecommendation() {
        if (this.state.aiRecommendedPalette) {
            this.state.styleRecommendationLoading = false;
            return;
        }
        const { selectedIndustry, selectedType, selectedPositioning, formerSelectedPositioning } =
            this.state;
        const userLanguage = getUserLanguageName();
        const industry = selectedIndustry?.label || "general";
        const type = WEBSITE_TYPES[selectedType]?.name || "business";
        const positioning = selectedPositioning || formerSelectedPositioning || "";
        const palettes = Object.values(this.state.palettes);
        const catalog = {};
        palettes.forEach((palette, idx) => {
            catalog[idx] = {
                palette: palette.name,
                colors: {
                    color1: palette.color1,
                    color2: palette.color2,
                    color3: palette.color3,
                    color4: palette.color4,
                    color5: palette.color5,
                },
            };
        });
        const prompt = `For a ${industry} ${type} business with a ${positioning} positioning, recommend a color palette from this catalog:
${JSON.stringify(catalog, null, 2)}

Return ONLY a JSON object with:
- "id": the numeric ID from the catalog
- "reason": a short sentence in ${userLanguage} mentioning the business context, like: "For a family restaurant with a cozy positioning, I'd recommend warm colors to feel welcoming."`;
        this.state.styleRecommendationLoading = true;
        this.state.styleRecommendation = undefined;
        let palette;
        let reason = " ";
        try {
            const response = await rpc("/html_editor/generate_text", {
                prompt,
                conversation_history: [],
            });
            const match = response?.match(/\{[\s\S]*\}/);
            const parsed = match && JSON.parse(match[0]);
            palette = parsed && palettes[parsed.id];
            if (palette) {
                reason = parsed.reason || " ";
            }
        } catch {
            // Silently fail — the user can still pick manually
        }
        this.state.styleRecommendation = reason;
        this.state.styleRecommendationLoading = false;
        if (palette) {
            this.state.aiRecommendedPalette = palette.name;
            if (!this.state.selectedPalette) {
                this.selectPalette(palette.name);
            }
        }
    }

    get previewPalette() {
        return (
            this.hoverState.palette ||
            this.state.selectedPalette ||
            this.state.recommendedPalette ||
            Object.values(this.state.palettes || {})[0] || {
                color1: "#6EA8FE",
                color2: "#474973",
                color3: "#F0F2F5",
                color4: "#FFFFFF",
                color5: "#404264",
            }
        );
    }

    onPaletteCardHover(palette = null) {
        this.hoverState.palette = palette;
    }

    uploadLogo() {
        this.logoInputRef.el?.click();
    }

    /**
     * Removes the previously uploaded logo.
     *
     * @param {Event} ev
     */
    async removeLogo(ev) {
        ev.stopPropagation();
        // Permit to trigger onChange even with the same file.
        if (this.logoInputRef.el) {
            this.logoInputRef.el.value = "";
        }
        if (this.state.logoAttachmentId) {
            await this._removeAttachments([this.state.logoAttachmentId]);
        }
        this.state.changeLogo();
        // Remove recommended palette.
        this.state.setRecommendedPalette();
    }

    async changeLogo() {
        const logoSelectInput = this.logoInputRef.el;
        if (!logoSelectInput) {
            return;
        }
        if (logoSelectInput.files.length === 1) {
            const previousLogoAttachmentId = this.state.logoAttachmentId;
            const file = logoSelectInput.files[0];
            if (file.size > 2500000) {
                this.notification.add(
                    _t("The logo is too large. Please upload a logo smaller than 2.5 MB."),
                    {
                        title: file.name,
                        type: "warning",
                    }
                );
                return;
            }
            const data = await getDataURLFromFile(file);
            const logoData = data.startsWith("data:image/svg+xml") ? await svgToPNG(data) : data;
            const attachment = await rpc("/web_editor/attachment/add_data", {
                name: "logo",
                data: data.split(",")[1],
                is_image: true,
            });
            if (!attachment.error) {
                if (previousLogoAttachmentId) {
                    await this._removeAttachments([previousLogoAttachmentId]);
                }
                this.state.changeLogo(logoData, attachment.id);
                this.updatePalettes();
            } else {
                this.notification.add(attachment.error, {
                    title: file.name,
                });
            }
        }
    }

    async updatePalettes() {
        let img = this.state.logo;
        if (img.startsWith("data:image/svg+xml")) {
            img = await svgToPNG(img);
        }
        if (img.startsWith("data:image/webp")) {
            img = await webpToPNG(img);
        }
        img = img.split(",")[1];
        const [color1, color2] = await this.orm.call(
            "base.document.layout",
            "extract_image_primary_secondary_colors",
            [img],
            { mitigate: 255 }
        );
        this.state.setRecommendedPalette(color1, color2);
    }

    selectPalette(paletteName) {
        this.state.selectPalette(paletteName);
    }

    goToThemeSelection() {
        if (!this.state.selectedPalette) {
            return;
        }
        this.props.navigate(ROUTES.themeSelectionScreen);
    }

    /**
     * Removes the attachments from the DB.
     *
     * @private
     * @param {Array<number>} ids the attachment ids to remove
     */
    _removeAttachments(ids) {
        return rpc("/html_editor/attachment/remove", { ids: ids });
    }
}

export class ApplyConfiguratorScreen extends Component {
    static template = "";
    static props = ["*"];
    setup() {
        this.websiteService = useService("website");
        this.configuratorProgress = 0;
    }

    async applyConfigurator(themeName) {
        if (!this.state.selectedIndustry) {
            return this.props.navigate(ROUTES.descriptionScreen);
        }
        if (!this.state.selectedPalette) {
            return this.props.navigate(ROUTES.paletteSelectionScreen);
        }

        const attemptConfiguratorApply = async (data, retryCount = 0) => {
            try {
                return await this.orm.silent.call("website", "configurator_apply", [], data);
            } catch (error) {
                // Wait a bit before retrying or allowing manual retry.
                await delay(5000);
                if (retryCount < 3) {
                    return attemptConfiguratorApply(data, retryCount + 1);
                }
                document.querySelector(".o_website_loader_container").remove();
                throw error;
            }
        };

        if (themeName !== undefined) {
            const loadingSteps = [
                {
                    description: _t("Applying your colors and design..."),
                    flag: "colors",
                },
                {
                    description: _t("Searching your images..."),
                    flag: "images",
                },
                {
                    description: _t("Generating inspiring text..."),
                    flag: "text",
                },
                {
                    title: _t("Finalizing."),
                    description: _t("Activating your website."),
                    flag: "generic",
                },
            ];

            // The apply call is long-running, so real-time progress can't be
            // fetched. We simulate it instead.
            const stopProgressSimulation = this.startConfiguratorProgressSimulation();
            this.websiteService.showLoader({
                title: _t("Building your website."),
                loadingSteps,
                getProgress: () => this.configuratorProgress,
                bottomMessageTemplate: "website.website_loader.tour_tip",
            });
            let selectedPalette = this.state.selectedPalette.name;
            if (!selectedPalette) {
                selectedPalette = [
                    this.state.selectedPalette.color1,
                    this.state.selectedPalette.color2,
                    this.state.selectedPalette.color3,
                    this.state.selectedPalette.color4,
                    this.state.selectedPalette.color5,
                ];
            }
            const resp = await attemptConfiguratorApply(
                this.getConfigurationData(selectedPalette, themeName)
            );

            this.props.clearStorage();
            stopProgressSimulation();

            this.websiteService.redirectOutFromLoader({
                redirectAction: () => {
                    // Here, the website service `goToWebsite` method is not
                    // used because the web client needs to be reloaded after
                    // the configurator has updated the website.
                    window.sessionStorage.setItem("website.first_configurator_edit", "1");
                    const defaultLanguagePath = encodeURIComponent("/website/lang/default?r=/");
                    redirect(
                        `/odoo/action-website.website_preview?website_id=${encodeURIComponent(
                            resp.website_id
                        )}&path=${defaultLanguagePath}&enable_editor=1`
                    );
                },
            });
        }
    }

    getConfigurationData(selectedPalette, themeName) {
        return {
            industry_id: this.state.selectedIndustry.id,
            industry_name: this.state.selectedIndustry.label.toLowerCase(),
            selected_palette: selectedPalette,
            theme_name: themeName,
            website_purpose:
                this.state.selectedPositioning || this.state.formerSelectedPositioning || "general",
            website_type: WEBSITE_TYPES[this.state.selectedType].name,
            logo_attachment_id: this.state.logoAttachmentId,
        };
    }

    /**
     * Simulates the progress for website creation, divided into three phases:
     * 1. Initial Phase (0-30%): Fast progress to give the impression of quick
     *    processing.
     * 2. Processing Phase (30-90%): Slower progress while the website is built.
     * 3. Final Phase (90-100%): Slow progress to allow any pending operations
     *    to complete before reaching 100%.
     *
     * @returns {Function} A cleanup function that stops the simulation.
     */
    startConfiguratorProgressSimulation() {
        const INITIAL_PHASE_END = 30;
        const PROCESSING_PHASE_END = 90;

        const processingProgress = PROCESSING_PHASE_END - INITIAL_PHASE_END;

        let progress = 0;
        let phase = "initial";

        const intervalId = setInterval(() => {
            switch (phase) {
                case "initial":
                    progress += 2;
                    if (progress >= INITIAL_PHASE_END) {
                        phase = "processing";
                    }
                    break;

                case "processing": {
                    const currentProgress = progress - INITIAL_PHASE_END;
                    const ratio = clamp(currentProgress / processingProgress, 0, 1);
                    const speed = 1.5 + (0.2 - 1.5) * ratio;

                    progress = Math.min(progress + speed, PROCESSING_PHASE_END);
                    if (progress >= PROCESSING_PHASE_END) {
                        phase = "final";
                    }
                    break;
                }

                case "final":
                    progress = Math.min(progress + 0.05, 100);
                    break;
            }

            this.configuratorProgress = progress;
        }, 500);

        return () => clearInterval(intervalId);
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
        env.store["themesLoading"] = !env.store.themes?.length;
        env.store["extraThemesLoaded"] = false;
        env.store["extraThemes"] = [];
        this.state = proxy(env.store);
        useEffect(() => {
            const previewHeaders = this.state.previewHeaders?.join("\n") || "";
            if (!previewHeaders) {
                return;
            }
            this.updatePreviewIframeHeadings();
            this.scalePreviewIframes();
        });
        onWillStart(async () => {
            if (!this.state.previewHeaders?.length && !this.state.previewHeadersLoading) {
                await ensurePreviewHeaders(this.state);
            }
            if (!this.state.themes.length) {
                let themeName;
                this.uiService.block();
                try {
                    const themes = await getRecommendedThemes(this.orm, this.state);
                    if (!themes.length) {
                        themeName = "theme_default";
                    } else {
                        updateRecommendedThemes(this.state, themes);
                    }
                } finally {
                    this.state.themesLoading = false;
                    this.uiService.unblock();
                }
                if (themeName) {
                    await this.chooseTheme(themeName);
                    return;
                }
            }
        });
        onMounted(() => {
            this.scalePreviewIframes();
        });

        useListener(window, "resize", () => this.scalePreviewIframes());
    }

    /**
     * The button should be shown if we never tried to load the extra themes and
     * if they are enough main themes already displayed. If this last condition
     * is not fulfilled, there is no need to display the button as no more will
     * be displayed.
     */
    get showViewMoreThemesButton() {
        return (
            !this.state.extraThemesLoaded &&
            this.state.themes.length === MAX_NBR_DISPLAY_MAIN_THEMES
        );
    }

    scalePreviewIframes() {
        for (const iframe of document.querySelectorAll(
            ".o_theme_selection_screen .o_configurator_theme_preview_iframe"
        )) {
            this.scalePreviewIframe(iframe);
        }
    }

    getThemePreviewUrl(theme) {
        const previewUrl = new URL("/website/configurator/preview", browser.location.origin);
        const palette = this.state.selectedPalette || {};
        previewUrl.searchParams.set("preview_url", theme.preview_url);
        previewUrl.searchParams.set("theme_name", theme.name);
        previewUrl.searchParams.set("industry_id", this.state.selectedIndustry?.id || -1);
        for (const colorName of ["color1", "color2", "color3", "color4", "color5"]) {
            previewUrl.searchParams.set(colorName, palette[colorName] || "");
        }
        return previewUrl.toString();
    }

    /**
     * Pick a generated heading text for a preview iframe based on its display order.
     *
     * @param {HTMLIFrameElement} iframe
     * @returns {string | null}
     */
    getPreviewHeader(iframe) {
        const previewHeaders = this.state.previewHeaders || [];
        if (!previewHeaders.length) {
            return null;
        }
        const iframes = [
            ...document.querySelectorAll(
                ".o_theme_selection_screen .o_configurator_theme_preview_iframe"
            ),
        ];
        const index = iframes.indexOf(iframe);
        return previewHeaders[(index >= 0 ? index : 0) % previewHeaders.length];
    }

    getPreviewIframeDocument(iframe) {
        try {
            const previewDocument = iframe.contentDocument;
            return previewDocument?.readyState === "complete" ? previewDocument : null;
        } catch (error) {
            if (error.name === "SecurityError") {
                return null;
            }
            throw error;
        }
    }

    replacePreviewIframeHeading(iframe) {
        const previewHeader = this.getPreviewHeader(iframe);
        if (!previewHeader) {
            return;
        }
        const previewDocument = this.getPreviewIframeDocument(iframe);
        if (!previewDocument) {
            return;
        }
        const heading = previewDocument.querySelector("h1, .h1");
        if (heading) {
            heading.textContent = previewHeader;
        }
    }

    replacePreviewIframeLogo(iframe) {
        const logo = this.state.logo;
        if (!logo) {
            return;
        }
        const previewDocument = this.getPreviewIframeDocument(iframe);
        if (!previewDocument) {
            return;
        }
        const logoImage = previewDocument.querySelector("header img, #top img, .navbar-brand img");
        if (logoImage) {
            logoImage.src = logo;
        }
    }

    updatePreviewIframeHeadings() {
        for (const iframe of document.querySelectorAll(
            ".o_theme_selection_screen .o_configurator_theme_preview_iframe"
        )) {
            this.replacePreviewIframeHeading(iframe);
        }
    }

    getPreviewIframeContentSize(iframe) {
        const iframeWindow = iframe.contentWindow;
        const iframeDocument = this.getPreviewIframeDocument(iframe);
        const scrollingElement = iframeDocument?.scrollingElement;
        const documentElement = iframeDocument?.documentElement;
        const body = iframeDocument?.body;
        if (!iframeWindow || !scrollingElement || !documentElement) {
            return null;
        }
        return {
            width: Math.max(
                DESKTOP_PREVIEW_WIDTH,
                iframeWindow.innerWidth,
                scrollingElement.scrollWidth,
                documentElement.scrollWidth,
                body?.scrollWidth || 0
            ),
            height: Math.max(
                scrollingElement.scrollHeight,
                documentElement.scrollHeight,
                body?.scrollHeight || 0,
                documentElement.offsetHeight,
                body?.offsetHeight || 0
            ),
        };
    }

    scalePreviewIframe(iframe) {
        if (!iframe) {
            return;
        }

        const previewContainer = iframe.parentElement;
        const availableWidth = previewContainer.clientWidth;
        const availableHeight = previewContainer.clientHeight;

        if (!availableWidth || !availableHeight) {
            return;
        }

        iframe.style.setProperty("width", `${DESKTOP_PREVIEW_WIDTH}px`, "important");
        const contentSize = this.getPreviewIframeContentSize(iframe);
        const iframeWidth = contentSize?.width || DESKTOP_PREVIEW_WIDTH;
        const scale = Math.min(1, availableWidth / iframeWidth);
        const fallbackContentHeight = (availableHeight * 2) / scale;
        const iframeHeight = Math.ceil(contentSize?.height || fallbackContentHeight);
        // The iframe is scaled, so the scroll distance must use the scaled
        // height, not the raw document height.
        const scrollDistance = Math.max(0, iframeHeight * scale - availableHeight);

        iframe.style.setProperty("width", `${iframeWidth}px`, "important");
        iframe.style.setProperty("height", `${iframeHeight}px`, "important");
        iframe.style.setProperty(
            "--o-configurator-iframe-scroll-distance",
            `${Math.floor(scrollDistance)}px`
        );
        iframe.style.setProperty("--o-configurator-iframe-scale", scale);
        iframe.style.setProperty("transform-origin", "top left");
        iframe.style.setProperty("flex", "0 0 auto", "important");
    }

    onPreviewIframeLoad(ev) {
        const iframe = ev.currentTarget;
        this.replacePreviewIframeHeading(iframe);
        this.replacePreviewIframeLogo(iframe);
        iframe.parentElement.classList.add("o_preview_loaded");
        this.scalePreviewIframe(iframe);
    }

    async chooseTheme(themeName) {
        await this.applyConfigurator(themeName);
    }

    async getMoreThemes() {
        const themes = await getRecommendedThemes(
            this.orm,
            this.state,
            this.maxNbrDisplayExtraThemes,
            true
        );
        // Filter the extra themes to not propose a theme that is already
        // present in the main themes.
        const mainThemeNames = this.state.themes.map((theme) => theme.name);
        this.state.extraThemes = themes.filter(
            (extraTheme) => !mainThemeNames.includes(extraTheme.name)
        );
        this.state.extraThemesLoaded = true;
    }
}

//------------------------------------------------------------------------------
// Store
//------------------------------------------------------------------------------

export class Store {
    async start(getInitialState) {
        Object.assign(this, await getInitialState());
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
        this.selectedType = id;
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
        if (paletteName === "recommendedPalette") {
            this.selectedPalette = this.recommendedPalette;
        } else {
            this.selectedPalette = this.palettes[paletteName];
        }
    }

    setRecommendedPalette(color1, color2) {
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
}

export function useStore() {
    const env = useEnv();
    return proxy(env.store);
}

export class Configurator extends Component {
    static components = {
        DescriptionScreen,
        PaletteSelectionScreen,
        ThemeSelectionScreen,
    };
    static template = "website.Configurator.Configurator";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.website = useService("website");

        // Using the back button must update the router state.
        useListener(window, "popstate", (ev) => {
            // FIXME: this doesn't work unless this component is already mounted so navigating through
            // history from a different client action will not work.
            if (ev.state && "configuratorStep" in ev.state) {
                // Do not use navigate because URL is already updated.
                this.state.currentStep = ev.state.configuratorStep;
            }
        });

        const initialStep = router.current.step || ROUTES.descriptionScreen;
        const store = proxy(new Store());
        let isStoreStarted = false;
        useEffect(() => {
            const storageState = this.getStorageState(store);
            if (!isStoreStarted) {
                return;
            }
            this.updateStorage(storageState);
        });

        this.state = proxy({
            currentStep: initialStep,
        });

        useSubEnv({ store });

        onWillStart(async () => {
            this.websiteId = await rpc("/website/get_current_website_id");

            await store.start(() => this.getInitialState());
            this.updateStorage(this.getStorageState(store));
            isStoreStarted = true;
            if (!store.industries || store.configurator_done) {
                await this.skipConfigurator();
            }
        });

        // This is a hack to overwrite the history state, modified by the
        // router service after executing an action. Ideally, the router
        // service would let us push a state with a new pathname.
        onMounted(() => {
            setTimeout(() => {
                router.cancelPushes();
                this.updateBrowserUrl();
            });
        });
    }

    get pathname() {
        return `/website/configurator${
            this.state.currentStep ? `/${encodeURIComponent(this.state.currentStep)}` : ""
        }`;
    }

    get storageItemName() {
        return `websiteConfigurator${this.websiteId}`;
    }

    updateBrowserUrl() {
        history.pushState(
            { skipRouteChange: true, configuratorStep: this.state.currentStep },
            "",
            this.pathname
        );
    }

    get currentComponent() {
        if (this.state.currentStep === ROUTES.descriptionScreen) {
            return DescriptionScreen;
        } else if (this.state.currentStep === ROUTES.paletteSelectionScreen) {
            return PaletteSelectionScreen;
        } else if (this.state.currentStep === ROUTES.themeSelectionScreen) {
            return ThemeSelectionScreen;
        }
        return DescriptionScreen;
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
        this.state.currentStep = step;
        if (reload) {
            redirect(this.pathname);
        } else {
            this.updateBrowserUrl();
        }
    }

    clearStorage() {
        sessionStorage.removeItem(this.storageItemName);
    }

    async getInitialState() {
        // Load values from python and iap
        var results = await this.orm.call("website", "configurator_init");
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

        const style = window.getComputedStyle(document.documentElement);
        const palettes = getCSSPalettes(style, PALETTE_NAMES, CUSTOM_BG_COLOR_ATTRS);

        const localState = JSON.parse(sessionStorage.getItem(this.storageItemName));
        if (localState) {
            const storedState = { ...localState };
            delete storedState.selectedPurpose;
            delete storedState.formerSelectedPurpose;
            let themes = [];
            let images = {};
            if (storedState.selectedIndustry && storedState.selectedPalette) {
                themes = await getRecommendedThemes(this.orm, storedState);
            }
            if (storedState.selectedIndustry?.id > 0) {
                images = await getIndustryImages(
                    this.orm,
                    storedState.selectedIndustry.id,
                    themes[0]?.name || ""
                );
            }
            return Object.assign(r, {
                ...storedState,
                images,
                palettes,
                themes,
                previewHeaders: [],
                previewHeadersKey: undefined,
                previewHeadersLoading: false,
            });
        }

        // Palette color used by default as background color for menu and footer.
        // Needed to build the recommended palette.
        const defaultColors = {};
        CUSTOM_BG_COLOR_ATTRS.forEach((attr) => {
            const color = getCSSVariableValue(`o-default-${attr}-bg`, style);
            const match = color.match(/o-color-(?<idx>[1-5])/);
            const colorIdx = parseInt(match.groups["idx"]);
            defaultColors[attr] = `color${colorIdx}`;
        });

        return Object.assign(r, {
            selectedType: undefined,
            positionings: [],
            positioningsLoading: false,
            selectedPositioning: undefined,
            formerSelectedPositioning: undefined,
            selectedIndustry: undefined,
            images: {},
            selectedPalette: undefined,
            recommendedPalette: undefined,
            styleRecommendationLoading: false,
            styleRecommendation: undefined,
            aiRecommendedPalette: undefined,
            previewHeaders: [],
            previewHeadersKey: undefined,
            previewHeadersLoading: false,
            defaultColors: defaultColors,
            palettes: palettes,
            themes: [],
            logoAttachmentId: undefined,
        });
    }

    getStorageState(state) {
        return {
            defaultColors: state.defaultColors,
            logo: state.logo,
            logoAttachmentId: state.logoAttachmentId,
            selectedIndustry: state.selectedIndustry,
            selectedPalette: state.selectedPalette,
            positionings: state.positionings,
            selectedPositioning: state.selectedPositioning,
            formerSelectedPositioning: state.formerSelectedPositioning,
            selectedType: state.selectedType,
            recommendedPalette: state.recommendedPalette,
        };
    }

    updateStorage(state) {
        const newState = JSON.stringify(state);
        sessionStorage.setItem(this.storageItemName, newState);
    }

    async skipConfigurator() {
        this.website.showLoader({
            title: _t("Building your website."),
            bottomMessageTemplate: "website.website_loader.tour_tip",
        });
        const redirectUrl = await this.orm.call("website", "configurator_skip");
        this.clearStorage();
        // Here the website service goToWebsite method is not used because
        // the web client needs to be reloaded after the configurator has
        // updated the website.
        await this.action.doAction(redirectUrl);
    }
}

registry.category("actions").add("website_configurator", Configurator);
