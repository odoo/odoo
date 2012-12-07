openerp.note = function(instance) {     
    instance.web.FormView.include({ 
        init: function(parent, dataset, view_id, options) {
            this._super(parent, dataset, view_id, options);
            this.options.views_history = parent.views_history;             
        },
        to_view_mode: function(){
            var prev_view = this.options.views_history[this.options.views_history.length - 2];
            if(this.model == 'note.note' && prev_view == 'kanban'){
                this.do_switch_view(prev_view);
            }else{
                this._super();
            }
        },
    });
}
