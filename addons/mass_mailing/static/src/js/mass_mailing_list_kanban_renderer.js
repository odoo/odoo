odoo.define('mass_mailing.ListKanbanRenderer', function (require) {
"use strict";

var MassMailingListKanbanRecord = require('mass_mailing.ListKanbanRecord');

var KanbanRenderer = require('web.KanbanRenderer');

var MassMailingListKanbanRenderer = KanbanRenderer.extend({
    config: _.extend({}, KanbanRenderer.prototype.config, {
        KanbanRecord: MassMailingListKanbanRecord,
    })
});

return MassMailingListKanbanRenderer;

});
