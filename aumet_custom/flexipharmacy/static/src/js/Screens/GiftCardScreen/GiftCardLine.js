    odoo.define('point_of_sale.GiftCardLine', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useState } = owl.hooks;

    class GiftCardLine extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({card_no:this.props.gift_card.card_no})
        }
        get highlight() {
            if (this.props.selectedCard && this.props.selectedCard.id === this.props.gift_card.id) {
                return 'highlight'
            }else{
                return ''
            }
        }
    }
    GiftCardLine.template = 'GiftCardLine';

    Registries.Component.add(GiftCardLine);

    return GiftCardLine;
});
