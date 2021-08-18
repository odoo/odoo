odoo.define('flexipharmacy.MaterialList', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useState} = owl.hooks;
    
    class MaterialList extends PosComponent {}
    MaterialList.template = 'MaterialList';

    Registries.Component.add(MaterialList);

    return MaterialList;
});
