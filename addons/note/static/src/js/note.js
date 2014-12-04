odoo.define("note.note", function(require) {
'use strict';

var core = require('web.core');
var KanbanColoumn = require('web_kanban.Column');

var _t = core._t;

KanbanColoumn.include({
    init: function() {
        this._super.apply(this, arguments);
        this.title = ((this.dataset.model === 'note.note') && (this.title === _t('Undefined'))) ? _t('Shared') : this.title;
    },
});

});