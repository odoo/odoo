openerp.account = function(instance) {
var _t = instance.web._t,
   _lt = instance.web._lt;
instance.web.views.add('form_clone', 'instance.account.extend_form_view');
instance.web.form.tags.add('list_button','instance.account.list_button')
instance.account.extend_actionmanager = instance.web.ActionManager.include({
    ir_actions_act_window: function (action, on_close) {
        var self = this;
        if (_(['base.module.upgrade', 'base.setup.installer'])
                .contains(action.res_model)) {
            var old_close = on_close;
            on_close = function () {
                instance.webclient.do_reload().then(old_close);
            };
        }
        if (action.target === 'new') {
            if (this.dialog == null) {
                this.dialog = new instance.web.Dialog(this, { width: '80%' });
                if(on_close)
                    this.dialog.on_close.add(on_close);
            } else {
                this.dialog_viewmanager.destroy();
            }
            this.dialog.dialog_title = action.name;
            this.dialog_viewmanager = new instance.web.ViewManagerAction(this, action);
            this.dialog_viewmanager.appendTo(this.dialog.$element);
            this.dialog.open();
        } else  {
            this.dialog_stop();
            this.content_stop();
            if(action.menu_id) {
                return this.getParent().do_action(action, function () {
                    instance.webclient.menu.open_menu(action.menu_id);
                });
            }
            this.inner_action = action;
            if (action.extended_form_view_id){
                this.inner_viewmanager = new instance.account.extend_viewmanager(this, action);
            }else{
                this.inner_viewmanager = new instance.web.ViewManagerAction(this, action);
            }
            this.inner_viewmanager.appendTo(this.$element);
        }
    },
    })
    
instance.account.extend_viewmanager = instance.web.ViewManagerAction.extend({
    init: function(parent, action) {
        this._super.apply(this,arguments);
        this.dataset_form = new instance.web.DataSetSearch(this, action.res_model, action.context, action.domain);
    },
    start : function(){
        this._super()
        this.setup_exended_list_view(this)
    }, 
    on_mode_switch: function (view_type, no_store, options) {
        self = this
        self.list_loaded = $.when(this._super.apply(this, arguments)).then(function () {
            self.list_view = self.views['list']
        })
    },
    setup_exended_list_view: function(parent){
        var from_view,
            obj_from_view;
        view_id = this.action.extended_form_view_id[0]
        from_view = this.registry.get_object('form_clone');
        this.dataset_form.context.extended_from = true
        this.dataset_loaded  = this.dataset_form.read_slice()
        this.dataset_form.context.extended_from = false
        obj_from_view = new from_view(self, this.dataset_form, view_id, options={});
        obj_from_view.template = 'ExtendedFormView' 
        view_promise = obj_from_view.appendTo(this.$element.find('.oe_extended_form_view'))
        $.when(view_promise && this.dataset_loaded).then(function() {
            obj_from_view.on_pager_action('first')
        })
    } 
    
})
instance.account.extend_form_view = instance.web.FormView.extend({
    init :function(){
        this._super.apply(this,arguments);
        this.original_domain = this.getParent().action.domain;
    },
    on_pager_action: function(action) {
        var self = this
        var viewmanager = self.getParent();
        viewmanager.action.domain = this.original_domain
        $.when(this._super(action)).then(function() {
            var id = self.get_fields_values().partner_id;
            viewmanager.action.domain = (viewmanager.action.domain || []).concat([["partner_id", "=", id]])
            viewmanager.searchview.do_search()
        })
    }
})
instance.account.list_button = instance.web.form.WidgetButton.extend({
    on_click: function() {
        var list_view = this.view.getParent().list_view.controller
        ids = list_view.get_selected_ids()
        if (ids.length == 0) {
            instance.web.dialog($("<div />").text(_t("You must choose at least one record.")), { title: _t("Warning"), modal: true });
            return false;
        }
        var additional_context = _.extend({
            active_id: ids[0],
            active_ids: ids,
            active_model: list_view.dataset.model
        });
        self.rpc("/web/action/load", {
            action_id: py.eval(this.node.attrs.name),
            context: additional_context
        }, function(result) {
            result.result.context = _.extend(result.result.context || {},
                additional_context);
            result.result.flags = result.result.flags || {};
            result.result.flags.new_window = true;
            self.do_action(result.result, function () {
                // reload view
                list_view.reload();
            });
        });
   }
})
 
}
