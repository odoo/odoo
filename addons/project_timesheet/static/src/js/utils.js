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

    // Takes a decimal hours and converts it to hh:mm string representation
    // e.g. 1.5 => "01:30"
    project_timesheet.unit_amount_to_hours_minutes = function(unit_amount){
        if(_.isUndefined(unit_amount)){
            return ["00","00"];
        }

        var minutes = Math.round((unit_amount % 1) * 60);
        var hours = Math.floor(unit_amount);

        if(minutes < 10){
            minutes = "0" + minutes.toString();
        }
        else{
            minutes = minutes.toString();
        }
        if(hours < 10){
            hours = "0" + hours.toString();
        }
        else{
            hours = hours.toString();
        }

        return [hours, minutes];
    };

    project_timesheet.get_sync_label = function() {
        var label = "Sync";
        if (project_timesheet.session && project_timesheet.session.display_username) {
            label = project_timesheet.session.display_username;
        }
        return label;
    };
};