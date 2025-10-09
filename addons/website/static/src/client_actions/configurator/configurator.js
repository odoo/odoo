/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
const sessionStorage = browser.sessionStorage;
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { delay } from "@web/core/utils/concurrency";
import { getDataURLFromFile, redirect } from "@web/core/utils/urls";
import weUtils from '@web_editor/js/common/utils';
import { _t } from "@web/core/l10n/translation";
import { svgToPNG, webpToPNG } from "@website/js/utils";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { mixCssColors } from '@web/core/utils/colors';
import { router } from "@web/core/browser/router";
import {
    Component,
    onMounted,
    reactive,
    useEffect,
    useEnv,
    useRef,
    useState,
    useSubEnv,
    onWillStart,
    useExternalListener,
} from "@odoo/owl";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

export const ROUTES = {
    descriptionScreen: 2,
    paletteSelectionScreen: 3,
    featuresSelectionScreen: 4,
    themeSelectionScreen: 5,
};

export const WEBSITE_TYPES = {
    1: {id: 1, label: _t("a business website"), name: 'business'},
    2: {id: 2, label: _t("an online store"), name: 'online_store'},
    3: {id: 3, label: _t("a blog"), name: 'blog'},
    4: {id: 4, label: _t("an event website"), name: 'event'},
    5: {id: 5, label: _t("an elearning platform"), name: 'elearning'},
};

export const WEBSITE_PURPOSES = {
    1: {id: 1, label: _t("get leads"), name: 'get_leads'},
    2: {id: 2, label: _t("develop the brand"), name: 'develop_brand'},
    3: {id: 3, label: _t("sell more"), name: 'sell_more'},
    4: {id: 4, label: _t("inform customers"), name: 'inform_customers'},
    5: {id: 5, label: _t("schedule appointments"), name: 'schedule_appointments'},
};

export const PALETTE_NAMES = [
    'default-light-1',
    'default-light-2',
    'default-light-4',
    'default-light-3',
    'default-light-5',
    'default-24',
    'default-light-7',
    'default-light-6',
    'default-light-11',
    'default-light-14',
    'default-light-8',
    'default-6',
    'default-7',
    'default-8',
    'default-9',
    'default-23',
    'default-25',
    'default-12',
    'default-14',
    'default-22',
    'default-15',
    'default-16',
    'default-17',
    'default-light-10',
    'default-19',
    'default-20',
    'default-5',
    'default-4',
    'default-light-9',
    'default-2',
    'default-light-13',
    'default-27',
    'default-light-12',
    'default-1',
    'default-28',
    'default-21',
];

// Attributes for which background color should be retrieved
// from CSS and added in each palette.
export const CUSTOM_BG_COLOR_ATTRS = ["menu", "footer"];

const MAX_NBR_DISPLAY_MAIN_THEMES = 3;

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
    return orm.call("website",
        "configurator_recommended_themes",
        [],
        {
            "industry_id": state.selectedIndustry.id,
            "palette": state.selectedPalette,
            "result_nbr_max": resultNbrMax,
        },
    );
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

export class WelcomeScreen extends Component {
    static template = "website.Configurator.WelcomeScreen";
    static components = { SkipButton };
    static props = {
        skip: Function,
        navigate: Function,
    };
    setup() {
        this.state = useStore();
    }

    goToDescription() {
        this.props.navigate(ROUTES.descriptionScreen);
    }
}

export class IndustrySelectionAutoComplete extends AutoComplete {
    static timeout = 400;

    get dropdownOptions() {
        return {
            ...super.dropdownOptions,
            position: "bottom-fit",
        };
    }

    get ulDropdownClass() {
        return `${super.ulDropdownClass} custom-ui-autocomplete shadow-lg border-0 o_configurator_show_fast o_configurator_industry_dropdown`;
    }
}

export class DescriptionScreen extends Component {
    static template = 'website.Configurator.DescriptionScreen';
    static components = { SkipButton, AutoComplete: IndustrySelectionAutoComplete };
    static props = {
        navigate: Function,
        skip: Function,
    };
    setup() {
        this.industrySelection = useRef('industrySelection');
        this.state = useStore();
        this.orm = useService('orm');

        onMounted(() => this.onMounted());
    }

