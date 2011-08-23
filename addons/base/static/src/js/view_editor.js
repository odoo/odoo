openerp.base.view_editor = function(openerp) {
openerp.base.ViewEditor = openerp.base.Dialog.extend({
    init: function(parent, element_id, dataset, view, options) {
        this._super(parent);
        self.template = 'ViewEditor';
        this.element_id = element_id
        this.parent = parent
        this.dataset = dataset;
        this.model = dataset.model;

        this.fields_views = view;
    },
    start: function() {

        var self = this;

    },
});
};
