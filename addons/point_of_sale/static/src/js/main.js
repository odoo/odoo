
openerp.point_of_sale = function(openerp) {
    "use strict";

    var module = openerp.point_of_sale;

    openerp.point_of_sale.load_db(openerp,module);

    openerp.point_of_sale.load_models(openerp,module);

    openerp.point_of_sale.load_basewidget(openerp,module);

    openerp.point_of_sale.load_keyboard(openerp,module);

    openerp.point_of_sale.load_gui(openerp,module);

    openerp.point_of_sale.load_popups(openerp,module);

    openerp.point_of_sale.load_screens(openerp,module);

    openerp.point_of_sale.load_devices(openerp,module);

    openerp.point_of_sale.load_chrome(openerp,module);

    openerp.web.client_actions.add('pos.ui', 'openerp.point_of_sale.Chrome');
};

