openerp.pos_restaurant = function(openerp){

    var module = openerp.point_of_sale;

    openerp.pos_restaurant.load_notes(openerp,module);

    openerp.pos_restaurant.load_splitbill(openerp,module);

    openerp.pos_restaurant.load_printbill(openerp,module);

    openerp.pos_restaurant.load_floors(openerp,module);

    openerp.pos_restaurant.load_multiprint(openerp,module);

};

