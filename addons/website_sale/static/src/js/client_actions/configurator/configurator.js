import { patch } from '@web/core/utils/patch';

import {
    ApplyConfiguratorScreen,
    Configurator,
    ROUTES,
    ThemeSelectionScreen,
} from '@website/client_actions/configurator/configurator';
import {
    ProductPageSelectionScreen,
} from '@website_sale/js/client_actions/configurator/productPageSelectionScreen';
import {
    ShopPageSelectionScreen,
} from '@website_sale/js/client_actions/configurator/shopPageSelectionScreen';

ROUTES.shopPageSelectionScreen = 50;
ROUTES.productPageSelectionScreen = 55;

patch(ApplyConfiguratorScreen.prototype, {

    /**
     * @override to include eCommerce pages style configuration.
     */
    getConfigurationData() {
        const data = super.getConfigurationData(...arguments);
        return Object.assign(data, {
            'shop_page_style_option': this.state.selectedShopPageStyleOption,
            'product_page_style_option': this.state.selectedProductPageStyleOption,
        });
    },

})

patch(ThemeSelectionScreen.prototype, {
    async chooseTheme(themeName) {
        this.state.selectedThemeName = themeName;
        this.props.navigate(ROUTES.shopPageSelectionScreen);
    },
});

patch(Configurator, {

    components: {
        ...Configurator.components,
        ShopPageSelectionScreen,
        ProductPageSelectionScreen,
    },

})

patch(Configurator.prototype, {

    /**
     * @override to include eCommerce's selection screen components.
     */
    get currentComponent() {
        if (this.state.currentStep === ROUTES.shopPageSelectionScreen) {
            return ShopPageSelectionScreen;
        }
        if (this.state.currentStep === ROUTES.productPageSelectionScreen) {
            return ProductPageSelectionScreen;
        }
        return super.currentComponent;
    },

    /**
     * @override to allow the product page selection screen to apply the configurator.
     */
    get componentProps() {
        const props = super.componentProps;
        if (this.state.currentStep === ROUTES.productPageSelectionScreen) {
            props.clearStorage = this.clearStorage.bind(this);
        }
        return props;
    },

    /**
     * @override to include eCommerce's initial page style values.
     */
    async getInitialState() {
        const initState = await super.getInitialState(...arguments);
        initState.selectedThemeName = undefined;
        initState.selectedShopPageStyleOption = undefined;
        initState.selectedProductPageStyleOption = undefined;
        return initState;
    },

})
