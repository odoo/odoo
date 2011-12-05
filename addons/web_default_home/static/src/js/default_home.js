openerp.web_default_home = function(openerp) {
  var QWeb = openerp.web.qweb;

  openerp.web.client_actions.add('default_home', 'openerp.web.Welcome');
  openerp.web.Welcome = openerp.web.Widget.extend({
    init: function(parent) {
            this._super(parent);
          },
    start: function() {
       var self = this;
       var applications = [
          {module: 'crm', name: 'CRM', menu: 'Sales', help: "Acquire leads, follow opportunities, manage prospects and phone calls, \u2026"},
          {module: 'sale', name: 'Sales', menu: 'Sales', help: "Do quotations, follow sales orders, invoice and control deliveries"},
          {module: 'account_voucher', name: 'Invoicing', menu: 'Accounting', help: "Send invoice, track payments and reminders"},
          {module: 'point_of_sale', name: 'Point of Sale', menu: 'Point of Sale', help: "Manage shop sales, use touch-screen POS"},
          {module: 'purchase', name: 'Purchase', menu: 'Sales', help: "Do purchase orders, control invoices and reception, follow your suppliers, \u2026"},
          {module: 'stock', name: 'Warehouse', menu: 'Warehouse', help: "Track your stocks, schedule product moves, manage incoming and outgoing shipments, \u2026"},
          {module: 'mrp', name: 'Manufacturing', menu: 'Manufacturing', help: "Manage your manufacturing, control your supply chain, personalize master data, \u2026"},
          {module: 'account_accountant', name: 'Accounting & Finance', menu: 'Accounting', help: "Record financial operations, automate followup, manage multi-currency, \u2026"},
          {module: 'project', name: 'Projects', menu: 'Project', help: "Manage projects, track tasks, invoice task works, follow issues, \u2026"},
          {module: 'hr', name: 'Human Resources', menu: 'Human Resources', help: "Manage employees and their contracts, follow laves, recruit people, \u2026"},
          {module: 'marketing', name: 'Marketing', menu: 'Marketing', help: "Manage campaigns, follow activities, automate emails, \u2026"},
          {module: 'knowledge', name: 'Knowledge', menu: 'Knowledge', help: "Track your documents, browse your files, \u2026"}
       ];

       var Installer = new openerp.web.DataSet(this, 'base.setup.installer');
       Installer.call('default_get', [], function (installed_modules) {
         console.log(installed_modules);
         self.$element.html(QWeb.render('Welcome-Page', {'applications': applications}));
         self.$element.find('.install-module-link').click(function () {
           self.install_module($(this).data('module'), $(this).data('menu'));
           return false;
         });
       });
     },
    install_module: function (module_name, menu_name) {
        var self = this;
        var Modules = new openerp.web.DataSetSearch(
            this, 'ir.module.module', null,
            [['name', '=', module_name], ['state', '=', 'uninstalled']]);
        var Upgrade = new openerp.web.DataSet(this, 'base.module.upgrade');

        $.blockUI();
        Modules.read_slice(['id'], {}, function (records) {
            if (!(records.length === 1)) { $.unblockUI(); return; }
            Modules.call('state_update',
                [_.pluck(records, 'id'), 'to install', ['uninstalled']],
                function () {
                    Upgrade.call('upgrade_module', [[]], function () {
                        self.run_configuration_wizards(menu_name);
                    });
                }
            )
        });
    },
    run_configuration_wizards: function (menu_name) {
        var self = this;
        new openerp.web.DataSet(this, 'res.config').call('start', [[]], function (action) {
            self.widget_parent.widget_parent.do_action(action, function () {
                openerp.webclient.do_reload();
            });
            self.$element.empty();
            var dss = new openerp.web.DataSetSearch(this, 'ir.ui.menu', null, [['parent_id', '=', false], ['name', '=', menu_name]]);
            dss.read_slice(['id'], {}, function(menus) {
                if(!(menus.length === 1)) { $.unblockUI(); return; }
                $.when(openerp.webclient.menu.on_menu_click(null, menus[0].id)).then($.unblockUI);
            });
        });
    }
  });

};

