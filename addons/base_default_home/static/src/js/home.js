openerp.base_default_home = function (openerp) {
    QWeb.add_template('/base_default_home/static/src/xml/base_default_home.xml');

    openerp.base_default_home = {
        applications: [
            [
                {
                    module: 'crm', name: 'CRM',
                    help: "Acquire leads, follow opportunities, manage prospects and phone calls, \u2026"
                }, {
                    module: 'sale', name: 'Sales',
                    help: "Do quotations, follow sales orders, invoice and control deliveries"
                }, {
                    module: 'account_voucher', name: 'Invoicing',
                    help: "Send invoice, track payments and reminders"
                }, {
                    module: 'project', name: 'Projects',
                    help: "Manage projects, track tasks, invoice task works, follow issues, \u2026"
                }
            ], [
                {
                    module: 'purchase', name: 'Purchase',
                    help: "Do purchase orders, control invoices and reception, follow your suppliers, \u2026"
                }, {
                    module: 'stock', name: 'Warehouse',
                    help: "Track your stocks, schedule product moves, manage incoming and outgoing shipments, \u2026"
                }, {
                    module: 'hr', name: 'Human Resources',
                    help: "Manage employees and their contracts, follow laves, recruit people, \u2026"
                }, {
                    module: 'point_of_sale', name: 'Point of Sales',
                    help: "Manage shop sales, use touch-screen POS"
                }
            ], [
                {
                    module: 'profile_tools', name: 'Extra Tools',
                    help: "Track ideas, manage lunch, create surveys, share data"
                }, {
                    module: 'mrp', name: 'Manufacturing',
                    help: "Manage your manufacturing, control your supply chain, personalize master data, \u2026"
                }, {
                    module: 'marketing', name: 'Marketing',
                    help: "Manage campaigns, follow activities, automate emails, \u2026"
                }, {
                    module: 'knowledge', name: 'Knowledge',
                    help: "Track your documents, browse your files, \u2026"
                }
            ]
        ]
    };

    openerp.base.WebClient.include({
        default_home: function () {
            var self = this,
                // resig class can't handle _super in async contexts, by the
                // time async callback comes back, _super has already been
                // reset to a baseline value of this.prototype (or something
                // like that)
                old_home = this._super;
            var Installer = new openerp.base.DataSet(
                    this, 'base.setup.installer');
            Installer.call('already_installed', [], function (installed_modules) {
                if (!_(installed_modules).isEmpty()) {
                    return old_home.call(self);
                }
                self.$element.find('.oe-application').html(
                    QWeb.render('StaticHome', {
                        url: window.location.protocol + '//' + window.location.host + window.location.pathname,
                        session: self.session,
                        rows: openerp.base_default_home.applications
                })).delegate('.oe-static-home-tile-text button', 'click', function () {
                    self.install_module($(this).val());
                })

            }, function (err, event) {
                event.preventDefault();
                return old_home.call(self);
            });
        },
        install_module: function (module_name) {
            var Modules = new openerp.base.DataSetSearch(
                this, 'ir.module.module', null,
                [['name', '=', module_name], ['state', '=', 'uninstalled']]),
                Upgrade = new openerp.base.DataSet(this, 'base.module.upgrade');

            $.blockUI({
                message: '<img src="/base_default_home/static/src/img/throbber.gif">'
            });
            Modules.read_slice({fields: ['id']}, function (records) {
                if (!(records.length === 1)) { return; }
                Modules.call('state_update',
                    [_.pluck(records, 'id'), 'to install', ['uninstalled']],
                    function () {
                        Upgrade.call('upgrade_module', [[]], function () {
                            $.unblockUI();
                            // TODO: less brutal reloading
                            window.location.reload(true);
                        });
                    }
                )
            });
        }
    });
};
