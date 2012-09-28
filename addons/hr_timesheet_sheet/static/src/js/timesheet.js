
openerp.hr_timesheet_sheet = function(instance) {
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;

    instance.hr_timesheet_sheet.WeeklyTimesheet = instance.web.form.FormWidget.extend({
        template: "hr_timesheet_sheet.WeeklyTimesheet",

    });

    instance.web.form.custom_widgets.add('weekly_timesheet', 'instance.hr_timesheet_sheet.WeeklyTimesheet');

};
