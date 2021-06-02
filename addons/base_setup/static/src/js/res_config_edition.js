odoo.define('base_setup.ResConfigEdition', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var widget_registry = require('web.widget_registry');
    var session = require ('web.session');

    var ResConfigEdition = Widget.extend({
        template: 'res_config_edition',

       /**
        * @override
        */
        init: function () {
            this._super.apply(this, arguments);
            this.server_version = session.server_version;
            this.expiration_date = session.expiration_date
                ? moment(session.expiration_date)
                : moment().add(30, 'd');
        },
   });

   widget_registry.add('res_config_edition', ResConfigEdition);

    return ResConfigEdition;
});
