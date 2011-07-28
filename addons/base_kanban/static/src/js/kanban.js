openerp.base_kanban = function (openerp) {
openerp.base.views.add('kanban', 'openerp.base_kanban.KanbanView');
openerp.base_kanban.KanbanView = openerp.base.View.extend({

    init: function(parent, element_id, dataset, view_id) {
        this._super(parent, element_id);
        this.view_manager = parent;
        this.dataset = dataset;
        this.model = this.dataset.model;
        this.view_id = view_id;
    },

    start: function() {
        this.rpc("/base_kanban/kanbanview/load",
        {"model": this.model, "view_id": this.view_id}, this.on_loaded);
    },

    on_loaded: function(data) {
        var template_xml = '';
        _.each(data.fields_view.arch.children, function(child) {
            if (child.tag == "template"){
                template_xml = openerp.base.json_node_to_xml(child, true)
            }
        });
        console.log(":template_xml:::",template_xml);
    },
});
};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
