/** @odoo-module **/

import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { delay } from "@web/core/utils/concurrency";
import { getDataURLFromFile } from "@web/core/utils/urls";
import weUtils from '@web_editor/js/common/utils';
import { _t } from "@web/core/l10n/translation";
import { svgToPNG, webpToPNG } from "@website/js/utils";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { mixCssColors } from '@web/core/utils/colors';
import {
    Component,
    onMounted,
    reactive,
    useEnv,
    useRef,
    useState,
    useSubEnv,
    onWillStart,
    useExternalListener,
} from "@odoo/owl";

const ROUTES = {
    descriptionScreen: 2,
    paletteSelectionScreen: 3,
    featuresSelectionScreen: 4,
    themeSelectionScreen: 5,
};

const WEBSITE_TYPES = {
    1: {id: 1, label: _t("a business website"), name: 'business'},
    2: {id: 2, label: _t("an online store"), name: 'online_store'},
    3: {id: 3, label: _t("a blog"), name: 'blog'},
    4: {id: 4, label: _t("an event website"), name: 'event'},
    5: {id: 5, label: _t("an elearning platform"), name: 'elearning'},
};

const WEBSITE_PURPOSES = {
    1: {id: 1, label: _t("get leads"), name: 'get_leads'},
    2: {id: 2, label: _t("develop the brand"), name: 'develop_brand'},
    3: {id: 3, label: _t("sell more"), name: 'sell_more'},
    4: {id: 4, label: _t("inform customers"), name: 'inform_customers'},
    5: {id: 5, label: _t("schedule appointments"), name: 'schedule_appointments'},
};

const PALETTE_NAMES = [
    'default-1',
    'default-2',
    'default-3',
    'default-4',
    'default-5',
    'default-6',
    'default-7',
    'default-8',
    'default-9',
    'default-10',
    'default-11',
    'default-12',
    'default-13',
    'default-14',
    'default-15',
    'default-16',
    'default-17',
    'default-18',
    'default-19',
    'default-20',
];

// Attributes for which background color should be retrieved
// from CSS and added in each palette.
const CUSTOM_BG_COLOR_ATTRS = ['menu', 'footer'];

//------------------------------------------------------------------------------
// Components
//------------------------------------------------------------------------------

class SkipButton extends Component {}
SkipButton.template = 'website.Configurator.SkipButton';

class WelcomeScreen extends Component {
    setup() {
        this.state = useStore();
    }

    goToDescription() {
        this.props.navigate(ROUTES.descriptionScreen);
    }
}

Object.assign(WelcomeScreen, {
    components: {SkipButton},
    template: 'website.Configurator.WelcomeScreen',
});

class IndustrySelectionAutoComplete extends AutoComplete {
    static timeout = 400;

    get dropdownOptions() {
        return {
            ...super.dropdownOptions,
            position: "bottom-fit",
        }
    }

    get ulDropdownClass() {
        return `${super.ulDropdownClass} custom-ui-autocomplete shadow-lg border-0 o_configurator_show_fast o_configurator_industry_dropdown`
    }
}

class DescriptionScreen extends Component {
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

Object.assign(DescriptionScreen, {
    components: { SkipButton, AutoComplete: IndustrySelectionAutoComplete },
    template: 'website.Configurator.DescriptionScreen',
});

class PaletteSelectionScreen extends Component {
    setup() {
        this.state = useStore();
        this.logoInputRef = useRef('logoSelectionInput');
        this.notification = useService("notification");
        this.rpc = useService("rpc");
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
            const data = await getDataURLFromFile(file);
            const attachment = await this.rpc('/web_editor/attachment/add_data', {
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
        this.rpc("/web_editor/attachment/remove", { ids: ids });
    }
}

Object.assign(PaletteSelectionScreen, {
    components: {SkipButton},
    template: 'website.Configurator.PaletteSelectionScreen',
});

class ApplyConfiguratorScreen extends Component {
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
            window.location.replace(`/web#action=website.website_preview&website_id=${encodeURIComponent(resp.website_id)}`);
        }
    }
}

export class FeaturesSelectionScreen extends ApplyConfiguratorScreen {
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
        const themes = await this.orm.call('website',
            'configurator_recommended_themes',
            [],
            {
                'industry_id': industryId,
                'palette': this.state.selectedPalette,
            },
        );

