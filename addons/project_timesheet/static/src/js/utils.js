function odoo_project_timesheet_utils(project_timesheet) {

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

        return hours + ":" + minutes;;
    };

    // Takes a string as input and tries to parse it as a hh:mm duration/ By default, strings without ":" are considered to be hh. 
    // We use % 1 to avoid accepting NaN as an integer.
    project_timesheet.validate_duration = function(hh_mm){
        var time = hh_mm.split(":");
        if(time.length === 1){
            var hours = parseInt(time[0]);
            if(hours % 1 != 0){
                return undefined;
            }
            if (hours < 10){
                return "0" + hours.toString() + ":00";
            }
            else{
                return hours.toString() + ":00";
            }
        }
        else if(time.length === 2){
            var hours = parseInt(time[0]);
            var minutes = parseInt(time[1]);
            if((hours % 1 === 0) && (minutes % 1 === 0) && minutes < 61){
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

                return hours + ":" + minutes;
            }
            else{
                return undefined;
            }
        }
        else{
            return undefined;
        }

    };

    project_timesheet.hh_mm_to_unit_amount = function(hh_mm){
        var time = hh_mm.split(":");
        if(time.length === 1){
            return parseInt(time[0]);
        }
        else if(time.length === 2){
            var hours = parseInt(time[0]);
            var minutes = parseInt(time[1]);
            return Math.round((hours + (minutes / 60 )) * 100) / 100;
        }
        else{
            return undefined;
        }
            
    };

    project_timesheet.get_sync_label = function() {
        var label = "Sync";
        if (project_timesheet.session && project_timesheet.session.display_username) {
            label = project_timesheet.session.display_username;
        }
        return label;
    };
};