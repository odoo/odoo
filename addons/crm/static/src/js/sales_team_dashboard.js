odoo.define('crm.sales_team_dashboard', function (require) {
"use strict";

var SalesTeamDashboard = require('sales_team.dashboard');

SalesTeamDashboard.Model.include({
    _fetchDashboardData: function() {
        return this.performModelRPC('crm.lead', 'retrieve_sales_dashboard');
    },
});

});
