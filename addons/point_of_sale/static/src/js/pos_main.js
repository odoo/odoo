
openerp.point_of_sale = function(instance) {

    instance.point_of_sale = {};

    var module = instance.point_of_sale;

    openerp_pos_models(module,instance);    // import pos_models.js
    
    openerp_pos_widgets(module,instance);   // import pos_widgets.js

    openerp_pos_devices(module,instance);   // import pos_devices.js

    instance.web.client_actions.add('pos.ui', 'instance.point_of_sale.POSWidget');
};

    
