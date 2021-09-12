/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

odoo.define('saas_kit_custom_plan.product_page', function (require) {
    "use strict";
    var session = require('web.session');
    var rpc = require('web.rpc');
    var ajax = require('web.ajax');
    var number = 0;
    var publicWidget = require('web.public.widget');
    var total_cost = 0;

    publicWidget.registry.CustomPlan = publicWidget.Widget.extend({
        selector: '.custom_plan_section',

        events: {
            'click  .check_app' : '_onCheckApp',
            'click   #create_request': '_onCreateRequest',
            'click  .version_button' : '_onSelectVersion',
            'click  .billing_cycle' : '_onSelectBilling',
            'change #number_of_users' : '_onChangeUsers',
        },

        _onSelectVersion : function(event){
            var version_name = $(event.target).text();
            var version_code = $(event.target).attr('data-code');
            $('#dropdownmenu2').text(version_name);
            $('#dropdownmenu2').attr('data-code', version_code);
        },

        _onSelectBilling : function(event){
            var billing_type = $(event.target).text();
            $('#dropdownmenu3').text(billing_type);
            var costing_nature = $('#costing_nature').text();
            if (costing_nature == 'per_month'){            
                var app_costing = $('#app_cost').text();
                app_costing = parseInt(app_costing);
                var number = 1;
                if (billing_type == 'Monthly'){
                    number = 1;
                }
                else{
                    number = 12;
                }
                var total = app_costing * number;
                $('#app_cost_number').text(number.toString());
                $('#app_total_cost').text(total.toString());
            }
        },

        _onCheckApp : function(e){
            var currency_name = $('#currency').text();
            var billing_type = $('#dropdownmenu3').text().trim();
            var users = parseInt($('#number_of_users').val());
            var costing_nature = $('#costing_nature').text();
            var checked_box = $(event.target).is(':checked');
            var total_count = $('#total_apps_count').text();
            total_count = parseInt(total_count);
            var target_app_cost = $(event.target).parent().parent().parent().children('.product_div').children('.product_price').children().children().children().text();
            target_app_cost = parseInt(target_app_cost);
            var app_costing = $('#app_cost').text();
            app_costing = parseInt(app_costing);
            var user_cost = $('#user_cost').text();
            if (costing_nature=='per_month'){
                if (billing_type=='Yearly'){
                    number = 12;
                }
                else {
                    number = 1
                }
            }else{
                number = $('#number_of_users').val();
            }
            var app_name = $(event.target).parent().parent().parent().children('.product_div').children('.product_name').children().children().text();
            var border_name = app_name+'_border'
            if (checked_box){
                app_costing = app_costing + target_app_cost;
                total_count = total_count + 1;
                // product_name = $.trim(product_name)
                var prod = parseInt(app_costing) * parseInt(number);
                // total_cost = total_cost + prod;
                // app = parseInt(app);
                // app = app + parseInt(product_name);

                var name_div = "<div style='height: 40px;' class='d-flex product_items' id='"+app_name+"'>"+
                "<div style='width: 54%; margin-left: 8%; margin-top:3%;font-size: 17px;' class='d-flex fw-bold'>"+app_name+
                "</div>"+"<span style='margin-top:2%; font-size:20px;'>"+target_app_cost+"</span>"+" <span style='margin-left:3%; margin-top:4%;' itemprop='priceCurrency'>"+currency_name+"</span>"+
                
            "</div>"+
            "<div id='"+border_name+"' style='border: 1px solid #E0E0E0; height:1px;' class='.bg-secondary'>"+
            "</div>";
            $('#product_title_head').prepend(name_div);

            }
            else{
                app_costing = app_costing - target_app_cost;
                var prod = parseInt(app_costing) * parseInt(number);
                total_count = total_count - 1;
                $('#'+app_name).remove();
                $('#'+border_name).remove();

            }
            var count = total_count.toString();
            $('#total_apps_count').text(count);
            $('#app_cost').text(app_costing.toString());
            $('#app_total_cost').text(prod.toString());
        },

        _onCreateRequest : function(e){
            var billing_type = $('#dropdownmenu3').text().trim();
            if (! billing_type){
                alert("Please select Billing Cycle");
                return 
            }
            var recurring_interval = 0;
            var a = billing_type == 'Monthly';
            if (billing_type == 'Monthly'){
                recurring_interval = 1;
            }
            else{
                recurring_interval = 12;
            }
            var users = $('#number_of_users');
            var checkbox = $('input:checkbox:checked');
            if (checkbox.length == 0){
                alert('Please Select Atleast One App to continue !')
                return
            }
            var version_name = $('#dropdownmenu2').attr('data-code');
            if (version_name == '1'){
                alert('Please Select Version to continue !')
                return
            }
            var apps = new Array();
            checkbox.each(function(i, el){
                apps.push($(this).parent().parent().parent().children('.product_div').children('.product_name').attr('data-value'));
            });
            var number_of_users = parseInt(users.val());
            if (users.length && ! number_of_users){
                alert('Please Enter User to Continue');                
            }
            var user_cost = parseInt($('#user_cost').text());
            var total_cost = parseInt($('#app_total_cost').text());
            var users_cost = parseInt($('#prod_user').text());
            var free_users = parseInt($('#free_users').text());
            if (free_users){
                users_cost = users_cost - free_users * user_cost;
                if (users_cost < 0){
                    users_cost = 0;
                }
            }
            ajax.jsonRpc("/saas/add/plan", 'call', {
                'apps': apps,
                'saas_users': number_of_users,
                'version_name': version_name,
                'total_cost': total_cost,
                'users_cost': users_cost,
                'recurring_interval' : recurring_interval,
            }).then(function(a){
                location.href='/shop/cart';
            });
        },


        _onChangeUsers : function(e){
            var users = $('#number_of_users').val();
            $('#user_selected_1').text(users.toString());
            var user_cost = parseInt($('#user_cost').text());
            var total = user_cost * users;
            $('#prod_user').text(total.toString());
            var costing_nature = $('#costing_nature').text();
            if (costing_nature == 'per_user'){
                $('#app_cost_number').text(users.toString());
                var app_cost = parseInt($('#app_cost').text());
                total = app_cost * users;
                $('#app_total_cost').text(total.toString());
            }
        }

    });
        
});
