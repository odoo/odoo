import { patch } from '@web/core/utils/patch';

import {
    ApplyConfiguratorScreen,
    Configurator,
    FeaturesSelectionScreen,
    ROUTES,
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

patch(FeaturesSelectionScreen, {

    /**
     * @override to redirect to the shop page selection screen.
     */
    nextStep() {
        return ROUTES.shopPageSelectionScreen;
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
     * @override to include eCommerce's initial page style values.
     */
    async getInitialState() {
        const initState = await super.getInitialState(...arguments);
        initState.selectedShopPageStyleOption = undefined;
        initState.selectedProductPageStyleOption = undefined;
        return initState;
    },

})
