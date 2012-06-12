openerp.account = function(instance) {
    instance.account.extend_view = instance.web.ViewManager.include({
        start : function(){
            this._super()
            this.setup_exended_list_view()
        },
        
        setup_exended_list_view: function(parent){
            if (this.action && this.action.extended_form_view_id){
                view_id = this.action.extended_form_view_id[0]
                var from_view = this.registry.get_object('form');
                var options = {}
                var obj_from_view = new from_view(this, this.dataset, view_id, options);
                obj_from_view.template = 'ExtendedFormView' 
                obj_from_view.appendTo(this.$element.find('.oe_extended_form_view'))
            }
        },
    })
}