    onMounted() {
        this.selectWebsitePurpose();
    }
    /**
     * Set the input's parent label value to automatically adapt input size
     * and update the selected industry.
     *
     * @private
     * @param {Object} suggestion an industry
     */
    _setSelectedIndustry(suggestion) {
        const { label, id } = Object.getPrototypeOf(suggestion);
        this.state.selectIndustry(label, id);
        this.checkDescriptionCompletion();
    }

    get sources() {
        return [
            {
                options: (request) => {
                    return request.length < 1 ? [] : this._autocompleteSearch(request);
                },
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
        const terms = term.toLowerCase().split(/[|,\n]+/);
        const limit = 30;
        const sortLimit = 7;
        // `this.state.industries` is already sorted by hit count (from IAP).
        // That order should be kept after manipulating the recordset.
        let matches = this.state.industries.filter((val, index) => {
            // To match, every term should be contained in either the label or a
            // synonym
            for (const candidate of [val.label, ...(val.synonyms || '').split(/[|,\n]+/)]) {
                if (terms.every(term => candidate.toLowerCase().includes(term))) {
                    return true;
                }
            }
        });
        if (matches.length > limit) {
            // Keep matches with the least number of words so that e.g.
            // "restaurant" remains available even if there are 30 specific
            // sub-types that have a higher hit count.
            matches = matches.sort((x, y) => x.wordCount - y.wordCount)
                             .slice(0, limit)
                             .sort((x, y) => x.hitCountOrder - y.hitCountOrder);
        }
        if (matches.length <= sortLimit) {
            // Sort results by ascending label if few of them.
            matches = matches.sort((x, y) => (x.label < y.label ? -1 : x.label > y.label ? 1 : 0));
        }
        return matches.length ? matches : [{ label: term, id: -1 }];
    }

    selectWebsiteType(id) {
        this.state.selectWebsiteType(id);
        setTimeout(() => {
            this.industrySelection.el.querySelector("input").focus();
        });
        this.checkDescriptionCompletion();
    }

    selectWebsitePurpose(id) {
        this.state.selectWebsitePurpose(id);
        this.checkDescriptionCompletion();
    }

    checkDescriptionCompletion() {
        const {selectedType, selectedPurpose, selectedIndustry} = this.state;
        if (selectedType && selectedPurpose && selectedIndustry) {
            // If the industry name is not known by the server, send it to the
            // IAP server.
            if (selectedIndustry.id === -1) {
                this.orm.call('website', 'configurator_missing_industry', [], {
                    'unknown_industry': selectedIndustry.label,
                });
            }
            this.props.navigate(ROUTES.paletteSelectionScreen);
        }
    }
}

export class PaletteSelectionScreen extends Component {
    static components = {SkipButton};
    static template = 'website.Configurator.PaletteSelectionScreen';
    static props = {
        navigate: Function,
        skip: Function,
    };
    setup() {
        this.state = useStore();
        this.logoInputRef = useRef('logoSelectionInput');
        this.notification = useService("notification");
        this.orm = useService('orm');

        onMounted(() => {
            if (this.state.logo) {
                this.updatePalettes();
            }
        });
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
        // Remove recommended palette.
        this.state.setRecommendedPalette();
    }

    async changeLogo() {
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
            const attachment = await rpc('/web_editor/attachment/add_data', {
                'name': 'logo',
                'data': data.split(',')[1],
                'is_image': true,
            });
            if (!attachment.error) {
                if (previousLogoAttachmentId) {
                    await this._removeAttachments([previousLogoAttachmentId]);
                }
                this.state.changeLogo(data, attachment.id);
                this.updatePalettes();
            } else {
                this.notification.add(
                    attachment.error,
                    {
                        title: file.name,
                    }
                );
            }
        }
    }

    async updatePalettes() {
        let img = this.state.logo;
        if (img.startsWith('data:image/svg+xml')) {
            img = await svgToPNG(img);
        }
        if (img.startsWith('data:image/webp')) {
            img = await webpToPNG(img);
        }
        img = img.split(',')[1];
        const [color1, color2] = await this.orm.call('base.document.layout',
            'extract_image_primary_secondary_colors',
            [img],
            {mitigate: 255},
        );
        this.state.setRecommendedPalette(color1, color2);
    }

    selectPalette(paletteName) {
        this.state.selectPalette(paletteName);
        this.props.navigate(ROUTES.featuresSelectionScreen);
    }

    /**
     * Removes the attachments from the DB.
     *
     * @private
     * @param {Array<number>} ids the attachment ids to remove
     */
    async _removeAttachments(ids) {
        rpc("/web_editor/attachment/remove", { ids: ids });
    }
}

export class ApplyConfiguratorScreen extends Component {
    static template = "";
    static props = ["*"];
    setup() {
        this.websiteService = useService('website');
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
                return await this.orm.silent.call('website',
                    'configurator_apply', [], data
                );
            } catch (error) {
                // Wait a bit before retrying or allowing manual retry.
                await delay(5000);
                if (retryCount < 3) {
                    return attemptConfiguratorApply(data, retryCount + 1);
                }
                document.querySelector('.o_website_loader_container').remove();
                throw error;
            }
        };

