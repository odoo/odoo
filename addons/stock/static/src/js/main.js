console.log('Executing picking module');

openerp.stock = function(instance){

    console.log('Loading stock picking module');

    instance.stock = instance.stock || {};

    openerp_picking_widgets(instance);

    instance.web.client_actions.add('stock.ui', 'instance.stock.PickingMainWidget');
};

    
