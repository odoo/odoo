import {
    reactive,
    useEnv,
    useExternalListener,
    useLayoutEffect,
    useRef,
    useState,
    useSubEnv,
} from "@web/owl2/utils";
import { browser } from "@web/core/browser/browser";
const sessionStorage = browser.sessionStorage;
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { delay } from "@web/core/utils/concurrency";
import { getDataURLFromFile, redirect } from "@web/core/utils/urls";
import { getCSSVariableValue } from "@html_editor/utils/formatting";
import { loadImage } from "@html_editor/utils/image_processing";
import { getBgImageURLFromEl } from "@html_builder/utils/utils_css";
import { _t } from "@web/core/l10n/translation";
import { svgToPNG, webpToPNG } from "@website/js/utils";
import { escapeRegExp } from "@web/core/utils/strings";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { mixCssColors, normalizeCSSColor } from "@web/core/utils/colors";
import { router } from "@web/core/browser/router";
import { Component, markup, onMounted, onWillStart, onWillUnmount } from "@odoo/owl";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { fuzzyLevenshteinLookup } from "@web/core/utils/search";
import { isBrowserSafari } from "@web/core/browser/feature_detection";

export const ROUTES = {
    descriptionScreen: 1,
    themeSelectionScreen: 2,
    setupStyleScreen: 3,
};

