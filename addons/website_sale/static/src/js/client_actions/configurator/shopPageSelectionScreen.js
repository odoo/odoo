import { Component, onWillStart, t, useProps } from '@odoo/owl';
import { useService } from '@web/core/utils/hooks';

import { ROUTES, useStore } from '@website/client_actions/configurator/configurator';

export class ShopPageSelectionScreen extends Component {
    static template = 'website_sale.Configurator.ShopPageSelectionScreen';
    props = useProps({
        navigate: t.function(),
        skip: t.function(),
    });

    setup() {
        super.setup();
        this.orm = useService('orm');
        this.state = useStore();
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
