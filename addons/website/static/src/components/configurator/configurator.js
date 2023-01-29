/** @odoo-module **/

import concurrency from 'web.concurrency';
import rpc from 'web.rpc';
import utils from 'web.utils';
import weUtils from 'web_editor.utils';
import session from 'web.session';
import {ColorpickerWidget} from 'web.Colorpicker';
import {_t, _lt} from 'web.core';
import {svgToPNG} from 'website.utils';
import {useService} from "@web/core/utils/hooks";

const {Component, Store, mount, QWeb} = owl;
const {useDispatch, useStore, useGetters, useRef} = owl.hooks;
const {Router, RouteComponent} = owl.router;
const {whenReady} = owl.utils;

const WEBSITE_TYPES = {
    1: {id: 1, label: _lt("a business website"), name: 'business'},
    2: {id: 2, label: _lt("an online store"), name: 'online_store'},
    3: {id: 3, label: _lt("a blog"), name: 'blog'},
    4: {id: 4, label: _lt("an event website"), name: 'event'},
    5: {id: 5, label: _lt("an elearning platform"), name: 'elearning'}
};

const WEBSITE_PURPOSES = {
    1: {id: 1, label: _lt("get leads"), name: 'get_leads'},
    2: {id: 2, label: _lt("develop the brand"), name: 'develop_brand'},
    3: {id: 3, label: _lt("sell more"), name: 'sell_more'},
    4: {id: 4, label: _lt("inform customers"), name: 'inform_customers'},
    5: {id: 5, label: _lt("schedule appointments"), name: 'schedule_appointments'}
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

const SESSION_STORAGE_ITEM_NAME = 'websiteConfigurator' + session.website_id;

//---------------------------------------------------------
// Components
//---------------------------------------------------------

class SkipButton extends Component {
    async skip() {
        await skipConfigurator(Component.env.services);
    }
}

SkipButton.template = 'website.Configurator.SkipButton';

class WelcomeScreen extends Component {
    constructor() {
        super(...arguments);
        this.dispatch = useDispatch();
    }

    goToDescription() {
        this.env.router.navigate({to: 'CONFIGURATOR_DESCRIPTION_SCREEN'});
    }
}

Object.assign(WelcomeScreen, {
    components: {SkipButton},
    template: 'website.Configurator.WelcomeScreen',
});

class DescriptionScreen extends Component {
    constructor() {
        super(...arguments);
        this.industrySelection = useRef('industrySelection');
        this.state = useStore((state) => state);
        this.labelToId = {};
        this.getters = useGetters();
        this.dispatch = useDispatch();
        this.autocompleteHasResults = true;
    }

    mounted() {
        this.dispatch('selectWebsitePurpose', undefined);
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
            }
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
        this.dispatch('selectIndustry', undefined, undefined);
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
        this.dispatch('selectIndustry', label, id);
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
     * Called each time the autocomplete input's value changes. Only industries containing
     * the input value are kept. Industries starting with the input value are put in first
     * position then the order is the alphabetical one. The result size is limited to 15.
     *
     * @param {Object} request object with a single 'term' property which is the input current value
     * @param {function} response callback which takes the data to suggest as argument
     */
    _autocompleteSearch(request, response) {
        const lcTerm = request.term.toLowerCase();
        const limit = 15;
        const matches = this.state.industries.filter((val) => {
            return val.label.startsWith(lcTerm);
        });
        let results = matches.slice(0, limit);
        this.labelToId = {};
        let labels = results.map((val) => val.label);
        if (labels.length < limit) {
            let relaxedMatches = this.state.industries.filter((val) => {
                return val.label.includes(lcTerm) && !labels.includes(val.label);
            });
            relaxedMatches = relaxedMatches.slice(0, limit - labels.length);
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

    selectWebsiteType(ev) {
        const {id} = ev.target.dataset;
        this.dispatch('selectWebsiteType', id);
        setTimeout(() => {
            this.industrySelection.el.focus();
        });
        this.checkDescriptionCompletion();
    }

    selectWebsitePurpose(ev) {
        const {id} = ev.target.dataset;
        this.dispatch('selectWebsitePurpose', id);
        this.checkDescriptionCompletion();
    }

    checkDescriptionCompletion() {
        const {selectedType, selectedPurpose, selectedIndustry} = this.state;
        if (selectedType && selectedPurpose && selectedIndustry) {
            this.env.router.navigate({to: 'CONFIGURATOR_PALETTE_SELECTION_SCREEN'});
        }
    }
}

Object.assign(DescriptionScreen, {
    components: {SkipButton},
    template: 'website.Configurator.DescriptionScreen',
});

class PaletteSelectionScreen extends Component {
    constructor() {
        super(...arguments);
        this.state = useStore((state) => state);
        this.getters = useGetters();
        this.dispatch = useDispatch();
        this.logoInputRef = useRef('logoSelectionInput');
        this.notification = useService("notification");
    }

    mounted() {
        if (this.state.logo) {
            this.updatePalettes();
        }
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
                route: '/web_editor/attachment/add_data',
                params: {
                    name: 'logo',
                    data: data.split(',')[1],
                    is_image: true,
                }
            });
            if (!attachment.error) {
                this.dispatch('changeLogo', data, attachment.id);
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
        const [color1, color2] = await this.rpc({
            model: 'base.document.layout',
            method: 'extract_image_primary_secondary_colors',
            args: [img],
            kwargs: {mitigate: 255},
        });
        this.dispatch('setRecommendedPalette', color1, color2);
    }

    selectPalette(paletteName) {
        this.dispatch('selectPalette', paletteName);
        this.env.router.navigate({to: 'CONFIGURATOR_FEATURES_SELECTION_SCREEN'});
    }
}

Object.assign(PaletteSelectionScreen, {
    components: {SkipButton},
    template: 'website.Configurator.PaletteSelectionScreen',
});

export class FeaturesSelectionScreen extends Component {
    constructor() {
        super(...arguments);
        this.state = useStore((state) => state);
        this.getters = useGetters();
        this.dispatch = useDispatch();
    }

    async buildWebsite() {
        const industryId = this.state.selectedIndustry && this.state.selectedIndustry.id;
        if (!industryId) {
            this.env.router.navigate({to: 'CONFIGURATOR_DESCRIPTION_SCREEN'});
            return;
        }
        const params = {
            industry_id: industryId,
            palette: this.state.selectedPalette
        };
        const themes = await this.rpc({
            model: 'website',
            method: 'configurator_recommended_themes',
            kwargs: params,
        });

        if (!themes.length) {
            await applyConfigurator(this, 'theme_default');
        } else {
            this.dispatch('updateRecommendedThemes', themes);
            this.env.router.navigate({to: 'CONFIGURATOR_THEME_SELECTION_SCREEN'});
        }
    }
}

Object.assign(FeaturesSelectionScreen, {
    components: {SkipButton},
    template: 'website.Configurator.FeatureSelection',
});

class ThemeSelectionScreen extends Component {
    constructor() {
        super(...arguments);
        this.state = useStore((state) => state);
        this.getters = useGetters();
        this.themeSVGPreviews = [useRef('ThemePreview1'), useRef('ThemePreview2'), useRef('ThemePreview3')];
    }

    mounted() {
        this.state.themes.forEach((theme, idx) => {
            $(this.themeSVGPreviews[idx].el).append(theme.svg);
        });
    }

    async chooseTheme(themeName) {
        await applyConfigurator(this, themeName);
    }
}

ThemeSelectionScreen.template = 'website.Configurator.ThemeSelectionScreen';

class App extends Component {}

Object.assign(App, {
    components: {RouteComponent},
    template: 'website.Configurator.App',
});

//---------------------------------------------------------
// Routes
//---------------------------------------------------------

const ROUTES = [
    {name: 'CONFIGURATOR_WELCOME_SCREEN', path: '/website/configurator', component: WelcomeScreen},
    {name: 'CONFIGURATOR_WELCOME_SCREEN_FALLBACK', path: '/website/configurator/1', component: WelcomeScreen},
    {name: 'CONFIGURATOR_DESCRIPTION_SCREEN', path: '/website/configurator/2', component: DescriptionScreen},
    {name: 'CONFIGURATOR_PALETTE_SELECTION_SCREEN', path: '/website/configurator/3', component: PaletteSelectionScreen},
    {name: 'CONFIGURATOR_FEATURES_SELECTION_SCREEN', path: '/website/configurator/4', component: FeaturesSelectionScreen},
    {name: 'CONFIGURATOR_THEME_SELECTION_SCREEN', path: '/website/configurator/5', component: ThemeSelectionScreen},
];

//---------------------------------------------------------
// Store
//---------------------------------------------------------

const getters = {
    getWebsiteTypes() {
        return Object.values(WEBSITE_TYPES);
    },

    getSelectedType(_, id) {
        return id ? WEBSITE_TYPES[id] : undefined;
    },

    getWebsitePurpose() {
        return Object.values(WEBSITE_PURPOSES);
    },

    getSelectedPurpose(_, id) {
        return id ? WEBSITE_PURPOSES[id] : undefined;
    },

    getFeatures({state}) {
        return Object.values(state.features);
    },

    getPalettes({state}) {
        return Object.values(state.palettes);
    },

    getThemeName({state}, idx) {
        return state.themes.length > idx ? state.themes[idx].name : undefined;
    },
    /**
     * @param {Object} obj
     * @param {string|undefined} [obj.state]
     * @returns {string|false}
     */
    getSelectedPaletteName({state}) {
        const palette = state.selectedPalette;
        return palette ? (palette.name || 'recommendedPalette') : false;
    },
};

const actions = {
    selectWebsiteType({state}, id) {
        Object.values(state.features).filter((feature) => feature.module_state !== 'installed').forEach((feature) => {
            feature.selected = feature.website_config_preselection.includes(WEBSITE_TYPES[id].name);
        });
        state.selectedType = id;
    },
    selectWebsitePurpose({state}, id) {
        // Keep track or the former selection in order to be able to keep
        // the auto-advance navigation scheme while being able to use the
        // browser's back and forward buttons.
        if (!id && state.selectedPurpose) {
            state.formerSelectedPurpose = state.selectedPurpose;
        }
        Object.values(state.features).filter((feature) => feature.module_state !== 'installed').forEach((feature) => {
            // need to check id, since we set to undefined in mount() to avoid the auto next screen on back button
            feature.selected |= id && feature.website_config_preselection.includes(WEBSITE_PURPOSES[id].name);
        });
        state.selectedPurpose = id;
    },
    selectIndustry({state}, label, id) {
        if (!label || !id) {
            state.selectedIndustry = undefined;
        } else {
            state.selectedIndustry = {id, label};
        }
    },
    changeLogo({state}, data, attachmentId) {
        state.logo = data;
        state.logoAttachmentId = attachmentId;
    },
    selectPalette({state}, paletteName) {
        if (paletteName === 'recommendedPalette') {
            state.selectedPalette = state.recommendedPalette;
        } else {
            state.selectedPalette = state.palettes[paletteName];
        }
    },
    toggleFeature({state}, featureId) {
        const feature = state.features[featureId];
        const isModuleInstalled = feature.module_state === 'installed';
        feature.selected = !feature.selected || isModuleInstalled;
    },
    setRecommendedPalette({state}, color1, color2) {
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
                recommendedPalette[attr] = recommendedPalette[state.defaultColors[attr]];
            });
            state.recommendedPalette = recommendedPalette;
        } else {
            state.recommendedPalette = undefined;
        }
    },
    updateRecommendedThemes({state}, themes) {
        state.themes = themes.slice(0, 3);
    }
};

