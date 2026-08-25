import { onWillStart } from '@odoo/owl';
import { useService } from '@web/core/utils/hooks';

import {
    ApplyConfiguratorScreen,
    ROUTES,
    useStore,
} from '@website/client_actions/configurator/configurator';
import { usePagePreviews } from '@website_sale/js/client_actions/configurator/pagePreview';

export class ProductPageSelectionScreen extends ApplyConfiguratorScreen {
    static template = 'website_sale.Configurator.ProductPageSelectionScreen';
    static props = {
        navigate: Function,
        skip: Function,
        clearStorage: Function,
    };

    setup() {
        super.setup();
        this.orm = useService('orm');
        this.state = useStore();
        this.previews = usePagePreviews();
        onWillStart(async () => {
            this.productPageStyles = await this.orm.call(
                'website', 'get_configurator_product_page_styles', [], {}
            );
        });
    }

    async selectStyle(option) {
        this.state.selectedProductPageStyleOption = option;
        if (!this.state.selectedThemeName) {
            this.props.navigate(ROUTES.themeSelectionScreen);
            return;
        }
        await this.applyConfigurator(this.state.selectedThemeName);
    }
}
