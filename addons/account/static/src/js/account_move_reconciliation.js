openerp.account = function(instance) {
var _t = instance.web._t,
   _lt = instance.web._lt;
instance.web.views.add('form_clone', 'instance.account.extend_form_view');
instance.web.form.tags.add('list_button','instance.account.list_button')
instance.web.form.tags.add('btn_extend','instance.account.btn_extend')
instance.web.form.widgets.add('many2one_pager','instance.account.many2one_pager')
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
            if (this.dialog === null) {
                // These buttons will be overwrited by <footer> if any
                this.dialog = new instance.web.Dialog(this, {
                    buttons: { "Close": function() { $(this).dialog("close"); }},
            dialogClass: 'oe_act_window'
                });
                if(on_close)
                    this.dialog.on_close.add(on_close);
            } else {
                this.dialog_widget.destroy();
            }
            this.dialog.dialog_title = action.name;
            this.dialog_widget = new instance.web.ViewManagerAction(this, action);
            this.dialog_widget.appendTo(this.dialog.$element);
            this.dialog.open();
        } else  {
            this.dialog_stop();
            if(action.menu_id) {
                return this.getParent().do_action(action, function () {
                    instance.webclient.menu.open_menu(action.menu_id);
                });
            }
            this.inner_action = action;
            if (action.extended_form_view_id){
                var inner_widget = this.inner_widget = new instance.account.extend_viewmanager(this, action);
            }else{
                var inner_widget = this.inner_widget = new instance.web.ViewManagerAction(this, action);
            }
            inner_widget.add_breadcrumb();
            this.inner_widget.appendTo(this.$element);
        }
    }
    })
    
    
instance.account.extend_viewmanager = instance.web.ViewManagerAction.extend({
    init: function(parent, action) {
        this._super.apply(this, arguments);
        //Fix me: pass hard coded model name, find the way to fetch it from server
        this.dataset_form = new instance.web.DataSetSearch(this, 'account.move.reconciliation', action.context, action.domain);
    },
    start : function(){
        this._super()
        this.setup_exended_form_view(this)
    }, 
    on_mode_switch: function (view_type, no_store, options) {
        self = this
        self.list_loaded = $.when(this._super.apply(this, arguments)).then(function () {
            self.list_view = self.views['list']
        })
    },
    setup_exended_form_view: function(parent){
        var self = this,
            from_view,
            obj_from_view;
        view_id = this.action.extended_form_view_id[0]
        from_view = this.registry.get_object('form_clone');
        this.dataset_loaded  = this.dataset_form.read_slice()
        obj_from_view = new from_view(self, this.dataset_form, view_id, options={});
        obj_from_view.template = 'ExtendedFormView' 
        view_promise = obj_from_view.appendTo(this.$element.find('.oe_extended_form_view'))
        $.when(view_promise, this.dataset_loaded).then(function() {
            if (!_.isEmpty(self.dataset_form.ids)) {
                obj_from_view.on_pager_action('first')
            }
        })
    } 
    
})
instance.account.extend_form_view = instance.web.FormView.extend({
    init :function(){
        this._super.apply(this,arguments);
        this.original_domain = this.getParent().action.domain;
    },
    on_loaded: function(data) {
         this._super.apply(this,arguments);
         var self = this
         this.$element.on('click','a[data-pager-action]',function() {
            var action = $(this).data('pager-action');
            self.on_pager_action(action);
        });
    },
    do_update_pager: function(hide_index) {
        var index = hide_index ? '-' : this.dataset.index + 1;
        this.$element.find('span.oe_pager_index_extend').html(index).end()
                   .find('span.oe_pager_count_extend').html(this.dataset.ids.length);
    },
    on_pager_action: function(action) {
        var self = this
        var viewmanager = self.getParent();
        viewmanager.action.domain = this.original_domain
        $.when(this._super(action)).then(function() {
            var id = self.get_fields_values().partner_id;
            // apply domain on list
            viewmanager.action.domain = (viewmanager.action.domain || []).concat([["partner_id", "=", id]])
            viewmanager.searchview.do_search()
        })
    },
  })
instance.account.many2one_pager = instance.web.form.FieldMany2One.extend({
    template: "FieldMany2One_Pager",
    display_string: function(str) {
        var self = this;
        if (!this.get("effective_readonly")) {
            this.$input.val(str);
        } else {
            this.$element.find('a.oe_form_uri')
                 .unbind('click')
                 .text(str)
                 .click(function () {
                    self.do_action({
                        type: 'ir.actions.act_window',
                        res_model: self.field.relation,
                        res_id: self.get("value"),
                        context: self.build_context(),
                        views: [[false, 'form']],
                        target: 'current'
                    });
                    return false;
                 });
        }
    },
})
instance.account.btn_extend = instance.web.form.WidgetButton.extend({
    on_click: function() {
        var self = this;
        this.force_disabled = true;
        this.check_disable();
        this.execute_action().always(function() {
            self.force_disabled = false;
            self.check_disable();
            self.reload_view();
        });
        
    },
    reload_view :function(){
       viewmanager = this.view.getParent().getParent()
       viewmanager.inner_widget.list_view.controller.reload_content();
    },
    on_confirmed: function() {
        var self = this;

        var context = this.node.attrs.context;
        if (context && context.__ref) {
            context = new instance.web.CompoundContext(context);
            context.set_eval_context(this._build_eval_context());
        }

        return this.view.do_execute_action(
            _.extend({}, this.node.attrs, {context: context}),
            this.view.dataset, this.view.datarecord.id, function () {
                $.when(self.view.dataset.read_slice()).then(function() {
                     if (!_.isEmpty(self.view.dataset.ids)){
                        self.view.reload();
                        //reload list view
                        self.view.on_pager_action()
                     }
                })
            });
    },
})

instance.account.list_button = instance.web.form.WidgetButton.extend({
    on_click: function() {
        var self = this
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
                self.getParent().reload()
            });
        });
   }
})
 
}
