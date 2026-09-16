odoo.define('salon_management.website_salon_booking', function (require) {
    'use strict';

    var ajax = require('web.ajax');
    var core = require('web.core');
    var _t = core._t;
    var rpc = require('web.rpc');
    var QWeb = core.qweb;

    $(document).on('click', "#submit_button", function () {
        var name = $("#name").val();
        var date = $("#date").val();
        var time = $("#time").val();
        var phone = $("#phone").val();
        var email = $("#email").val();
        var service = $('.check_box_salon:checkbox:checked');
        var chair = $("#chair").val();
        var list_service = [];
        var number = service.length;
        for (var i = 0; i < (service.length); i++) {
            var k = { i: service[i].attributes['service-id'].value };
            list_service.push(k);
        }
        if (name == "" || date == "" || time == "" || phone == "" || email == "" || list_service.length == 0) {
            alert("All fields are mandatory");
        } else {
            var time_left_char = time.substring(0, 2);
            var time_right_char = time.substring(3, 5);
            var time_separator = time.substring(2, 3);
            if (isNaN(time_left_char) || isNaN(time_right_char) || time_separator != ":") {
                alert("Select a valid Time");
            } else {
                var time_left = parseInt(time_left_char);
                var time_right = parseInt(time_right_char);
                if ((time_left < 24) && (time_right < 60) && (time_left >= 0) && (time_right >= 0)) {
                    var booking_record = { 'name': name, 'date': date, 'time': time, 'phone': phone, 'email': email, 'list_service': list_service, 'chair': chair, 'number': number };
                    $.ajax({
                        url: "/page/salon_details",
                        type: "POST",
                        dataType: "json",
                        data: booking_record,
                        success: function (data) {
                            window.location.href = "/page/salon_management/salon_booking_thank_you";
                        },
                        error: function (error) {
                            alert('error: ' + error);
                        }
                    });
                } else {
                    alert("Select a valid time");
                }
            }
        }
    });

    $(document).on('click', "#check_button", function () {
        var check_date = $("#check_date").val();
        if (check_date != "") {
            ajax.jsonRpc("/page/salon_check_date", 'call', {
                'check_date': check_date
            }).then(function (order_details) {
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
                    order += '<div class="col-lg-4 s_title pt16 pb16"><div style="height: 200px!important; text-align: center;' +
                        'border: 1px solid #666;padding: 15px 0px;box-shadow: 7px 8px 5px #888888;background-color:#7c7bad;border-radius:58px;color:#fff;margin-bottom: 10px;">' +
                        '<span style="font-size: 15px;">' + chair_name + '</span>' +
                        '<br/><a style="color:#fff;font-size:15px;">Order Details</a>' +
                        '<div id="style-2" style="overflow-y:scroll;height:105px;padding-right:25px;padding-left:25px;margin-right:10px;">' +
                        '<table class="table"><th style="font-size:11px;">Order No.</th><th style="font-size:11px;">Start Time</th>' +
                        '<th style="font-size:11px;">End Time</th><div><tbody style="font-size: 10px;">' +
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
            });
        } else {
            alert("Fill the Field");
        }
    });

});