async function getInitialState(services) {

    // Load values from python and iap
    var results = await services.rpc({
        model: 'website',
        method: 'configurator_init',
    });
    const r = {
        industries: results.industries,
        logo: results.logo ? 'data:image/png;base64,' + results.logo : false,
    };

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

    const localState = JSON.parse(window.sessionStorage.getItem(SESSION_STORAGE_ITEM_NAME));
    if (localState) {
        let themes = [];
        if (localState.selectedIndustry && localState.selectedPalette) {
            const params = {
                industry_id: localState.selectedIndustry.id,
                palette: localState.selectedPalette
            };
            themes = await services.rpc({
                model: 'website',
                method: 'configurator_recommended_themes',
                kwargs: params,
            });
        }
        return Object.assign(r, {...localState, palettes, themes});
    }

    const features = {};
    results.features.forEach(feature => {
        features[feature.id] = Object.assign({}, feature, {selected: feature.module_state === 'installed'});
        const wtp = features[feature.id].website_config_preselection;
        features[feature.id].website_config_preselection = wtp ? wtp.split(',') : [];
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

async function skipConfigurator(services) {
    await services.rpc({
        model: 'website',
        method: 'configurator_skip',
    });
    window.sessionStorage.removeItem(SESSION_STORAGE_ITEM_NAME);
    window.location = '/web#action=website.theme_install_kanban_action';
}

async function applyConfigurator(self, themeName) {
    if (!self.state.selectedIndustry) {
        self.env.router.navigate({to: 'CONFIGURATOR_DESCRIPTION_SCREEN'});
        return;
    }
    if (!self.state.selectedPalette) {
        self.env.router.navigate({to: 'CONFIGURATOR_PALETTE_SELECTION_SCREEN'});
        return;
    }

    async function attemptConfiguratorApply(data, retryCount = 0) {
        try {
            return await self.rpc({
                model: 'website',
                method: 'configurator_apply',
                kwargs: data,
            });
        } catch (error) {
            // Wait a bit before retrying or allowing manual retry.
            await concurrency.delay(5000);
            if (retryCount < 3) {
                return attemptConfiguratorApply(data, retryCount + 1);
            }
            document.querySelector('.o_theme_install_loader_container').remove();
            throw error;
        }
    }

    if (themeName !== undefined) {
        $('body').append(self.env.loader);
        const selectedFeatures = Object.values(self.state.features).filter((feature) => feature.selected).map((feature) => feature.id);
        let selectedPalette = self.state.selectedPalette.name;
        if (!selectedPalette) {
            selectedPalette = [
                self.state.selectedPalette.color1,
                self.state.selectedPalette.color2,
                self.state.selectedPalette.color3,
                self.state.selectedPalette.color4,
                self.state.selectedPalette.color5,
            ];
        }
        const data = {
            selected_features: selectedFeatures,
            industry_id: self.state.selectedIndustry.id,
            selected_palette: selectedPalette,
            theme_name: themeName,
            website_purpose: WEBSITE_PURPOSES[
                self.state.selectedPurpose || self.state.formerSelectedPurpose
            ].name,
            website_type: WEBSITE_TYPES[self.state.selectedType].name,
            logo_attachment_id: self.state.logoAttachmentId,
        };
        const resp = await attemptConfiguratorApply(data);
        window.sessionStorage.removeItem(SESSION_STORAGE_ITEM_NAME);
        window.location = resp.url;
    }
}

async function makeEnvironment() {
    const env = {};
    const router = new Router(env, ROUTES);
    await router.start();
    const services = Component.env.services;
    const state = await getInitialState(services);
    const store = new Store({state, actions, getters});
    store.on("update", null, () => {
        const newState = {
            selectedType: store.state.selectedType,
            selectedPurpose: store.state.selectedPurpose,
            formerSelectedPurpose: store.state.formerSelectedPurpose,
            selectedIndustry: store.state.selectedIndustry,
            selectedPalette: store.state.selectedPalette,
            recommendedPalette: store.state.recommendedPalette,
            defaultColors: store.state.defaultColors,
            features: store.state.features,
            logo: store.state.logo,
            logoAttachmentId: store.state.logoAttachmentId,
        };
        window.sessionStorage.setItem(SESSION_STORAGE_ITEM_NAME, JSON.stringify(newState));
    });
    await session.is_bound;
    const qweb = new QWeb({translateFn: _t});
    const loaderTemplate = await owl.utils.loadFile('/website/static/src/xml/theme_preview.xml');
    const configuratorTemplates = await owl.utils.loadFile('/website/static/src/components/configurator/configurator.xml');
    qweb.addTemplates(loaderTemplate);
    qweb.addTemplates(configuratorTemplates);

    env.loader = qweb.renderToString('website.ThemePreview.Loader', {
        showTips: true
    });
    return Object.assign(env, {router, store, qweb, services});
}

async function setup() {
    const env = await makeEnvironment();
    if (!env.store.state.industries) {
        await skipConfigurator(env.services);
    } else {
        mount(App, {target: document.body, env});
    }
}

whenReady(setup);