        if (themeName !== undefined) {
            const selectedFeatures = Object.values(this.state.features).filter((feature) => feature.selected).map((feature) => feature.id);
            this.websiteService.showLoader({
                showTips: true,
                selectedFeatures: selectedFeatures,
                showWaitingMessages: true,
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

            const data = {
                'selected_features': selectedFeatures,
                'industry_id': this.state.selectedIndustry.id,
                'industry_name': this.state.selectedIndustry.label.toLowerCase(),
                'selected_palette': selectedPalette,
                'theme_name': themeName,
                'website_purpose': WEBSITE_PURPOSES[
                    this.state.selectedPurpose || this.state.formerSelectedPurpose
                ].name,
                'website_type': WEBSITE_TYPES[this.state.selectedType].name,
                'logo_attachment_id': this.state.logoAttachmentId,
            };
            const resp = await attemptConfiguratorApply(data);

            this.props.clearStorage();

            this.websiteService.prepareOutLoader();
            // Here the website service goToWebsite method is not used because
            // the web client needs to be reloaded after the new modules have
            // been installed.
            redirect(`/odoo/action-website.website_preview?website_id=${encodeURIComponent(resp.website_id)}`);
        }
    }
}

export class FeaturesSelectionScreen extends ApplyConfiguratorScreen {
    static components = {SkipButton};
    static template = 'website.Configurator.FeatureSelection';
    setup() {
        super.setup();

        this.orm = useService("orm");
        this.state = useStore();
    }

    async buildWebsite() {
        const industryId = this.state.selectedIndustry && this.state.selectedIndustry.id;
        if (!industryId) {
            return this.props.navigate(ROUTES.descriptionScreen);
        }
        const themes = await getRecommendedThemes(this.orm, this.state);

        if (!themes.length) {
            await this.applyConfigurator('theme_default');
        } else {
            this.state.updateRecommendedThemes(themes);
            this.props.navigate(ROUTES.themeSelectionScreen);
        }
    }
}

export class ThemeSelectionScreen extends ApplyConfiguratorScreen {
    static template = "website.Configurator.ThemeSelectionScreen";
    setup() {
        super.setup();

        this.uiService = useService('ui');
        this.orm = useService('orm');
        this.maxNbrDisplayExtraThemes = 100;
        const env = useEnv();
        env.store["extraThemesLoaded"] = false;
        env.store["extraThemes"] = [];
        this.state = useState(env.store);
        this.themeSVGPreviews = [useRef('ThemePreview1'), useRef('ThemePreview2'), useRef('ThemePreview3')];
        this.extraThemesButtonRef = useRef("extraThemesButton");
        this.extraThemeSVGPreviews = [];
        for (let i = 0; i < this.maxNbrDisplayExtraThemes; i++) {
            this.extraThemeSVGPreviews.push(useRef(`ExtraThemePreview${i}`));
        }

        onMounted(() => {
            this.blockUiDuringImageLoading(this.state.themes, this.themeSVGPreviews);
        });

        useEffect(
            () => this.blockUiDuringImageLoading(this.state.extraThemes, this.extraThemeSVGPreviews),
            () => [this.state.extraThemes]
        );
    }

