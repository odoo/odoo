/** @odoo-module **/

import concurrency from 'web.concurrency';
import utils from 'web.utils';
import weUtils from 'web_editor.utils';
import {ColorpickerWidget} from 'web.Colorpicker';
import {_t, _lt} from 'web.core';
import {svgToPNG} from 'website.utils';
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

const { Component, onMounted, reactive, useEnv, useRef, useState, useSubEnv, onWillStart, useExternalListener } = owl;

const ROUTES = {
    descriptionScreen: 2,
    paletteSelectionScreen: 3,
    featuresSelectionScreen: 4,
    themeSelectionScreen: 5,
};

const WEBSITE_TYPES = {
    1: {id: 1, label: _lt("a business website"), name: 'business'},
    2: {id: 2, label: _lt("an online store"), name: 'online_store'},
    3: {id: 3, label: _lt("a blog"), name: 'blog'},
    4: {id: 4, label: _lt("an event website"), name: 'event'},
    5: {id: 5, label: _lt("an elearning platform"), name: 'elearning'},
};

const WEBSITE_PURPOSES = {
    1: {id: 1, label: _lt("get leads"), name: 'get_leads'},
    2: {id: 2, label: _lt("develop the brand"), name: 'develop_brand'},
    3: {id: 3, label: _lt("sell more"), name: 'sell_more'},
    4: {id: 4, label: _lt("inform customers"), name: 'inform_customers'},
    5: {id: 5, label: _lt("schedule appointments"), name: 'schedule_appointments'},
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

class DescriptionScreen extends Component {
    setup() {
        this.industrySelection = useRef('industrySelection');
        this.state = useStore();
        this.labelToId = {};
        this.autocompleteHasResults = true;

        onMounted(() => this.onMounted());
    }

    onMounted() {
        this.selectWebsitePurpose();
        $(this.industrySelection.el).autocomplete({
            appendTo: '.o_configurator_industry_wrapper',
            delay: 400,
            minLength: 1,
            source: this._autocompleteSearch.bind(this),
            select: this._selectIndustry.bind(this),
            open: this._customizeNoResultMenuStyle.bind(this),
            focus: this._disableKeyboardNav.bind(this),
            classes: {
                'ui-autocomplete': 'custom-ui-autocomplete shadow-lg border-0 o_configurator_show_fast',
            },
        });
        if (this.state.selectedIndustry) {
            this.industrySelection.el.value = this.state.selectedIndustry.label;
            this.industrySelection.el.parentNode.dataset.value = this.state.selectedIndustry.label;
            this.labelToId[this.state.selectedIndustry.label] = this.state.selectedIndustry.id;
        }
    }

    /**
     * Clear the input and its parent label and set the selected industry to undefined.
     *
     * @private
     */
    _clearIndustrySelection() {
        this.industrySelection.el.value = '';
        this.industrySelection.el.parentNode.dataset.value = '';
        this.state.selectIndustry();
    }

    /**
     * Set the input's parent label value to automatically adapt input size
     * and update the selected industry.
     *
     * @private
     * @param {String} label an industry label
     */
    _setSelectedIndustry(label) {
        this.industrySelection.el.parentNode.dataset.value = label;
        const id = this.labelToId[label];
        this.state.selectIndustry(label, id);
        this.checkDescriptionCompletion();
    }

    /**
     * Called each time the suggestion menu is opened or updated. If there are no
     * results to display the style of the "No result found" message is customized.
     *
     * @private
     */
    _customizeNoResultMenuStyle() {
        if (!this.autocompleteHasResults) {
            const noResultLinkEl = this.industrySelection.el.parentElement.getElementsByTagName('a')[0];
            noResultLinkEl.classList.add('o_no_result');
        }
    }

    /**
     * Disables keyboard navigation when there are no results to avoid selecting the
     * "No result found" message by pressing the down arrow key.
     *
     * @private
     * @param {Event} ev
     */
    _disableKeyboardNav(ev) {
        if (!this.autocompleteHasResults) {
            ev.preventDefault();
        }
    }

    /**
     * Called each time the autocomplete input's value changes. Only industries
     * having a label or a synonym containing all terms of the input value are
     * kept.
     * The order received from IAP is kept (expected to be on descending hit
     * count) unless there are 7 or less matches in which case the results are
     * sorted alphabetically.
     * The result size is limited to 15.
     *
     * @param {Object} request object with a single 'term' property which is the
     *      input current value
     * @param {function} response callback which takes the data to suggest as
     *      argument
     */
    _autocompleteSearch(request, response) {
        const terms = request.term.toLowerCase().split(/[|,\n]+/);
        const limit = 15;
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
            // "restaurant" remains available even if there are 15 specific
            // sub-types that have a higher hit count.
            matches = matches.sort((x, y) => x.wordCount - y.wordCount)
                             .slice(0, limit)
                             .sort((x, y) => x.hitCountOrder - y.hitCountOrder);
        }
        this.labelToId = {};
        let labels;
        this.autocompleteHasResults = !!matches.length;
        if (this.autocompleteHasResults) {
            if (matches.length <= sortLimit) {
                // Sort results by ascending label if few of them.
                matches.sort((x, y) => x.label < y.label ? -1 : x.label > y.label ? 1 : 0);
            }
            labels = matches.map(val => val.label);
            matches.forEach(r => {
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
     * @private
     * @param {Event} ev
     * @param {Object} ui an object with label and value properties for
     *      the selected option.
     */
    _selectIndustry(ev, ui) {
        if (this.autocompleteHasResults) {
            this._setSelectedIndustry(ui.item.label);
        } else {
            this._clearIndustrySelection();
            ev.preventDefault();
        }
    }

    /**
     * Called on industrySelection input blur. Updates the selected industry or
     * clears the input if its current value is not a valid industry.
     *
     * @private
     * @param {Event} ev
     */
    _blurIndustrySelection(ev) {
        if (this.labelToId[ev.target.value] !== undefined) {
            this._setSelectedIndustry(ev.target.value);
        } else {
            this._clearIndustrySelection();
        }
    }

    selectWebsiteType(id) {
        this.state.selectWebsiteType(id);
        setTimeout(() => {
            this.industrySelection.el.focus();
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
            this.props.navigate(ROUTES.paletteSelectionScreen);
        }
    }
}

Object.assign(DescriptionScreen, {
    components: {SkipButton},
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

    async changeLogo() {
        const logoSelectInput = this.logoInputRef.el;
        if (logoSelectInput.files.length === 1) {
            const file = logoSelectInput.files[0];
            const data = await utils.getDataURLFromFile(file);
            const attachment = await this.rpc('/web_editor/attachment/add_data', {
                'name': 'logo',
                'data': data.split(',')[1],
                'is_image': true,
            });
            if (!attachment.error) {
                this.state.changeLogo(data, attachment.id);
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
        let img = this.state.logo;
        if (img.startsWith('data:image/svg+xml')) {
            img = await svgToPNG(img);
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
                await concurrency.delay(5000);
                if (retryCount < 3) {
                    return attemptConfiguratorApply(data, retryCount + 1);
                }
                document.querySelector('.o_website_loader_container').remove();
                throw error;
            }
        };

        if (themeName !== undefined) {
            this.websiteService.showLoader({ showTips: true });
            const selectedFeatures = Object.values(this.state.features).filter((feature) => feature.selected).map((feature) => feature.id);
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

            // Here the website service goToWebsite method is not used because
            // the web client needs to be reloaded after the new modules have
            // been installed.
            window.location.replace(`/web#action=website.website_preview&website_id=${resp.website_id}&enable_editor=1&with_loader=1`);
        }
    }
}

class FeaturesSelectionScreen extends ApplyConfiguratorScreen {
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

        this.orm = useService('orm');
        this.state = useStore();
        this.themeSVGPreviews = [useRef('ThemePreview1'), useRef('ThemePreview2'), useRef('ThemePreview3')];

        onMounted(() => {
            this.state.themes.forEach((theme, idx) => {
                $(this.themeSVGPreviews[idx].el).append(theme.svg);
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
                color2 = ColorpickerWidget.mixCssColors('#FFFFFF', color1, 0.2);
            }
            const recommendedPalette = {
                color1: color1,
                color2: color2,
                color3: ColorpickerWidget.mixCssColors('#FFFFFF', color2, 0.9),
                color4: '#FFFFFF',
                color5: ColorpickerWidget.mixCssColors(color1, '#000000', 0.75),
            };
            CUSTOM_BG_COLOR_ATTRS.forEach((attr) => {
                recommendedPalette[attr] = recommendedPalette[this.defaultColors[attr]];
            });
            this.recommendedPalette = recommendedPalette;
        } else {
            this.recommendedPalette = undefined;
        }
    }

    updateRecommendedThemes(themes) {
        this.themes = themes.slice(0, 3);
    }
}

function useStore() {
    const env = useEnv();
    return useState(env.store);
}

class Configurator extends Component {
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
        return `/website/configurator${this.state.currentStep ? `/${this.state.currentStep}` : ''}`;
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
