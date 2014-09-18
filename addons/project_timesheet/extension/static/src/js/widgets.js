function odoo_project_timesheet_widgets(project_timesheet) {
    var QWeb = openerp.qweb,
    _t = openerp._t;

    project_timesheet.project_timesheet_widget = openerp.Widget.extend({
        template: "ProjectTimesheet",
        init: function() {
            this._super.apply(this, arguments);
            project_timesheet.project_timesheet_model = new project_timesheet.project_timesheet_model(this.session);
        },
        start: function() {
            this._super.apply(this, arguments);
            this.$el.on('click', this.on_button_click);
            //Add the concept of screen, screen will decide which widgets to render at which position
            var pt_activity = new project_timesheet.ActivityScreen(this, {})
            pt_activity.replace(this.$el.find(".content_area"));
            var pt_footer = new project_timesheet.FooterWidget(this, {});
            pt_footer.replace(this.$el.find(".pt_footer"))
        },
        on_button_click: function(e) {
            this.$dialog_box = $(QWeb.render('InfoModal', {title: 'First Modal'})).appendTo("body");
            this.$dialog_box.modal('show');
        },
    });

    project_timesheet.FooterWidget = openerp.Widget.extend({
        template: "Footer",
        init: function() {
            this._super.apply(this, arguments);
        },
        start: function() {
            this._super.apply(this, arguments);
        }
    });
}