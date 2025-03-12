import { Component, onWillStart } from '@odoo/owl';
import { ROUTES, useStore } from '@website/client_actions/configurator/configurator';
import { useService } from '@web/core/utils/hooks';

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
            this.state.productPageStyles = await this.orm.call(
                'website', 'get_configurator_product_page_styles', [], {}
            );
        });
    }

    selectStyle(id) {
        this.state.selectedProductPageStyleId = id;
        this.props.navigate(ROUTES.themeSelectionScreen);
    }
}
