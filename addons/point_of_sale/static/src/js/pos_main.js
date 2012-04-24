
openerp.point_of_sale = function(instance) {

    instance.point_of_sale = {};

    var module = instance.point_of_sale;

    pos_models(module,instance);    // import pos_models.js
    
    pos_widgets(module,instance);   // import pos_widgets.js

    instance.web.client_actions.add('pos.ui', 'instance.point_of_sale.POSWidget');
};

    
