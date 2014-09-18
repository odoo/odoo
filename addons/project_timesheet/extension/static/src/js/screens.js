function odoo_project_timesheet_screens(project_timesheet) {
    project_timesheet.ActivityScreen = openerp.Widget.extend({
        template: "ActivityScreen",
        init: function() {
            this._super.apply(this, arguments);
        },
        start: function() {
            this._super.apply(this, arguments);
        }
    });

    project_timesheet.ModifyActivityScreen = openerp.Widget.extend({
        template: "ModifyActivityScreen",
        init: function() {
            this._super.apply(this, arguments);
        },
        start: function() {
            this._super.apply(this, arguments);
        }
    });

    project_timesheet.SyncScreen = openerp.Widget.extend({
        template: "SyncScreen",
        init: function() {
            this._super.apply(this, arguments);
        },
        start: function() {
            this._super.apply(this, arguments);
        }
    });

    project_timesheet.StatisticScreen = openerp.Widget.extend({
        template: "StatisticScreen",
        init: function() {
            this._super.apply(this, arguments);
        },
        start: function() {
            this._super.apply(this, arguments);
        }
    });
}