    /**
     * The button should be shown if we never tried to load the extra themes and
     * if they are enough main themes already displayed. If this last condition
     * is not fulfilled, there is no need to display the button as no more will
     * be displayed.
     */
    get showViewMoreThemesButton() {
        return !this.state.extraThemesLoaded
            && this.state.themes.length === MAX_NBR_DISPLAY_MAIN_THEMES;
    }

    /**
     * Transforms text svgs into svg elements and adds a loading effect that
     * blocks the UI during the loading of the images inside those svg elements.
     *
     * @param {Array<Object>} themes - The text svgs.
     * @param {Array} themeSVGPreviews - A reference to the svg elements.
     */
    blockUiDuringImageLoading(themes, themeSVGPreviews) {
        if (!themes.length) {
            // There is no svg to transform
            return;
        }
        const proms = [];
        this.uiService.block({delay: 700});
        themes.forEach((theme, idx) => {
            const svgEl = new DOMParser().parseFromString(theme.svg, "image/svg+xml").documentElement;
            for (const imgEl of svgEl.querySelectorAll("image")) {
                proms.push(new Promise((resolve, reject) => {
                    imgEl.addEventListener("load", () => {
                        resolve(imgEl);
                    }, {once: true});
                    imgEl.addEventListener("error", () => {
                        reject(imgEl);
                    }, {once: true});
                }));
            }
            themeSVGPreviews[idx].el.appendChild(svgEl);
        });
        // When all the images inside the svgs are loaded then remove the
        // loading effect.
        Promise.allSettled(proms).then(() => {
            this.uiService.unblock();
        });
    }

    async chooseTheme(themeName) {
        await this.applyConfigurator(themeName);
    }

    async getMoreThemes() {
        this.uiService.block();
        const themes = await getRecommendedThemes(
            this.orm,
            this.state,
            this.maxNbrDisplayExtraThemes
        );
        // Filter the extra themes to not propose a theme that is already
        // present in the main themes.
        const mainThemeNames = this.state.themes.map((theme) => theme.name);
        this.state.extraThemes = themes.filter((extraTheme) => !mainThemeNames.includes(extraTheme.name));
        this.state.extraThemesLoaded = true;
        this.uiService.unblock();
    }

    getExtraThemeName(idx) {
        return this.state.extraThemes.length > idx && this.state.extraThemes[idx].name;
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
        return palette ? (palette.name || 'recommendedPalette') : false;
    }

    //-------------------------------------------------------------------------
    // Actions
    //-------------------------------------------------------------------------

    selectWebsiteType(id) {
        Object.values(this.features).filter((feature) => feature.module_state !== 'installed').forEach((feature) => {
            feature.selected = feature.website_config_preselection.includes(WEBSITE_TYPES[id].name);
        });
        this.selectedType = id;
    }

