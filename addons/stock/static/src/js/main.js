console.log('Executing picking module');

openerp.stock = function(openerp){

    console.log('Loading stock picking module');

    openerp.stock = instance.stock || {};
    openerp_picking_widgets(openerp);
    openerp.web.client_actions.add('stock.ui', 'instance.stock.PickingMainWidget');
};

    
