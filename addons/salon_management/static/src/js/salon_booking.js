odoo.define('salon_management.website_salon_booking_system', function(require) {
    'use strict';
    var ajax = require('web.ajax');
    $(document).on('click', "#submit_button", function() {
        var name = $("#name").val();
        var date = $("#date").val();
        var time = $("#time").val();
        var phone = $("#phone").val();
        var chair = $("#chair").val();
        var duration = $("#duration").val();
        var bank_trx_id = $ ("#bank_trx_id").val();
        if (typeof bank_trx_id === 'undefined') {
            bank_trx_id = "None"
          }

        if (name == "" || date == "" || time == "" || phone == "" || chair == "" || duration == "") {
            alert("All fields are mandatory");
        } else {
            var time_left_char = time.substring(0, 2);
            var time_right_char = time.substring(3, 5);
            var time_separator = time.substring(2, 3);
            if (isNaN(time_left_char) || isNaN(time_right_char) || time_separator != ":") {
                alert("Select a valid Time");
            } else {
                document.querySelector("#submit_button").innerText = "Sending";
                var time_left = parseInt(time_left_char);
                var time_right = parseInt(time_right_char);
                console.log(time_left, time_right)
                if ((time_left < 24) && (time_right < 60) && (time_left >= 0) && (time_right >= 0)) {
                    var booking_record = { 'name': name, 'date': date, 'time': time, 'phone': phone, 'chair': chair, 'duration': duration,'bank_trx_id':bank_trx_id };
                    $.ajax({
                        url: "/page/salon_details",
                        type: "POST",
                        dataType: "json",
                        data: booking_record,
                        type: 'POST',
                        success: function(data) {
                            window.location.href = "/page/sport_management.sport_booking_thank_you";
                        },
                        error: function(error) {
                            alert('error: ' + error);
                        }
                    });
                } else {
                    alert("Select a valid time");
                }
            }
        }

    });

    $(document).on('click', "#check_button", function() {
        var check_date = $("#check_date").val();
        var court_option = $("#court_option_infor").val();

        if (check_date != "") {
            if(court_option == "Booked Court")
            {
                ajax.jsonRpc("/page/salon_check_date_booked_court", 'call', { 'check_date': check_date })
                .then(function(order_details) {
                    var x;
                    var total_orders = "";
                    var order = "";
                    var chair_name;
                    for (x in order_details) {
                        var chair_name = order_details[x]['name']
                        var i;
                        var lines = "";
                        for (i = 0; i < order_details[x]['orders'].length; i++) {
                            lines += '<tr><td><span>' + order_details[x]['orders'][i]['number'] +
                                '</span></td><td><span>' + order_details[x]['orders'][i]['start_time_only'] +
                                '</span></td><td><span>' + order_details[x]['orders'][i]['end_time_only'] + '</span></td></tr>'
                        }
                        order += '<div class="col-lg-4 s_title pt16 pb16 row"><div style="height: 200px!important; text-align: center;' +
                            'border: 1px solid #666;padding: 15px 0px;box-shadow: 7px 8px 5px #888888;background-color:#389D38;border-radius:10px;color:#fff;margin-bottom: 10px;">' +
                            '<span style="font-size: 15px;">' + chair_name + '</span>' +
                            '<br/><a style="color:#fff;font-size:15px;">Booked Details</a>' +
                            '<div id="style-2" style="overflow-y:scroll;height:105px;padding-right:25px;padding-left:25px;margin-right:10px;">' +
                            '<table class="table"><th style="font-size:11px;color:#fff;">Booked No.</th><th style="font-size:11px;color:#fff;">Start Time</th>' +
                            '<th style="font-size:12px;color:#fff;">End Time</th><div><tbody style="font-size:12px;color:#fff;">' +
                            lines + '</tbody></div></table></div></div></div>'

                    }
                    total_orders += '<div id="booking_chair_div" class="col-lg-12 s_title pt16 pb16 row">' + order + '</div>'
                    var res = document.getElementById('booking_chair_div')
                    res.innerHTML = "";
                    res.innerHTML = total_orders;
                    var date_value = 'DATE : <t>' + check_date + '</t>'
                    var date_field = document.getElementById('searched_date')
                    date_field.innerHTML = "";
                    date_field.innerHTML = date_value;
                })
            }
            else
            {
                ajax.jsonRpc("/page/salon_check_date_available_court", 'call', { 'check_date': check_date })
                .then(function(order_details) {
                    var x;
                    var total_orders = "";
                    var order = "";
                    var chair_name;
                    for (x in order_details) {
                        var chair_name = order_details[x]['name']
                        var i;
                        var lines = "";
                        for (i = 0; i < order_details[x]['orders'].length; i++) {
                            lines += '<tr><td><span>' + order_details[x]['orders'][i]['number'] +
                                '</span></td><td><span>' + order_details[x]['orders'][i]['start_time_only'] +
                                '</span></td><td><span>' + order_details[x]['orders'][i]['end_time_only'] + '</span></td></tr>'
                        }
                        order += '<div class="col-lg-4 s_title pt16 pb16 row"><div style="height: 200px!important; text-align: center;' +
                            'border: 1px solid #666;padding: 15px 0px;box-shadow: 7px 8px 5px #888888;background-color:#389D38;border-radius:10px;color:#fff;margin-bottom: 10px;">' +
                            '<span style="font-size: 15px;">' + chair_name + '</span>' +
                            '<br/><a style="color:#fff;font-size:15px;">Available Details</a>' +
                            '<div id="style-2" style="overflow-y:scroll;height:105px;padding-right:25px;padding-left:25px;margin-right:10px;">' +
                            '<table class="table"><th style="font-size:11px;color:#fff;">Available No.</th><th style="font-size:11px;color:#fff;">Start Time</th>' +
                            '<th style="font-size:12px;color:#fff;">End Time</th><div><tbody style="font-size:12px;color:#fff;">' +
                            lines + '</tbody></div></table></div></div></div>'

                    }
                    total_orders += '<div id="booking_chair_div" class="col-lg-12 s_title pt16 pb16 row">' + order + '</div>'
                    var res = document.getElementById('booking_chair_div')
                    res.innerHTML = "";
                    res.innerHTML = total_orders;
                    var date_value = 'DATE : <t>' + check_date + '</t>'
                    var date_field = document.getElementById('searched_date')
                    date_field.innerHTML = "";
                    date_field.innerHTML = date_value;
                    // alert("Available Booking Court Coming Soon")
                })
            }
            
        } 
        else 
        {
            alert("Fill the Field");
        }
    });
});