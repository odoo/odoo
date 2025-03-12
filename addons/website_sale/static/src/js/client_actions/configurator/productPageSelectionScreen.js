import { Component, onWillStart } from '@odoo/owl';
import { useService } from '@web/core/utils/hooks';

import { ROUTES, useStore } from '@website/client_actions/configurator/configurator';

export class ProductPageSelectionScreen extends Component {
    static template = 'website_sale.Configurator.ProductPageSelectionScreen';
    static props = {
        navigate: Function,
        skip: Function,
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

    selectStyle(option) {
        this.state.selectedProductPageStyleOption = option;
        this.props.navigate(ROUTES.themeSelectionScreen);
    }
}
