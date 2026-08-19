import { Component, onWillStart } from '@odoo/owl';
import { useService } from '@web/core/utils/hooks';

import { ROUTES, useStore } from '@website/client_actions/configurator/configurator';
import { usePagePreviews } from '@website_sale/js/client_actions/configurator/pagePreview';

export class ShopPageSelectionScreen extends Component {
    static template = 'website_sale.Configurator.ShopPageSelectionScreen';
    static props = {
        navigate: Function,
        skip: Function,
    };

    setup() {
        super.setup();
        this.orm = useService('orm');
        this.state = useStore();
        this.previews = usePagePreviews();
        onWillStart(async () => {
            this.shopPageStyles = await this.orm.call(
                'website', 'get_configurator_shop_page_styles', [], {}
            );
        });
    }

    selectStyle(option) {
        this.state.selectedShopPageStyleOption = option;
        this.props.navigate(ROUTES.productPageSelectionScreen);
    }
}
