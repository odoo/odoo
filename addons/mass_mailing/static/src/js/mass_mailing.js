odoo.define('mass_mailing.mass_mailing', function (require) {
"use strict";

var KanbanColumn = require('web.KanbanColumn');

KanbanColumn.include({
    init: function () {
        this._super.apply(this, arguments);
        if (this.modelName === 'mailing.mailing') {
            this.draggable = false;
        }
    },
});

});
