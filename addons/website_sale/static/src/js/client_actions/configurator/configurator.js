import { patch } from '@web/core/utils/patch';
import {
    ApplyConfiguratorScreen,
    Configurator,
    FeaturesSelectionScreen,
    ROUTES,
} from '@website/client_actions/configurator/configurator';
import {
    ShopPageSelectionScreen,
} from '@website_sale/js/client_actions/configurator/shopPageSelectionScreen';
import {
    ProductPageSelectionScreen,
} from '@website_sale/js/client_actions/configurator/productPageSelectionScreen';

ROUTES['shopPageSelectionScreen'] = 50;
ROUTES['productPageSelectionScreen'] = 51;

patch(ApplyConfiguratorScreen.prototype, {

    /**
     * @override to include shop and product page style configuration.
     */
    getConfigurationData(selectedFeatures, selectedPalette, themeName) {
        let data = super.getConfigurationData(...arguments);
        return Object.assign(data, {
            'shop_page_style_id': this.state.selectedShopPageStyleId,
            'product_page_style_id': this.state.selectedProductPageStyleId,
        });
    }
})

patch(FeaturesSelectionScreen.prototype, {

    /**
     * @override to redirect to shop page selection.
     */
    nextStep() {
        return ROUTES.shopPageSelectionScreen;
    }
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
     * @override to include shop and product components.
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
     * @override to include shop and product page style values.
     */
    async getInitialState() {
        const initState = await super.getInitialState(...arguments);
        initState.shopPageStyles = [];
        initState.productPageStyles = [];
        initState.selectedShopPageStyleId = undefined;
        initState.selectedProductPageStyleId = undefined;
        return initState;
    }
})