    selectWebsitePurpose(id) {
        // Keep track or the former selection in order to be able to keep
        // the auto-advance navigation scheme while being able to use the
        // browser's back and forward buttons.
        if (!id && this.selectedPurpose) {
            this.formerSelectedPurpose = this.selectedPurpose;
        }
        Object.values(this.features).filter((feature) => feature.module_state !== 'installed').forEach((feature) => {
            // need to check id, since we set to undefined in mount() to avoid the auto next screen on back button
            feature.selected |= id && feature.website_config_preselection.includes(WEBSITE_PURPOSES[id].name);
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
        if (paletteName === 'recommendedPalette') {
            this.selectedPalette = this.recommendedPalette;
        } else {
            this.selectedPalette = this.palettes[paletteName];
        }
    }

    toggleFeature(featureId) {
        const feature = this.features[featureId];
        const isModuleInstalled = feature.module_state === 'installed';
        feature.selected = !feature.selected || isModuleInstalled;
    }

    setRecommendedPalette(color1, color2) {
        if (color1 && color2) {
            if (color1 === color2) {
                color2 = mixCssColors('#FFFFFF', color1, 0.2);
            }
            const recommendedPalette = {
                color1: color1,
                color2: color2,
                color3: mixCssColors('#FFFFFF', color2, 0.9),
                color4: '#FFFFFF',
                color5: mixCssColors(color1, '#000000', 0.125),
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

function useStore() {
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
    static template = 'website.Configurator.Configurator';
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService('orm');
        this.action = useService('action');

        // Using the back button must update the router state.
        useExternalListener(window, "popstate", (ev) => {
            // FIXME: this doesn't work unless this component is already mounted so navigating through
            // history from a different client action will not work.
            if (ev.state && "configuratorStep" in ev.state) {
                // Do not use navigate because URL is already updated.
                this.state.currentStep = ev.state.configuratorStep;
            }
        });

        const initialStep = this.props.action.context.params && this.props.action.context.params.step;
        const store = reactive(new Store(), () => this.updateStorage(store));

        this.state = useState({
            currentStep: initialStep,
        });

        useSubEnv({ store });

        onWillStart(async () => {
            this.websiteId = (await this.orm.call('website', 'get_current_website')).match(/\d+/)[0];

            await store.start(() => this.getInitialState());
            this.updateStorage(store);
            if (store.redirect_url) {
                // If redirect_url exists, it means configurator_done is already
                // true, so we can skip the configurator flow.
                this.clearStorage();
                await this.action.doAction(store.redirect_url);
            }
            if (!store.industries) {
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
        return `/website/configurator${this.state.currentStep ? `/${encodeURIComponent(this.state.currentStep)}` : ''}`;
    }

    get storageItemName() {
        return `websiteConfigurator${this.websiteId}`;
    }

    updateBrowserUrl() {
        history.pushState({ skipRouteChange: true, configuratorStep: this.state.currentStep }, '', this.pathname);
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
        var results = await this.orm.call('website', 'configurator_init');
        const r = {
            industries: results.industries,
            logo: results.logo ? 'data:image/png;base64,' + results.logo : false,
            redirect_url: results.redirect_url,
        };
        r.industries = r.industries.map((industry, index) => ({
            ...industry,
            wordCount: industry.label.split(" ").length,
            hitCountOrder: index,
        }));

        // Load palettes from the current CSS
        const palettes = {};
        const style = window.getComputedStyle(document.documentElement);

        PALETTE_NAMES.forEach((paletteName) => {
            const palette = {
                name: paletteName
            };
            for (let j = 1; j <= 5; j += 1) {
                palette[`color${j}`] = weUtils.getCSSVariableValue(`o-palette-${paletteName}-o-color-${j}`, style);
            }
            CUSTOM_BG_COLOR_ATTRS.forEach((attr) => {
                palette[attr] = weUtils.getCSSVariableValue(`o-palette-${paletteName}-${attr}-bg`, style);
            });
            palettes[paletteName] = palette;
        });

        const localState = JSON.parse(sessionStorage.getItem(this.storageItemName));
        if (localState) {
            let themes = [];
            if (localState.selectedIndustry && localState.selectedPalette) {
                themes = await getRecommendedThemes(this.orm, localState);
            }
            return Object.assign(r, {...localState, palettes, themes});
        }

        const features = {};
        results.features.forEach(feature => {
            features[feature.id] = Object.assign({}, feature, {selected: feature.module_state === 'installed'});
            const wtp = features[feature.id]['website_config_preselection'];
            features[feature.id]['website_config_preselection'] = wtp ? wtp.split(',') : [];
        });

        // Palette color used by default as background color for menu and footer.
        // Needed to build the recommended palette.
        const defaultColors = {};
        CUSTOM_BG_COLOR_ATTRS.forEach((attr) => {
            const color = weUtils.getCSSVariableValue(`o-default-${attr}-bg`, style);
            const match = color.match(/o-color-(?<idx>[1-5])/);
            const colorIdx = parseInt(match.groups['idx']);
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
        await this.orm.call('website', 'configurator_skip');
        this.clearStorage();
        this.action.doAction('website.theme_install_kanban_action', {
            clearBreadcrumbs: true,
        });
    }
}

registry.category('actions').add('website_configurator', Configurator);
