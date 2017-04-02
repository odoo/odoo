odoo.define('crm.sales_team_dashboard', function (require) {
"use strict";

var SalesTeamDashboardView = require('sales_team.dashboard');
var Model = require('web.Model');

SalesTeamDashboardView.include({

    fetch_data: function() {
        return new Model('crm.lead')
            .call('retrieve_sales_dashboard', []);
    }
});

});
