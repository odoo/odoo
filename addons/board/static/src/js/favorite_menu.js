odoo.define('board.favorite_menu', function (require) {
"use strict";

var ActionManager = require('web.ActionManager');
var Context = require('web.Context');
var core = require('web.core');
var Domain = require('web.Domain');
var FavoriteMenu = require('web.FavoriteMenu');
var pyUtils = require('web.py_utils');

var _t = core._t;
var QWeb = core.qweb;

FavoriteMenu.include({
    /**
     * We manually add the 'add to dashboard' feature in the searchview.
     *
     * @override
     */
    start: function () {
        var self = this;
        if(this.action_id === undefined) {
            return this._super();
        }
        if (this.action.type === 'ir.actions.act_window') {
            this.add_to_dashboard_available = true;
            this.$('.o_favorites_menu').append(QWeb.render('SearchView.addtodashboard'));
            this.$add_to_dashboard = this.$('.o_add_to_dashboard');
            this.$add_dashboard_btn = this.$add_to_dashboard.eq(1).find('button');
            this.$add_dashboard_input = this.$add_to_dashboard.eq(0).find('input');
            this.$add_dashboard_link = this.$('.o_add_to_dashboard_link');
            var title = this.searchview.get_title();
            this.$add_dashboard_input.val(title);
            this.$add_dashboard_link.click(function (e) {
                e.preventDefault();
                self._toggleDashboardMenu();
            });
            this.$add_dashboard_btn.click(this.proxy('_addDashboard'));
        }
        return this._super();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * This is the main function for actually saving the dashboard.  This method
     * is supposed to call the route /board/add_to_dashboard with proper
     * information.
     *
     * @private
     * @returns {Deferred}
     */
    _addDashboard: function () {
        var self = this;
        var search_data = this.searchview.build_search_data();
        var context = new Context(this.searchview.dataset.get_context() || []);
        var domain = [];

        _.each(search_data.contexts, context.add, context);
        _.each(search_data.domains, function (d) {
            domain.push.apply(domain, Domain.prototype.stringToArray(d));
        });

        context.add({
            group_by: pyUtils.eval('groupbys', search_data.groupbys || [])
        });
        // AAB: trigger_up an event that will be intercepted by the controller,
        // as soon as the controller is the parent of the control panel
        var am = this.findAncestor(function (a) {
            return a instanceof ActionManager;
        });
        // with options 'keepSearchView', it may happen that the action_id of
        // the searchview (received in init) is not the one of the current
        // action, which corresponds to the one we want to add to dashboard
        var currentAction = am.getCurrentAction();
        var controller = am.getCurrentController();
        context.add(controller.widget.getContext());
        var c = pyUtils.eval('context', context);
        for (var k in c) {
            if (c.hasOwnProperty(k) && /^search_default_/.test(k)) {
                delete c[k];
            }
        }
        this._toggleDashboardMenu(false);
        c.dashboard_merge_domains_contexts = false;
        var name = self.$add_dashboard_input.val();

        return self._rpc({
                route: '/board/add_to_dashboard',
                params: {
                    action_id: currentAction.id || false,
                    context_to_save: c,
                    domain: domain,
                    view_mode: controller.viewType,
                    name: name,
                },
            })
            .then(function (r) {
                if (r) {
                    self.do_notify(
                        _.str.sprintf(_t("'%s' added to dashboard"), name),
                        _t('Please refresh your browser for the changes to take effect.')
                    );
                } else {
                    self.do_warn(_t("Could not add filter to dashboard"));
                }
            });
    },
    /**
     * @override
     * @private
     */
    _closeMenus: function () {
        if (this.add_to_dashboard_available) {
            this._toggleDashboardMenu(false);
        }
        this._super();
    },
    /**
     * @private
     * @param {undefined|false} isOpen
     */
    _toggleDashboardMenu: function (isOpen) {
        this.$add_dashboard_link
            .toggleClass('o_closed_menu', !(_.isUndefined(isOpen)) ? !isOpen : undefined)
            .toggleClass('o_open_menu', isOpen);
        this.$add_to_dashboard.toggle(isOpen);
        if (this.$add_dashboard_link.hasClass('o_open_menu')) {
            this.$add_dashboard_input.focus();
        }
    },
});

});
