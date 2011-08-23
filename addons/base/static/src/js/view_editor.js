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
        var action = {
            name:'ViewEditor',
            context:this.session.user_context,
//            domain: ["model", "=", this.dataset.model],
            res_model: 'ir.ui.view',
            views : [[false, 'list']],
            type: 'ir.actions.act_window',
            target: "current",
            limit : 80,
            auto_search : true,
            flags: {
                sidebar: false,
                views_switcher: false,
                action_buttons:false,
                search_view:false,
                pager:false,
            },
        };
        var action_manager = new openerp.base.ActionManager(this);
        this.dialog = new openerp.base.Dialog(this,{
            modal: true,
            title: 'ViewEditor',
            width: 600,
            height: 500,
            buttons: {

                Cancel: function(){
                     $(this).dialog('destroy');
                },
                Edit: function(){
                },
                Create: function(){
                }
            },
        });
       this.dialog.start();
       this.dialog.open();
       action_manager.appendTo(this.dialog);
       action_manager.render(this.dialog);
       action_manager.do_action(action);
    },
});
};
