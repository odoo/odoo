
openerp.point_of_sale = function(openerp) {
    "use strict";

    var module = openerp.point_of_sale;

    openerp.point_of_sale.load_db(openerp,module);         // import db.js

    openerp.point_of_sale.load_models(openerp,module);     // import pos_models.js

    openerp.point_of_sale.load_basewidget(openerp,module); // import pos_basewidget.js

    openerp.point_of_sale.load_keyboard(openerp,module);   // import  pos_keyboard_widget.js

    openerp.point_of_sale.load_screens(openerp,module);    // import pos_screens.js

    openerp.point_of_sale.load_devices(openerp,module);    // import pos_devices.js

    openerp.point_of_sale.load_widgets(openerp,module);    // import pos_widgets.js

    openerp.web.client_actions.add('pos.ui', 'openerp.point_of_sale.PosWidget');
};

    
