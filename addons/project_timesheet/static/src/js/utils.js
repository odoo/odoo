function odoo_project_timesheet_utils(project_timesheet) {

    project_timesheet.format_duration = function(value) {
        var data = value.toString().split(".");
        if (data[1]) {
            data[1] = Math.round((value%1)*60);
            if (data[1] == 60) {
                data[1] = 0;
                data[0] = parseInt(data[0]) + 1;
            }
        }
        return data;
    };

    project_timesheet.get_sync_label = function() {
        var label = "Sync";
        if (project_timesheet.session && project_timesheet.session.display_username) {
            label = project_timesheet.session.display_username;
        }
        return label;
    };
};