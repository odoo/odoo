/*---------------------------------------------------------
 * OpenERP base library
 *---------------------------------------------------------*/

openerp.base.tree = function(openerp) {

openerp.base.views.add('tree', 'openerp.base.TreeView');
openerp.base.TreeView = openerp.base.Controller.extend({
/**
 * Genuine tree view (the one displayed as a tree, not the list)
 */
    start: function () {
        this._super();
        this.$element.append('Tree view');
    },
    do_show: function () {
        this.$element.show();
    },
    do_hide: function () {
        this.$element.hide();
    }
});

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
