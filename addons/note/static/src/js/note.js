odoo.define("note.note", function(require) {
'use strict';

var core = require('web.core');
var KanbanColoumn = require('web_kanban.Column');

var _t = core._t;

KanbanColoumn.include({
    init: function() {
        this._super.apply(this, arguments);
        if ((this.dataset.model === 'note.note') && (this.dataset.domain.length > 0)){
            this.title = ((this.dataset.domain[0][0] === 'id')) ? _t('Shared') : this.title;
        }
    },
});

}); 