        if (!themes.length) {
            await this.applyConfigurator('theme_default');
        } else {
            this.state.updateRecommendedThemes(themes);
            this.props.navigate(ROUTES.themeSelectionScreen);
        }
    }
}

Object.assign(FeaturesSelectionScreen, {
    components: {SkipButton},
    template: 'website.Configurator.FeatureSelection',
});

class ThemeSelectionScreen extends ApplyConfiguratorScreen {
    setup() {
        super.setup();

        this.uiService = useService('ui');
        this.orm = useService('orm');
        this.state = useStore();
        this.themeSVGPreviews = [useRef('ThemePreview1'), useRef('ThemePreview2'), useRef('ThemePreview3')];
        const proms = [];

        onMounted(async () => {
            // Add a loading effect during the loading of the images inside the
            // svgs.
            this.uiService.block();
            this.state.themes.forEach((theme, idx) => {
                // Transform the text svg into a svg element.
                const svgEl = new DOMParser().parseFromString(theme.svg, 'image/svg+xml').documentElement;
                for (const imgEl of svgEl.querySelectorAll('image')) {
                    proms.push(new Promise((resolve, reject) => {
                        imgEl.addEventListener('load', () => {
                            resolve(imgEl);
                        }, {once: true});
                        imgEl.addEventListener('error', () => {
                            reject(imgEl);
                        }, {once: true});
                    }));
                }
                $(this.themeSVGPreviews[idx].el).append(svgEl);
            });
            // When all the images inside the svgs are loaded then remove the
            // loading effect.
            Promise.allSettled(proms).then(() => {
                this.uiService.unblock();
            });
        });
    }

    async chooseTheme(themeName) {
        await this.applyConfigurator(themeName);
    }
}

ThemeSelectionScreen.template = 'website.Configurator.ThemeSelectionScreen';

//------------------------------------------------------------------------------
// Store
//------------------------------------------------------------------------------

class Store {
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
                color5: mixCssColors(color1, '#000000', 0.75),
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
        this.themes = themes.slice(0, 3);
    }
}

function useStore() {
    const env = useEnv();
    return useState(env.store);
}

export class Configurator extends Component {
    setup() {
        this.orm = useService('orm');
        this.action = useService('action');
        this.router = useService('router');

        // Using the back button must update the router state.
        useExternalListener(window, "popstate", () => {
            const match = window.location.pathname.match(/\/website\/configurator\/(.*)$/);
            const step = parseInt(match && match[1], 10) || 1;
            // Do not use navigate because URL is already updated.
            this.state.currentStep = step;
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
            if (!store.industries) {
                await this.skipConfigurator();
            }
        });

        // This is a hack to overwrite the history state, modified by the
        // router service after executing an action. Ideally, the router
        // service would let us push a state with a new pathname.
        onMounted(() => {
            setTimeout(() => {
                this.router.cancelPushes();
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
        history.pushState({}, '', this.pathname);
    }

    navigate(step) {
        this.state.currentStep = step;
        this.updateBrowserUrl();
    }

    clearStorage() {
        window.sessionStorage.removeItem(this.storageItemName);
    }

    async getInitialState() {
        // Load values from python and iap
        var results = await this.orm.call('website', 'configurator_init');
        const r = {
            industries: results.industries,
            logo: results.logo ? 'data:image/png;base64,' + results.logo : false,
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

        const localState = JSON.parse(window.sessionStorage.getItem(this.storageItemName));
        if (localState) {
            let themes = [];
            if (localState.selectedIndustry && localState.selectedPalette) {
                themes = await this.orm.call('website', 'configurator_recommended_themes', [], {
                    'industry_id': localState.selectedIndustry.id,
                    'palette': localState.selectedPalette,
                });
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
        window.sessionStorage.setItem(this.storageItemName, newState);
    }

    async skipConfigurator() {
        await this.orm.call('website', 'configurator_skip');
        this.clearStorage();
        this.action.doAction('website.theme_install_kanban_action', {
            clearBreadcrumbs: true,
        });
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
    template: 'website.Configurator.Configurator',
});

registry.category('actions').add('website_configurator', Configurator);