export const WEBSITE_TYPES = {
    1: { id: 1, label: _t("a website"), name: "business" },
    2: { id: 2, label: _t("an eCommerce"), name: "eCommerce" },
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

export const TONE_OPTIONS = [
    { value: "professional", label: _t("Professional") },
    { value: "friendly", label: _t("Friendly") },
    { value: "inspirational", label: _t("Inspirational") },
    { value: "educational", label: _t("Educational") },
    { value: "playful", label: _t("Playful") },
    { value: "luxury", label: _t("Luxury") },
];

export const PALETTE_SECTIONS = [
    {
        id: "neutral",
        label: _t("Neutral"),
        names: [
            "default-light-13",
            "default-light-12",
            "default-23",
            "default-14",
            "default-27",
            "default-1",
            "default-28",
            "default-21",
        ],
    },
    {
        id: "airy",
        label: _t("Airy"),
        names: [
            "default-light-2",
            "default-light-4",
            "default-light-3",
            "default-light-10",
            "default-light-5",
            "default-light-7",
            "default-light-6",
            "default-light-8",
            "default-light-1",
            "default-24",
        ],
    },
    {
        id: "sophisticated",
        label: _t("Sophisticated"),
        names: [
            "default-light-11",
            "default-7",
            "default-25",
            "default-12",
            "default-22",
            "default-15",
            "default-17",
            "default-20",
        ],
    },
    {
        id: "vibrant",
        label: _t("Vibrant"),
        names: [
            "default-6",
            "default-8",
            "default-9",
            "default-10",
            "default-11",
            "default-13",
            "default-3",
            "default-16",
            "default-18",
            "default-19",
            "default-26",
            "default-5",
            "default-4",
            "default-light-9",
            "default-2",
            "default-light-14",
        ],
    },
];

export const PALETTE_NAMES = PALETTE_SECTIONS.flatMap((section) => section.names);

const FEATURED_PALETTE_PLACEHOLDER = {
    color1: "#868e96",
    color2: "#adb5bd",
    color3: "#ced4da",
    color4: "#dee2e6",
    color5: "#495057",
};

// Attributes for which background color should be retrieved
// from CSS and added in each palette.
export const CUSTOM_BG_COLOR_ATTRS = ["menu", "footer"];

const MAX_NBR_DISPLAY_MAIN_THEMES = 3;
const PREVIEW_IMAGE_SHAPE_URL_REGEX = /^\/?(html_editor|web_editor)\/image_shape(_url)?\//;
const PREVIEW_DYNAMIC_IMAGE_URL_REGEX = /^\/?(html_editor|web_editor)\/(image_)?shape(_url)?\//;

const DESKTOP_PREVIEW_WIDTH = 1400;

/**
 * Returns a list of maximum "resultNbrMax" themes that depends on the wanted
 * industry and the color palette.
 *
 * @param {Object} orm - The orm used for the server call.
 * @param {Object} state - The state that contains the wanted industry and color
 * palette.
 * @param {Number} resultNbrMax - The number of different wanted themes.
 * @returns {Promise<Array>} A list of objects that contains the different
 * theme names and their related text svgs (as result of a Promise). The length
 * of the list is at most 'resultNbrMax'.
 */
async function getRecommendedThemes(orm, state, resultNbrMax = MAX_NBR_DISPLAY_MAIN_THEMES) {
    return orm.call("website", "configurator_recommended_themes", [], {
        industry_id: state.selectedIndustry?.id || 0,
        result_nbr_max: resultNbrMax,
    });
}

function getPreviewPaletteCacheKey(paletteName, themeName, logoPalette) {
    if (paletteName !== "logoPalette" || !logoPalette) {
        return `${themeName}:${paletteName}`;
    }
    return [themeName, "logoPalette", ...[1, 2, 3, 4, 5].map((i) => logoPalette[`color${i}`])].join(
        ":"
    );
}

async function getPreviewPaletteCSS(orm, state, paletteName, logoPalette = state.logoPalette) {
    const cacheKey = getPreviewPaletteCacheKey(
        paletteName,
        state.selectedTheme || "theme_default",
        logoPalette
    );
    if (state.previewPaletteCSS[cacheKey]) {
        return state.previewPaletteCSS[cacheKey];
    }
    if (!state.previewPaletteCSSPromises[cacheKey]) {
        state.previewPaletteCSSPromises[cacheKey] = orm.silent
            .call("website.assets", "configurator_get_palette_preview_css", [
                paletteName,
                paletteName === "logoPalette" ? logoPalette : false,
            ])
            .then((css) => {
                state.previewPaletteCSS[cacheKey] = css;
                delete state.previewPaletteCSSPromises[cacheKey];
                return css;
            })
            .catch((error) => {
                delete state.previewPaletteCSSPromises[cacheKey];
                throw error;
            });
    }
    return state.previewPaletteCSSPromises[cacheKey];
}

//------------------------------------------------------------------------------
// Components
//------------------------------------------------------------------------------

export class SkipButton extends Component {
    static template = "website.Configurator.SkipButton";
    static props = {
        skip: Function,
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
                    this.industrySelection.el.querySelector("input").focus();
                }
                if (selectedIndustry) {
                    this.purposeSelectionRef.el.focus();
                }
            },
            () => [this.state.selectedType, this.state.selectedIndustry]
        );

        this.safariHackFocusedOutDropdown = null;
    }

    onMounted() {
        this.selectWebsitePurpose();
    }
    /**
     * Set the input's parent label value to automatically adapt input size
     * and update the selected industry.
     *
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
        this.state.selectedIndustry = undefined;
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

        matches.push({ label: term, id: -1 });
        return matches.map((match) => ({
            label: match.id === -1 ? _t('Create "%s"', match.label) : match.label,
            labelTermOrder: match.id === -1 ? null : this._getMatchTermOrder(match.label, terms),
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

    selectWebsitePurpose(id) {
        this.state.selectWebsitePurpose(id);
        this.checkDescriptionCompletion();
    }

    checkDescriptionCompletion() {
        const { selectedType, selectedPurpose, selectedIndustry } = this.state;
        if (selectedType && selectedPurpose && selectedIndustry) {
            // If the industry name is not known by the server, send it to the
            // IAP server.
            if (selectedIndustry.id === -1) {
                this.orm.call("website", "configurator_missing_industry", [], {
                    unknown_industry: selectedIndustry.label,
                });
            }
            this.props.navigate(ROUTES.themeSelectionScreen);
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
        }
    }
}

export class ApplyConfiguratorScreen extends Component {
    static template = "";
    static props = ["*"];
    setup() {
        this.websiteService = useService("website");
        this.configuratorProgress = 0;
    }

    async startBuilding() {
        if (!this.state.selectedPalette) {
            const fallbackPaletteName = this.state.palettes["default-25"]
                ? "default-25"
                : Object.keys(this.state.palettes || {})[0];
            if (fallbackPaletteName) {
                this.state.selectPalette(fallbackPaletteName);
            }
        }
        if (!this.state.selectedTheme) {
            this.state.selectedTheme = "theme_default";
        }
        await this.applyConfigurator(this.state.selectedTheme);
    }

    async applyConfigurator(themeName) {
        if (!this.state.selectedIndustry) {
            return this.props.navigate(ROUTES.descriptionScreen);
        }
        if (!this.state.selectedPalette) {
            return this.props.navigate(ROUTES.setupStyleScreen);
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
                    description: _t("Applying the last changes."),
                    flag: "generic",
                },
            ];

            // Server requests are locked during module installation,
            // uninstallation, or upgrade (when running without `workers`), so
            // real-time progress can't be fetched. We simulate it instead.
            const stopProgressSimulation = this.startConfiguratorProgressSimulation();
            this.websiteService.showLoader({
                title: _t("Building your website."),
                loadingSteps,
                getProgress: () => this.configuratorProgress,
                bottomMessageTemplate: "website.website_loader.tour_tip",
            });
            const resp = await attemptConfiguratorApply(
                this.getConfigurationData(this.state.selectedPalette, themeName)
            );

            this.props.clearStorage();
            stopProgressSimulation();

            this.websiteService.redirectOutFromLoader({
                redirectAction: () => {
                    // Here, the website service `goToWebsite` method is not
                    // used because the web client needs to be reloaded after
                    // the new modules have been installed.
                    redirect(
                        `/odoo/action-website.website_preview?website_id=${encodeURIComponent(
                            resp.website_id
                        )}`
                    );
                },
            });
        }
    }

    getConfigurationData(selectedPalette, themeName) {
        const selectedFontConfig = this.state.fonts?.[this.state.selectedFont];
        const toScssString = (value) => (value ? `'${value}'` : undefined);
        return {
            industry_id: this.state.selectedIndustry.id,
            industry_name: this.state.selectedIndustry.label.toLowerCase(),
            selected_palette:
                selectedPalette === "logoPalette"
                    ? [1, 2, 3, 4, 5].map((i) => this.state.logoPalette[`color${i}`])
                    : selectedPalette,
            theme_name: themeName,
            website_purpose:
                WEBSITE_PURPOSES[this.state.selectedPurpose || this.state.formerSelectedPurpose]
                    .name,
            website_type: WEBSITE_TYPES[this.state.selectedType].name,
            logo_attachment_id: this.state.logoAttachmentId,
            selected_font: toScssString(selectedFontConfig?.name),
            selected_headings_font: toScssString(selectedFontConfig?.headingsFamily),
        };
    }

    /**
     * Simulates the progress for website creation, divided into three phases:
     * 1. Initial Phase (0-30%): Fast progress to give the impression of quick
     *    processing.
     * 2. Build Phase (30-90%): Steady progress while the website is generated.
     * 3. Final Phase (90-100%): Slow progress to allow any pending operations
     *    to complete before reaching 100%.
     *
     * @returns {Function} A cleanup function that stops the simulation.
     */
    startConfiguratorProgressSimulation() {
        const INITIAL_PHASE_END = 30;
        const BUILD_PHASE_END = 90;

        let progress = 0;
        let phase = "initial";

        const intervalId = setInterval(() => {
            switch (phase) {
                case "initial":
                    progress += 2;
                    if (progress >= INITIAL_PHASE_END) {
                        phase = "build";
                    }
                    break;

                case "build":
                    progress = Math.min(progress + 0.8, BUILD_PHASE_END);
                    if (progress >= BUILD_PHASE_END) {
                        phase = "final";
                    }
                    break;

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
        this.maxNbrDisplayThemes = 100;
        this.themesByStep = 6;
        this.bottomPageTrigger = useRef("loadMoreThemes");
        this.bottomPageObserver = null;
        const env = useEnv();
        this.state = useState(env.store);
        onWillStart(async () => {
            await this.getThemes();
            if (!this.state.themes.length) {
                this.state.selectedTheme = "theme_default";
                this.props.navigate(ROUTES.setupStyleScreen);
            }
        });
        onMounted(() => {
            this.bottomPageObserver = new IntersectionObserver((entries) => {
                if (entries.some((entry) => entry.isIntersecting)) {
                    this.loadNextThemes();
                }
            });
            if (this.bottomPageTrigger.el) {
                this.bottomPageObserver.observe(this.bottomPageTrigger.el);
            }
        });
        onWillUnmount(() => {
            this.bottomPageObserver?.disconnect();
        });
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

    async chooseTheme(themeName) {
        if (this.state.selectedTheme !== themeName) {
            this.state.recommendedPalettes = undefined;
            this.state.featuredPaletteNames = [];
            this.state.selectedPalette = undefined;
            this.state.fonts = {};
            this.state.fontIds = [];
            this.state.selectedFont = undefined;
        }
        this.state.selectedTheme = themeName;
        this.props.navigate(ROUTES.setupStyleScreen);
    }

    async getThemes() {
        this.uiService.block();
        const themes = await getRecommendedThemes(this.orm, this.state, this.maxNbrDisplayThemes);
        this.state.allThemes = themes;
        this.loadNextThemes();
        this.uiService.unblock();
    }

    loadNextThemes() {
        const allThemes = this.state.allThemes || [];
        if (!allThemes.length) {
            return;
        }
        const nbrThemesToDisplay = Math.min(
            this.state.themes.length + this.themesByStep,
            allThemes.length
        );
        this.state.themes = allThemes.slice(0, nbrThemesToDisplay);
        if (nbrThemesToDisplay >= allThemes.length) {
            this.bottomPageObserver?.disconnect();
        }
    }
}

export class SetupStyleScreen extends ApplyConfiguratorScreen {
    static template = "website.Configurator.SetupStyleScreen";
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useStore();
        this.featuredPalettePlaceholders = [0, 1, 2, 3].map((index) => ({
            name: `featured_palette_placeholder_${index}`,
            ...FEATURED_PALETTE_PLACEHOLDER,
        }));
        this.fontPlaceholders = [0, 1, 2, 3].map((index) => ({
            name: `font_placeholder_${index}`,
        }));
        this.previewState = useState({ initialLoaded: false });
        this.scrollState = useState({
            isStylePanelBottomReached: false,
            isColorPanelBottomReached: false,
        });
        this.previewDevice = useState({ value: "desktop" });
        this.scrollContentRef = useRef("scrollContent");
        this.colorPanelBodyRef = useRef("colorPanelBody");
        this.previewIframeRef = useRef("previewIframe");
        this.logoInputRef = useRef("logoSelectionInput");
        this.isEnterprise = odoo.info && odoo.info.isEnterprise;
        this.toneOptions = TONE_OPTIONS;
        this.state.selectedTone = "inspirational";
        this.images_loaded = false;
        this.closeGeneratorNotification = null;
        this.previewPalettePrefetchId = 0;
        this.previewPalettePrefetchTimeout = null;
        this.previewInlineVhConversionTimeout = null;

        useExternalListener(window, "resize", () => this.scalePreviewIframe());

        onWillStart(() => {
            this.previewState.initialLoaded = false;
            this.state.previewIsLoading = true;
        });
        onMounted(() => {
            document.body.classList.add("o_configurator_notifications_top");
            this.onScrollContent(this.scrollContentRef, "isStylePanelBottomReached");
            this.onScrollContent(this.colorPanelBodyRef, "isColorPanelBottomReached");
            document.getElementById("describeYourWebsiteTextarea").value = _t(
                "Generate the text content for my %(industryName)s business.",
                {
                    industryName: this.state.selectedIndustry.label,
                }
            );
        });
        onWillUnmount(() => {
            document.body.classList.remove("o_configurator_notifications_top");
            this.cancelPreviewPalettePrefetch();
            if (this.previewInlineVhConversionTimeout) {
                browser.clearTimeout(this.previewInlineVhConversionTimeout);
                this.previewInlineVhConversionTimeout = null;
            }
            this.closeGeneratorNotification?.();
            this.closeGeneratorNotification = null;
        });
    }

    onScrollContent(ref, stateKey) {
        const el = ref.el;
        if (!el) {
            return;
        }
        const isBottomReached = el.scrollTop + el.clientHeight >= el.scrollHeight - 1;
        if (this.scrollState[stateKey] !== isBottomReached) {
            this.scrollState[stateKey] = isBottomReached;
        }
    }

    uploadLogo() {
        this.logoInputRef.el.click();
    }

    /**
     * Removes the previously uploaded logo.
     *
     * @param {Event} ev
     */
    async removeLogo(ev) {
        ev.stopPropagation();
        // Permit to trigger onChange even with the same file.
        this.logoInputRef.el.value = "";
        if (this.state.logoAttachmentId) {
            await this._removeAttachments([this.state.logoAttachmentId]);
        }
        this.state.changeLogo();
        this.state.setLogoPalette();
        this.state.featuredPaletteNames = this.completeFeaturedPaletteNames(
            this.state.featuredPaletteNames
        );
        if (this.state.selectedPalette === "logoPalette" && this.state.featuredPaletteNames[0]) {
            await this.setPalette(this.state.featuredPaletteNames[0]);
        }
        this.setPreviewLogo();
    }

    async onLogoChange() {
        const logoSelectInput = this.logoInputRef.el;
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
            const attachment = await rpc("/web_editor/attachment/add_data", {
                name: "logo",
                data: data.split(",")[1],
                is_image: true,
            });
            if (!attachment.error) {
                if (previousLogoAttachmentId) {
                    await this._removeAttachments([previousLogoAttachmentId]);
                }
                this.state.changeLogo(data, attachment.id);
                await this.updateLogoPalette();
                if (this.state.selectedPalette === "logoPalette") {
                    await this.setPalette("logoPalette");
                }
                this.setPreviewLogo();
            } else {
                this.notification.add(attachment.error, {
                    title: file.name,
                });
            }
        }
    }

    setPreviewLogo(iframeDoc = this.previewIframeRef.el?.contentDocument) {
        if (!iframeDoc?.body) {
            return;
        }
        for (const imgEl of iframeDoc.querySelectorAll(
            'a[data-name="Navbar Logo"] img, a.navbar-brand.logo img'
        )) {
            if (!imgEl.dataset.previewOriginalSrc) {
                imgEl.dataset.previewOriginalSrc = imgEl.getAttribute("src") || "";
            }
            imgEl.src = this.state.logo || imgEl.dataset.previewOriginalSrc;
        }
    }

    async updateLogoPalette() {
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
        this.state.setLogoPalette(color1, color2);
    }

    /**
     * Removes the attachments from the DB.
     *
     * @private
     * @param {Array<number>} ids the attachment ids to remove
     */
    async _removeAttachments(ids) {
        rpc("/html_editor/attachment/remove", { ids: ids });
    }

    changeTheme() {
        this.props.navigate(ROUTES.themeSelectionScreen);
    }

    // Fill missing featured slots with recommended palettes, in order.
    completeFeaturedPaletteNames(featuredPaletteNames) {
        for (const palette of this.state.recommendedPalettes || []) {
            if (featuredPaletteNames.length >= 4) {
                break;
            }
            if (!featuredPaletteNames.includes(palette.name)) {
                featuredPaletteNames.push(palette.name);
            }
        }
        return featuredPaletteNames;
    }

    // Keep featured palettes ordered by recent user actions.
    updateFeaturedPaletteNames(paletteName) {
        const featuredPaletteNames = this.state.featuredPaletteNames.filter(
            (featuredPaletteName) => featuredPaletteName !== paletteName
        );
        featuredPaletteNames.unshift(paletteName);
        if (featuredPaletteNames.length > 4) {
            for (let index = featuredPaletteNames.length - 1; index >= 0; index--) {
                if (featuredPaletteNames[index] !== this.state.selectedPalette) {
                    featuredPaletteNames.splice(index, 1);
                    break;
                }
            }
        }
        this.state.featuredPaletteNames = featuredPaletteNames;
    }

    initializePalettesFromPreview() {
        const iframeDoc = this.previewIframeRef.el?.contentDocument;
        const iframeRoot = iframeDoc?.documentElement;
        if (!iframeRoot) {
            return;
        }
        const style = getComputedStyle(iframeRoot);
        const mainPalette = this.cleanValue(style.getPropertyValue("--color-palettes-name"));
        const recommendedPalettes = style
            .getPropertyValue("--recommended-palette-name")
            .replace(/[()]/g, "")
            .split(",")
            .map((value) => this.cleanValue(value))
            .filter(Boolean);
        // Read the theme recommendations from the preview CSS.
        this.state.recommendedPalettes = (
            recommendedPalettes.length ? recommendedPalettes : [mainPalette].filter(Boolean)
        ).map((paletteName) => this.state.palettes[paletteName]);
        // Preserve the current featured order across reloads and page refreshes.
        this.state.featuredPaletteNames = this.completeFeaturedPaletteNames(
            this.state.featuredPaletteNames.length
                ? [...this.state.featuredPaletteNames]
                : this.state.recommendedPalettes.slice(0, 4).map((palette) => palette.name)
        );
        // Keep the selected swatch aligned with the palette currently shown
        // in the preview.
        if (this.state.selectedPalette !== "logoPalette") {
            this.state.selectedPalette = mainPalette || this.state.recommendedPalettes[0]?.name;
        }
    }

    getFeaturedPalettes() {
        return this.state.featuredPaletteNames.map(
            (paletteName) => this.state.palettes[paletteName]
        );
    }

    getOtherPaletteSections() {
        const recommendedPaletteNames = new Set(
            (this.state.recommendedPalettes || []).map((palette) => palette.name)
        );
        return PALETTE_SECTIONS.map((section) => ({
            id: section.id,
            label: section.label,
            palettes: section.names
                .filter((paletteName) => !recommendedPaletteNames.has(paletteName))
                .map((paletteName) => this.state.palettes[paletteName]),
        })).filter((section) => section.palettes.length);
    }

    cancelPreviewPalettePrefetch() {
        this.previewPalettePrefetchId++;
        if (this.previewPalettePrefetchTimeout) {
            browser.clearTimeout(this.previewPalettePrefetchTimeout);
            this.previewPalettePrefetchTimeout = null;
        }
    }

    schedulePreviewPalettePrefetch() {
        this.cancelPreviewPalettePrefetch();
        const requestId = this.previewPalettePrefetchId;
        // Start with the theme recommendations, then continue with common
        // palettes in the background.
        const paletteNames = [
            ...(this.state.recommendedPalettes || []).map((palette) => palette.name),
            ...PALETTE_NAMES,
        ];
        this.previewPalettePrefetchTimeout = browser.setTimeout(async () => {
            this.previewPalettePrefetchTimeout = null;
            for (const paletteName of new Set(paletteNames)) {
                if (requestId !== this.previewPalettePrefetchId) {
                    return;
                }
                await getPreviewPaletteCSS(this.orm, this.state, paletteName).catch(() => {});
                await delay(100);
            }
        }, 500);
    }

    async setPalette(paletteName) {
        this.state.selectedPalette = paletteName;
        if (
            paletteName !== "logoPalette" &&
            !this.state.featuredPaletteNames.includes(paletteName)
        ) {
            this.updateFeaturedPaletteNames(paletteName);
        }
        this.cancelPreviewPalettePrefetch();
        const loadingTimer = browser.setTimeout(() => {
            this.state.previewIsLoading = true;
        }, 500);
        try {
            await this.applyPreviewPalette(paletteName);
        } finally {
            browser.clearTimeout(loadingTimer);
            this.state.previewIsLoading = false;
            this.schedulePreviewPalettePrefetch();
        }
    }

    async applyPreviewPalette(paletteName, iframeDoc = this.previewIframeRef.el?.contentDocument) {
        if (!iframeDoc?.head || !iframeDoc.documentElement) {
            return;
        }
        const css = await getPreviewPaletteCSS(this.orm, this.state, paletteName);
        let styleEl = iframeDoc.getElementById("o_configurator_preview_palette_test");
        if (!styleEl) {
            styleEl = iframeDoc.createElement("style");
            styleEl.id = "o_configurator_preview_palette_test";
            iframeDoc.head.appendChild(styleEl);
        }
        // Read the new palette colors before the CSS is applied.
        const colorValues = {};
        for (const match of css.matchAll(/--o-color-([1-5])\s*:\s*([^;]+);/g)) {
            colorValues[`o-color-${match[1]}`] = match[2].trim();
        }
        this.ensurePreviewShapeSources(iframeDoc);
        // Preload recolored shapes first so the whole preview switches together.
        const { imageSrcUpdates, backgroundImageUpdates } =
            await this.getPreviewDynamicShapeUpdates(iframeDoc, colorValues);
        styleEl.textContent = css;
        this.applyPreviewShapeUpdates(imageSrcUpdates, backgroundImageUpdates);
        this.convertVhToVw(this.previewIframeRef.el, 10 / 16);
    }

    // Rebuild dynamic shape URLs with the current iframe palette colors.
    async updatePreviewDynamicShapes(iframeDoc = this.previewIframeRef.el?.contentDocument) {
        // This is used after iframe reloads, when the preview CSS is already on
        // the page and we only need to sync dynamic shape URLs again.
        this.ensurePreviewShapeSources(iframeDoc);
        const { imageSrcUpdates, backgroundImageUpdates } =
            await this.getPreviewDynamicShapeUpdates(iframeDoc);
        this.applyPreviewShapeUpdates(imageSrcUpdates, backgroundImageUpdates);
    }

    ensurePreviewShapeSources(iframeDoc = this.previewIframeRef.el?.contentDocument) {
        if (!iframeDoc?.documentElement) {
            return;
        }
        const style = getComputedStyle(iframeDoc.documentElement);
        const paletteColors = Object.fromEntries(
            [1, 2, 3, 4, 5]
                .map((i) => [
                    normalizeCSSColor(getCSSVariableValue(`o-color-${i}`, style)),
                    `o-color-${i}`,
                ])
                .filter(([color]) => color)
        );
        const getPaletteShapeURL = (originalSrc) => {
            const url = new URL(originalSrc, window.location.origin);
            url.searchParams.forEach((value, key) => {
                if (!/^c[1-5]$/.test(key)) {
                    return;
                }
                const paletteColorName = paletteColors[normalizeCSSColor(value)];
                if (paletteColorName) {
                    url.searchParams.set(key, paletteColorName);
                }
            });
            return url.pathname + url.search;
        };
        for (const imgEl of iframeDoc.querySelectorAll("img")) {
            if (imgEl.dataset.configuratorOriginalSrc) {
                continue;
            }
            const originalSrc = imgEl.getAttribute("src") || "";
            if (!PREVIEW_IMAGE_SHAPE_URL_REGEX.test(originalSrc)) {
                continue;
            }
            // Keep a palette-based source so shapes follow palette changes.
            imgEl.dataset.configuratorOriginalSrc = getPaletteShapeURL(originalSrc);
        }
        for (const shapeEl of iframeDoc.querySelectorAll(".o_we_shape")) {
            if (shapeEl.dataset.configuratorOriginalBgSrc) {
                continue;
            }
            const originalSrc = getBgImageURLFromEl(shapeEl);
            if (!originalSrc || !PREVIEW_DYNAMIC_IMAGE_URL_REGEX.test(originalSrc)) {
                continue;
            }
            // Keep a palette-based source so shapes follow palette changes.
            shapeEl.dataset.configuratorOriginalBgSrc = getPaletteShapeURL(originalSrc);
        }
    }

    applyPreviewShapeUpdates(imageSrcUpdates, backgroundImageUpdates) {
        imageSrcUpdates.forEach(({ el, originalSrc, src }) => {
            el.dataset.configuratorOriginalSrc = originalSrc;
            el.setAttribute("src", src);
        });
        backgroundImageUpdates.forEach(({ el, originalSrc, src }) => {
            el.dataset.configuratorOriginalBgSrc = originalSrc;
            el.style.setProperty("background-image", `url("${src}")`);
        });
    }

    async getPreviewDynamicShapeUpdates(
        iframeDoc = this.previewIframeRef.el?.contentDocument,
        colorValues = null
    ) {
        if (!iframeDoc?.documentElement) {
            return { imageSrcUpdates: [], backgroundImageUpdates: [] };
        }
        const style = getComputedStyle(iframeDoc.documentElement);
        const colorizeShapeURL = (originalSrc) => {
            const url = new URL(originalSrc, window.location.origin);
            url.searchParams.forEach((value, key) => {
                const match = value.match(/^o-color-([1-5])$/);
                if (/^c[1-5]$/.test(key) && match) {
                    url.searchParams.set(
                        key,
                        colorValues?.[`o-color-${match[1]}`] ||
                            getCSSVariableValue(`o-color-${match[1]}`, style)
                    );
                }
            });
            return url.pathname + url.search;
        };
        const imageSrcUpdates = [];
        for (const imgEl of iframeDoc.querySelectorAll("img")) {
            const src = imgEl.getAttribute("src") || "";
            if (!PREVIEW_DYNAMIC_IMAGE_URL_REGEX.test(src)) {
                continue;
            }
            // Keep the original palette-based URL so each palette change starts
            // from c1=o-color-1, c2=o-color-2, ...
            const originalSrc = imgEl.dataset.configuratorOriginalSrc || src;
            imageSrcUpdates.push({ el: imgEl, originalSrc, src: colorizeShapeURL(originalSrc) });
        }
        const backgroundImageUpdates = [];
        for (const shapeEl of iframeDoc.querySelectorAll(".o_we_shape")) {
            const originalSrc =
                shapeEl.dataset.configuratorOriginalBgSrc || getBgImageURLFromEl(shapeEl);
            if (!originalSrc || !PREVIEW_DYNAMIC_IMAGE_URL_REGEX.test(originalSrc)) {
                continue;
            }
            backgroundImageUpdates.push({
                el: shapeEl,
                originalSrc,
                src: colorizeShapeURL(originalSrc),
            });
        }
        // Wait for the new URLs before applying them to avoid a short flash.
        await Promise.all(
            [...new Set([...imageSrcUpdates, ...backgroundImageUpdates].map(({ src }) => src))].map(
                (src) => loadImage(src).catch(() => null)
            )
        );
        return { imageSrcUpdates, backgroundImageUpdates };
    }

    cleanValue(value) {
        return value.trim().replace(/^['"]|['"]$/g, "");
    }
    async getFonts() {
        const iframeDoc = this.previewIframeRef.el?.contentDocument;
        const iframeRoot = iframeDoc?.documentElement;
        if (!iframeRoot) {
            return;
        }
        const style = getComputedStyle(iframeRoot);
        const numberOfFonts = Number.parseInt(style.getPropertyValue("--number-of-fonts"), 10) || 0;
        const getFontList = (cssVarName) =>
            style
                .getPropertyValue(cssVarName)
                .replace(/[()]/g, "")
                .split(",")
                .map((value) => this.cleanValue(value))
                .filter(Boolean);

        const fonts = {};
        const fontNameToId = {};
        const fontUrls = new Set();
        let nextFontId = 0;

        for (let i = 1; i <= numberOfFonts; i++) {
            const fontName = this.cleanValue(style.getPropertyValue(`--font-number-${i}`));
            const fontFamily = style.getPropertyValue(`--font-family-number-${i}`).trim();
            if (!fontName || !fontFamily) {
                continue;
            }
            const fontId = nextFontId++;
            fonts[fontId] = {
                name: fontName,
                bodyFamily: fontFamily,
                headingsFamily: "",
            };
            if (fontNameToId[fontName] === undefined) {
                fontNameToId[fontName] = fontId;
            }
            const fontUrl = this.cleanValue(style.getPropertyValue(`--font-url-number-${i}`));
            if (fontUrl) {
                fontUrls.add(fontUrl);
            }
        }

        const recommendedBodyFonts = [
            this.cleanValue(style.getPropertyValue("--font")),
            ...getFontList("--alternative-fonts"),
        ].filter(Boolean);
        const recommendedHeadingsFonts = [
            this.cleanValue(style.getPropertyValue("--headings-font")),
            ...getFontList("--alternative-headings-fonts"),
        ].filter(Boolean);
        const recommendedFontIds = [];
        const seenBaseFontIds = {};
        for (const [index, bodyFontName] of recommendedBodyFonts.entries()) {
            const baseFontId = fontNameToId[bodyFontName];
            if (baseFontId === undefined) {
                continue;
            }
            let fontId = baseFontId;
            if (seenBaseFontIds[baseFontId]) {
                fontId = nextFontId++;
                fonts[fontId] = { ...fonts[baseFontId] };
            }
            seenBaseFontIds[baseFontId] = true;
            fonts[fontId].headingsFamily = recommendedHeadingsFonts[index] || "";
            recommendedFontIds.push(fontId);
        }

        const addFontLink = (targetDoc, href) => {
            if (!targetDoc?.head) {
                return;
            }
            if (targetDoc.head.querySelector(`link[href="${href}"]`)) {
                return;
            }
            const link = targetDoc.createElement("link");
            link.rel = "stylesheet";
            link.href = href;
            targetDoc.head.appendChild(link);
        };

        for (const fontUrl of fontUrls) {
            const href = `https://fonts.googleapis.com/css?family=${fontUrl}&display=swap`;
            addFontLink(iframeDoc, href);
            addFontLink(document, href);
        }

        this.state.fonts = fonts;
        this.state.fontIds = recommendedFontIds;
        if (this.state.selectedFont === undefined || !fonts[this.state.selectedFont]) {
            this.state.selectedFont = recommendedFontIds[0];
        }
        const previewFontNames = [...recommendedBodyFonts, ...recommendedHeadingsFonts].filter(
            Boolean
        );
        await Promise.all(
            previewFontNames.map((fontName) =>
                document.fonts.load(`1em "${fontName}"`).catch(() => null)
            )
        );
    }

    setFont(font) {
        this.state.selectedFont = font;
        this.applyPreviewFont();
    }

    setPreviewDevice(device) {
        this.previewDevice.value = device;
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                this.scalePreviewIframe();
            });
        });
    }

    get isPreviewMobile() {
        return this.previewDevice.value === "mobile";
    }

    nextStep() {
        return this.startBuilding();
    }

    async onPreviewIframeLoad() {
        const hadGeneratorNotification = !!this.closeGeneratorNotification;
        const iframeDoc = this.previewIframeRef.el?.contentDocument;
        if (iframeDoc) {
            this.deactivatePreviewInteractions(iframeDoc);
            this.setPreviewLogo(iframeDoc);
            await this.getFonts();
            this.applyPreviewFont();
            if (!this.state.recommendedPalettes?.length) {
                this.initializePalettesFromPreview();
            }
            this.schedulePreviewPalettePrefetch();
            const mainPalette = this.cleanValue(
                getComputedStyle(iframeDoc.documentElement).getPropertyValue(
                    "--color-palettes-name"
                )
            );
            if (
                this.state.selectedPalette &&
                (this.state.selectedPalette === "logoPalette" ||
                    this.state.selectedPalette !== mainPalette)
            ) {
                await this.applyPreviewPalette(this.state.selectedPalette, iframeDoc);
            }
            await this.updatePreviewDynamicShapes(iframeDoc);
        }
        this.closeGeneratorNotification?.();
        this.closeGeneratorNotification = null;
        if (hadGeneratorNotification) {
            this.notification.add(_t("Your website content has been generated."), {
                type: "success",
            });
        }
        this.previewState.initialLoaded = true;
        this.state.previewIsLoading = false;
        this.scalePreviewIframe();
        const iframe = this.previewIframeRef.el;
        this.convertVhToVw(iframe, 10 / 16);
    }

    convertVhToVw(iframe, ratio) {
        const doc = iframe.contentDocument;
        if (!doc) {
            return;
        }

        for (const sheet of doc.styleSheets) {
            let rules;
            try {
                rules = sheet.cssRules;
            } catch {
                continue;
            }

            if (!rules) {
                continue;
            }

            for (const rule of rules) {
                if (!rule.style) {
                    continue;
                }

                for (let i = 0; i < rule.style.length; i++) {
                    const prop = rule.style[i];
                    const value = rule.style.getPropertyValue(prop);

                    if (!value.includes("vh")) {
                        continue;
                    }

                    const newValue = value.replace(/([\d.]+)vh/g, (_, v) => {
                        const vw = parseFloat(v) * ratio;
                        return `${vw}vw`;
                    });

                    const priority = rule.style.getPropertyPriority(prop);
                    rule.style.setProperty(prop, newValue, priority);
                }
            }
        }
    }

    convertInlineVhToVw(iframe, ratio) {
        const doc = iframe.contentDocument;
        if (!doc) {
            return;
        }

        doc.querySelectorAll("*").forEach((el) => {
            for (let i = 0; i < el.style.length; i++) {
                const prop = el.style[i];
                const value = el.style.getPropertyValue(prop);
                if (!value.includes("vh")) {
                    continue;
                }
                const newValue = value.replace(/([\d.]+)vh/g, (_, v) => {
                    const vw = parseFloat(v) * ratio;
                    return `${vw}vw`;
                });
                const priority = el.style.getPropertyPriority(prop);
                el.style.setProperty(prop, newValue, priority);
            }
        });
    }

    scalePreviewIframe() {
        const iframe = this.previewIframeRef.el;
        if (!iframe) {
            return;
        }
        if (this.isPreviewMobile) {
            iframe.style.removeProperty("width");
            iframe.style.removeProperty("height");
            iframe.style.removeProperty("transform");
            iframe.style.removeProperty("transform-origin");
            iframe.style.removeProperty("flex");
            return;
        }

        const previewContainer = iframe.parentElement;

        const topBarHeight =
            previewContainer.querySelector(".o_configurator_preview_iframe_topbar").offsetHeight ||
            0;

        const availableWidth = previewContainer.clientWidth;
        const availableHeight = previewContainer.clientHeight - topBarHeight;

        if (!availableWidth || !availableHeight) {
            return;
        }

        const scale = Math.min(1, availableWidth / DESKTOP_PREVIEW_WIDTH);

        iframe.style.setProperty("width", `${DESKTOP_PREVIEW_WIDTH}px`, "important");
        iframe.style.setProperty("height", `${Math.floor(availableHeight / scale)}px`, "important");
        iframe.style.setProperty("transform-origin", "top left");
        iframe.style.setProperty("transform", `scale(${scale})`);
        iframe.style.setProperty("flex", "0 0 auto", "important");
        if (this.previewInlineVhConversionTimeout) {
            browser.clearTimeout(this.previewInlineVhConversionTimeout);
        }
        this.previewInlineVhConversionTimeout = browser.setTimeout(() => {
            this.previewInlineVhConversionTimeout = null;
            this.convertInlineVhToVw(iframe, 10 / 16);
        }, 250);
    }

    deactivatePreviewInteractions(iframeDoc) {
        const stopInteraction = (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
        };
        iframeDoc.addEventListener("click", stopInteraction, true);
        iframeDoc.addEventListener("submit", stopInteraction, true);
    }

    applyPreviewFont(iframeDoc = this.previewIframeRef.el?.contentDocument) {
        if (iframeDoc?.body) {
            const fontConfig = this.state.fonts?.[this.state.selectedFont];
            if (!fontConfig) {
                return;
            }
            iframeDoc.body.style.fontFamily = fontConfig.bodyFamily || "";
            for (const el of iframeDoc.querySelectorAll(
                "h1, h2, h3, h4, h5, h6, .display-1, .display-2, .display-3, .display-4"
            )) {
                el.style.fontFamily = fontConfig.headingsFamily;
            }
        }
    }

    changeTone(tone) {
        this.state.selectedTone = tone;
    }

    generateContent() {
        const userPrompt = document.getElementById("describeYourWebsiteTextarea").value || "";
        const params = new URLSearchParams({
            industry: this.state.selectedIndustry.label,
            industry_id: this.state.selectedIndustry.id,
            install_theme: "0",
            theme_name: this.state.selectedTheme || "theme_default",
            generate_content: "1",
            user_prompt: userPrompt !== "" ? userPrompt : null,
            tone: this.state.selectedTone || null,
            with_images: "1",
        });
        const iframe = this.previewIframeRef.el;
        if (iframe) {
            this.closeGeneratorNotification?.();
            this.closeGeneratorNotification = this.notification.add(
                markup`<i class="fa fa-circle-o-notch fa-spin me-2" role="img" aria-label="${_t(
                    "Loading"
                )}"></i>${_t("Generating your website content with AI...")}`,
                {
                    type: "info",
                    sticky: true,
                }
            );
            iframe.src = `/website/configurator/preview?${params.toString()}&preview_ts=${Date.now()}`;
        }
    }

    get previewUrl() {
        const params = new URLSearchParams({
            industry: this.state.selectedIndustry.label,
            industry_id: this.state.selectedIndustry.id,
            install_theme: "1",
            theme_name: this.state.selectedTheme || "theme_default",
            generate_content: "0",
            with_images: "1",
        });
        this.images_loaded = true;
        return `/website/configurator/preview?${params.toString()}`;
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

    getWebsitePurpose() {
        return Object.values(WEBSITE_PURPOSES);
    }

    getSelectedPurpose(id) {
        return id && WEBSITE_PURPOSES[id];
    }

    getThemeName(idx) {
        return this.themes.length > idx && this.themes[idx].name;
    }

    //-------------------------------------------------------------------------
    // Actions
    //-------------------------------------------------------------------------

    selectWebsiteType(id) {
        this.selectedType = id;
    }

    selectWebsitePurpose(id) {
        // Keep track or the former selection in order to be able to keep
        // the auto-advance navigation scheme while being able to use the
        // browser's back and forward buttons.
        if (!id && this.selectedPurpose) {
            this.formerSelectedPurpose = this.selectedPurpose;
        }
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
        this.selectedPalette = paletteName;
    }

    setLogoPalette(color1, color2) {
        if (color1 && color2) {
            if (color1 === color2) {
                color2 = mixCssColors("#FFFFFF", color1, 0.2);
            }
            const logoPalette = {
                color1: color1,
                color2: color2,
                color3: mixCssColors("#FFFFFF", color2, 0.9),
                color4: "#FFFFFF",
                color5: mixCssColors(color1, "#000000", 0.125),
            };
            CUSTOM_BG_COLOR_ATTRS.forEach((attr) => {
                logoPalette[attr] = logoPalette[this.defaultColors[attr]];
            });
            this.logoPalette = logoPalette;
        } else {
            this.logoPalette = undefined;
        }
        // Keep the extracted logo palette available without changing selection.
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
        DescriptionScreen,
        ThemeSelectionScreen,
        SetupStyleScreen,
    };
    static template = "website.Configurator.Configurator";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.website = useService("website");

        // Using the back button must update the router state.
        useExternalListener(window, "popstate", (ev) => {
            // FIXME: this doesn't work unless this component is already mounted so navigating through
            // history from a different client action will not work.
            if (ev.state && "configuratorStep" in ev.state) {
                // Do not use navigate because URL is already updated.
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
            this.websiteId = (await this.orm.call("website", "get_current_website"))[0];

            await store.start(() => this.getInitialState());
            this.updateStorage(store);
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
        if (this.state.currentStep === ROUTES.themeSelectionScreen) {
            return ThemeSelectionScreen;
        } else if (this.state.currentStep === ROUTES.setupStyleScreen) {
            return SetupStyleScreen;
        }
        return DescriptionScreen;
    }

    get componentProps() {
        const props = {
            skip: this.skipConfigurator.bind(this),
            navigate: this.navigate.bind(this),
        };
        if (
            this.state.currentStep === ROUTES.themeSelectionScreen ||
            this.state.currentStep === ROUTES.setupStyleScreen
        ) {
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

        // Load palettes from the current CSS
        const palettes = {};
        const style = window.getComputedStyle(document.documentElement);

        const paletteNames = getCSSVariableValue("palette-names", style)
            .replace(/[()]/g, "")
            .split(/[,\s]+/)
            .map((name) => name.trim().replace(/^['"]|['"]$/g, ""))
            .filter(Boolean);

        const allPaletteNames = paletteNames.length ? paletteNames : PALETTE_NAMES;

        allPaletteNames.forEach((paletteName) => {
            const palette = {
                name: paletteName,
            };
            for (let j = 1; j <= 5; j += 1) {
                palette[`color${j}`] = getCSSVariableValue(
                    `o-palette-${paletteName}-o-color-${j}`,
                    style
                );
            }
            CUSTOM_BG_COLOR_ATTRS.forEach((attr) => {
                palette[attr] = getCSSVariableValue(`o-palette-${paletteName}-${attr}-bg`, style);
            });
            palettes[paletteName] = palette;
        });

        const localState = JSON.parse(sessionStorage.getItem(this.storageItemName));
        if (localState) {
            return Object.assign(r, {
                featuredPaletteNames: [],
                ...localState,
                palettes,
                previewPaletteCSS: {},
                previewPaletteCSSPromises: {},
                themes: [],
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
            selectedPurpose: undefined,
            formerSelectedPurpose: undefined,
            selectedIndustry: undefined,
            selectedPalette: undefined,
            selectedTheme: undefined,
            previewIsLoading: false,
            featuredPaletteNames: [],
            logoPalette: undefined,
            defaultColors: defaultColors,
            palettes: palettes,
            previewPaletteCSS: {},
            previewPaletteCSSPromises: {},
            themes: [],
            logoAttachmentId: undefined,
        });
    }

    updateStorage(state) {
        const newState = JSON.stringify({
            defaultColors: state.defaultColors,
            logo: state.logo,
            logoAttachmentId: state.logoAttachmentId,
            selectedIndustry: state.selectedIndustry,
            selectedPalette: state.selectedPalette,
            selectedTheme: state.selectedTheme,
            selectedPurpose: state.selectedPurpose,
            formerSelectedPurpose: state.formerSelectedPurpose,
            selectedType: state.selectedType,
            selectedFont: state.selectedFont,
            featuredPaletteNames: state.featuredPaletteNames,
            logoPalette: state.logoPalette,
        });
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
        // the web client needs to be reloaded after the new modules have
        // been installed.
        await this.action.doAction(redirectUrl);
    }
}

registry.category("actions").add("website_configurator", Configurator);
