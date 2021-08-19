    odoo.define('flexipharmacy.MaterialMonitorScreen', function(require) {
    'use strict';

    const { debounce } = owl.utils;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');
    var rpc = require('web.rpc');
    var core = require('web.core');
    const { useState } = owl.hooks;
    const { useRef } = owl.hooks;
    var _t = core._t;

    class MaterialMonitorScreen extends PosComponent {
        constructor() {
            super(...arguments);
            this.searchWordInput = useRef('search-word-input');
            this.updateSearch = debounce(this.updateSearch, 100);
            this.state = useState({ location_id: this.env.pos.get_order().get_product_location()});
        }
        close() {
            this.trigger('clear-search');
            this.showScreen('ProductScreen');
        }
        get LocationName(){
            if(this.state.location_id){
                return this.state.location_id.name
            }else{
                return 'Location'
            }
        }
 
        async SelectLocation(){
            const selectionLocation = this.env.pos.stock_location.map(location_id => ({
                id: location_id.id,
                label: location_id.name,
                isSelected: location_id.id === this.state.location_id.id,
                item: location_id,
            }));

            const { confirmed, payload: selectedLocation } = await this.showPopup(
                'SelectionPopup',
                {
                    title: this.env._t('Select the Location'),
                    list: selectionLocation,
                }
            );

            if (confirmed) {
                this.env.pos.get_order().set_product_location(selectedLocation)
                this.state.location_id = this.env.pos.get_order().get_product_location()
                this.env.pos.get_order().material_monitor_data();
            }
        }
    }
    MaterialMonitorScreen.template = 'MaterialMonitorScreen';

    Registries.Component.add(MaterialMonitorScreen);

    return MaterialMonitorScreen;
});
