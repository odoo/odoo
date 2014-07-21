openerp_client_action = function(instance) {
    var QWeb = instance.web.qweb;
    var _t = instance.web._t,
       _lt = instance.web._lt;

    instance.crm_linkedin = {};
    instance.linkedin_import_contacts = {};
    instance.crm_linkedin.dialog = instance.web.Widget.extend({
        init: function() {
            this._super.apply(this, arguments);
        },
        start: function() {
            this._super.apply(this, arguments);
            this.open_partner_action();
        },
        open_partner_action: function() {
            var self = this;
            var action = {
                name: _t('Customers'),
                type: 'ir.actions.act_window',
                res_model: 'res.partner',
                view_mode: 'kanban,tree,form',
                view_type: 'form',
                views: [[false, 'kanban'], [false, 'tree'], [false, 'form']],
                context: { "search_default_customer":1 },
            };
            instance.client.action_manager.do_action(action).done(function() { //No need to call do_action we can do same as instance.web.Reload
                var $dialog = new instance.web.Dialog(this, {
                        size: 'medium',
                        title: _t('LinkedIn Import Contact or Set API'),
                        buttons: [
                                { text: _t("Set API Key"), click: function() {  
                                    new instance.web.Model("ir.model.data").call("get_object_reference", ["base_setup", "action_sale_config"]).done(function(result) {
                                        return self.rpc("/web/action/load", {
                                            action_id: result[1],
                                        }).done(function (result) {
                                            $dialog.$dialog_box.modal('hide');
                                            return self.do_action(result, {}); //do_action will redirect to sale_config page but menu of settings will not loaded
                                        });
                                    });
                                }},
                                { text: _t("Import Contact"), click: function() { 
                                    var linkedin_import_button = self.getParent() && self.getParent().$el.find(".oe_kanban_import_contact");
                                    if (linkedin_import_button) { linkedin_import_button.trigger('click'); }
                                }},
                            ],
                }, QWeb.render('LinkedIn.InitialDialog', {widget: self})).open();
            });
        },
    });
    instance.web.client_actions.add('crm.linkedin.dialog', 'instance.crm_linkedin.dialog');
};