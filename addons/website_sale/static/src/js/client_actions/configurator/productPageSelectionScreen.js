import { onWillStart } from '@odoo/owl';
import { useService } from '@web/core/utils/hooks';

import { ApplyConfiguratorScreen, useStore } from '@website/client_actions/configurator/configurator';

export class ProductPageSelectionScreen extends ApplyConfiguratorScreen {
    static template = 'website_sale.Configurator.ProductPageSelectionScreen';
    static props = {
        navigate: Function,
        skip: Function,
        clearStorage: { type: Function, optional: true },
    };

    setup() {
        super.setup();
        this.orm = useService('orm');
        this.state = useStore();
        onWillStart(async () => {
            this.productPageStyles = await this.orm.call(
                'website', 'get_configurator_product_page_styles', [], {}
            );
        });
    }

    nextStep(option) {
        this.state.selectedProductPageStyleOption = option;
        return this.startBuilding();
    }
}
