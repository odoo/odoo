/*
    © 2017-2018 Savoir-faire Linux <https://savoirfairelinux.com>
    License LGPL-3.0 or later (http://www.gnu.org/licenses/LGPL.html).
*/
odoo.define('disable_quick_create', function(require) {
    "use strict";

    var relational_fields = require('web.relational_fields');
    var rpc = require('web.rpc');

    var model_deferred = $.Deferred();
    var models = [];

    rpc.query({
        model: "ir.model",
        method: "search_read",
        args:[
            [['disable_create_edit','=', true]],
            ['model'],
        ],
    }).then(function(result) {
        result.forEach(function(el){
            models.push(el.model);
        })
        model_deferred.resolve();
    });

    relational_fields.FieldMany2One.include({
        init: function() {
            this._super.apply(this, arguments);

            this.nodeOptions.no_quick_create = true;

            if (models.includes(this.field.relation)){
                this.nodeOptions.no_create_edit = true;
            }
        },
    });
});
