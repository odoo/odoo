/** @odoo-module **/

import rpc from 'web.rpc';
import utils from 'web.utils';
import weUtils from 'web_editor.utils';
import session from 'web.session';
import {ColorpickerWidget} from 'web.Colorpicker';
import {_t, _lt} from 'web.core';

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
    'avantgarde-2',
    'bistro-6',
    'bookstore-4',
    'generic-4',
    'bookstore-5',
    'beauty-3',
    'cobalt-1',
    'odoo-experts-2',
    'artists-4',
    'bewise-1',
    'generic-16',
    'generic-12',
    'clean-2',
    'generic-8',
    'vehicle-1',
    'anelusia-4',
    'nano-2',
    'notes-3',
    'graphene-2',
    'enark-4',
];

const SESSION_STORAGE_ITEM_NAME = 'websiteConfigurator' + session.website_id;

//---------------------------------------------------------
// Components
//---------------------------------------------------------

class SkipButton extends Component {
    async skip() {
        await skipConfigurator();
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
    }

    mounted() {
        this.dispatch('selectWebsitePurpose', undefined);
        $(this.industrySelection.el).autocomplete({
            appendTo: '.o_configurator_industry_wrapper',
            delay: 400,
            minLength: 1,
            source: this.autocompleteSearch.bind(this),
            select: this.selectIndustry.bind(this),
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

    autocompleteSearch(request, response) {
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
            labels = results.map((val) => val.label);
        }
        results.forEach((r) => {
            this.labelToId[r.label] = r.id;
        });
        response(labels);
    }

    selectIndustry(_, ui) {
        this.industrySelection.el.parentNode.dataset.value = ui.item.label;
        this.dispatch('selectIndustry', ui.item.label, this.labelToId[ui.item.label]);
        this.checkDescriptionCompletion();
    }

    blurIndustrySelection(ev) {
        const id = this.labelToId[ev.target.value];
        this.dispatch('selectIndustry', ev.target.value, id);
        if (id === undefined) {
            this.industrySelection.el.value = '';
            this.industrySelection.el.parentNode.dataset.value = '';
        } else {
            this.checkDescriptionCompletion();
        }
    }

    inputIndustrySelection(ev) {
        this.industrySelection.el.parentNode.dataset.value = ev.target.value;
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
            this.dispatch('changeLogo', data);
            this.updatePalettes();
        }
    }

    async updatePalettes() {
        let img = this.state.logo.split(',', 2)[1];
        const [color1, color2] = await rpc.query({
            model: 'base.document.layout',
            method: 'extract_image_primary_secondary_colors',
            args: [img]
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

class FeaturesSelectionScreen extends Component {
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
        const themes = await rpc.query({
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
            feature.selected = feature.website_types_preselection.includes(WEBSITE_TYPES[id].name);
        });
        state.selectedType = id;
    },
    selectWebsitePurpose({state}, id) {
        Object.values(state.features).filter((feature) => feature.module_state !== 'installed').forEach((feature) => {
            // need to check id, since we set to undefined in mount() to avoid the auto next screen on back button
            feature.selected |= id && feature.website_types_preselection.includes(WEBSITE_PURPOSES[id].name);
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
    changeLogo({state}, data) {
        state.logo = data;
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
            state.recommendedPalette = {
                color1: color1,
                color2: color2,
                color3: ColorpickerWidget.mixCssColors('#FFFFFF', color2, 0.9),
                color4: '#FFFFFF',
                color5: ColorpickerWidget.mixCssColors(color1, '#000000', 0.75),
            };
        } else {
            state.recommendedPalette = undefined;
        }
    },
    updateRecommendedThemes({state}, themes) {
        state.themes = themes.slice(0, 3);
    }
};

async function getInitialState() {

    // Load values from python and iap
    var results = await rpc.query({
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
            const color = weUtils.getCSSVariableValue(`o-palette-${paletteName}-o-color-${j}`, style);
            palette[`color${j}`] = color;
        }
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
            themes = await rpc.query({
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
        const wtp = features[feature.id].website_types_preselection;
        features[feature.id].website_types_preselection = wtp ? wtp.split(',') : [];
    });

    return Object.assign(r, {
        selectedType: undefined,
        selectedPurpose: undefined,
        selectedIndustry: undefined,
        selectedPalette: undefined,
        recommendedPalette: undefined,
        palettes: palettes,
        features: features,
        themes: [],
    });
}

async function skipConfigurator() {
    await rpc.query({
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
            logo: self.state.logo,
            industry_id: self.state.selectedIndustry.id,
            selected_palette: selectedPalette,
            theme_name: themeName,
            website_purpose: WEBSITE_PURPOSES[self.state.selectedPurpose].name,
            website_type: WEBSITE_TYPES[self.state.selectedType].name,
        };
        const resp = await rpc.query({
            model: 'website',
            method: 'configurator_apply',
            kwargs: {...data},
        });
        window.sessionStorage.removeItem(SESSION_STORAGE_ITEM_NAME);
        window.location = resp.url;
    }
}

async function makeEnvironment() {
    const env = {};
    const router = new Router(env, ROUTES);
    await router.start();
    const state = await getInitialState();
    const store = new Store({state, actions, getters});
    store.on("update", null, () => {
        const newState = {
            selectedType: store.state.selectedType,
            selectedPurpose: store.state.selectedPurpose,
            selectedIndustry: store.state.selectedIndustry,
            selectedPalette: store.state.selectedPalette,
            recommendedPalette: store.state.recommendedPalette,
            features: store.state.features,
            logo: store.state.logo,
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
    return Object.assign(env, {router, store, qweb});
}

async function setup() {
    const env = await makeEnvironment();
    if (!env.store.state.industries) {
        await skipConfigurator();
    } else {
        mount(App, {target: document.body, env});
    }
}

whenReady(setup);
