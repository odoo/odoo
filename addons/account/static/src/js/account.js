openerp.account = function(instance) {
    instance.account.extend_view = instance.web.ViewManager.include({
        start : function(){
            this._super()
            this.setup_exended_list_view()
        },
        setup_exended_list_view: function(parent){
            if (this.action && this.action.extended_form_view_id){
                var self = this
                view_id = this.action.extended_form_view_id[0]
                var from_view = this.registry.get_object('form');
                this.dataset_form.context.extended_from = true
                this.dataset_form.read_slice()
                this.dataset_form.context.extended_from = false
                var obj_from_view = new from_view(this, this.dataset_form, view_id, options={});
                this.obj_from_view = obj_from_view
                obj_from_view.template = 'ExtendedFormView' 
                view_promise = obj_from_view.appendTo(this.$element.find('.oe_extended_form_view'))
                $.when(view_promise).then(function() {
                    obj_from_view.on_pager_action('first')
                })
            }
        },
    })
    instance.account.extend_view_action = instance.web.ViewManagerAction.include({
        init: function(parent, action) {
            this._super(parent, action)
            this.dataset_form = new instance.web.DataSetSearch(this, action.res_model, action.context, action.domain);
        },
    })
    instance.account.extend_form_view = instance.web.FormView.include({
        on_pager_action: function(action) {
            var self = this
            var viewmanager = self.__parentedParent
            $.when(this._super(action)).then(function() {
                var id = self.get_fields_values().partner_id
                viewmanager.action.domain = [["partner_id", "=", id]]
                viewmanager.searchview.do_search()
            })
        }
    })
}
