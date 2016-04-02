odoo.define('website_crm.backend', function (require) {
"use strict";

var core = require('web.core');
var WebsiteBackend = require('website.backendDashboard');

var QWeb = core.qweb;

WebsiteBackend.include({

    events: _.defaults({
        'change .js_field_selection': 'on_field_selection',
    }, WebsiteBackend.prototype.events),

    init: function(parent, context) {
        this._super(parent, context);

        this.dashboards_templates.push('website_crm.dashboard_leads');
        this.graphs.push('leads');

        this.leads_table = [];
        this.lead_fields = [];
        this.lead_field = '';
    },

    compute_percentages: function() {
        if (!this.dashboards_data.leads.leads || !this.dashboards_data.leads.leads.length) {
            return;
        }
        var leads = this.dashboards_data.leads.leads;
        var lead_field_keys = _.pluck(leads, this.lead_field);
        var leads_counter = _.groupBy(lead_field_keys);
        this.leads_table = $.map(leads_counter, function(e, key) {
            return {
                'value': e.length,
                'key': key,
                'perc': Math.round(e.length*100/leads.length)
            };
        });
        this.leads_table.sort(function(a, b) { return b.value - a.value; });
    },

    fetch_data: function() {
        var self = this;
        return this._super().then(function() {
            var leads = self.dashboards_data.leads.leads;
            if (leads && leads.length) {
                self.lead_fields = Object.keys(self.dashboards_data.leads.leads[0]);
                self.lead_field = self.lead_fields[0];
                self.compute_percentages();
            }
        });
    },

    on_field_selection: function(ev) {
        this.lead_field = ev.currentTarget.value;
        this.compute_percentages();
        this.$('.js_leads_table').replaceWith(QWeb.render("website.LeadsTable", {'widget': this}));
    },
});

});
