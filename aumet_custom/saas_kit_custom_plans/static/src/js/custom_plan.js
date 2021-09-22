/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

odoo.define('saas_kit_custom_plan.product_page', function (require) {
    "use strict";
    var session = require('web.session');
    var rpc = require('web.rpc');
    var ajax = require('web.ajax');
    var number = 1;
    var publicWidget = require('web.public.widget');
    var total_app_value_span = 0;
    var final_cost_value_span = 0;
    var users_price = 0;
    var prev_cycle = 'Monthly';
    var remove_button = false;
    var apps = new Array();
    publicWidget.registry.CustomPlan = publicWidget.Widget.extend({
        selector: '.custom_plan_section',

        events: {
            'click #toggle_input': '_onToggleCategoryView',
            'click  .select_button' : '_onSelectApp',
            'mouseenter .selected_button' : '_onEnterSelectedButton',
            'mouseleave .remove_button' : '_onLeaveRemoveButton',      
            'click  .remove_button' : '_onClickRemoveButton',
            'click   #view_more_apps': '_onClickMoreApps',
            'click  .remove_app_button': '_onClickRemoveAppButton',
            'change #number_of_users' : '_onChangeUsers',
            'click #buy_now' : '_onClickBuyNow',
            'click .version_button' : '_onSelectVersion',
            'click .billing_cycle' : '_onSelectBilling',
        },

        _onToggleCategoryView : function(ev){
            var version_code = $('#dropdownmenu2').attr('data-code');
            if ($('input').is(':checked')){
                $.get("/show/categ/view", {
                }).then(function(data){
                    $('#normal_view_main_div').replaceWith(data);
                });
            }
            else{
                $.get("/show/normal/view", {
                }).then(function(data){
                    $('#category_view_main_div').replaceWith(data);
                });
            }
            $.get("/show/selected/apps/view", {
            }).then(function(data){
                $('#right_block').replaceWith(data);
                apps.length = 0;
                total_app_value_span = 0;
                final_cost_value_span = 0;
                users_price = 0;
            });

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
                rpc.query({
                    model: 'saas.odoo.version',
                    method: 'get_default_saas_values',
                    args: ['call'],
                })
                .then(function(data){
                    var user_cost = data['user_cost'];
                    if (billing_type == 'Monthly'){
                        number = 1;
                        if (prev_cycle == 'Yearly'){
                            total_app_value_span = total_app_value_span / 12;
                        }
                        prev_cycle = 'Monthly';
                    }
                    else{
                        number = 12;
                        if (prev_cycle == 'Monthly'){
                            total_app_value_span = total_app_value_span * 12;
                        }
                        prev_cycle = 'Yearly';
                    }
                    user_cost = user_cost * number;
                    if (data['is_users']){
                        var users = $('#number_of_users').val();
                        users_price = parseInt(users) * user_cost;
                        $('#user_price_span').text(user_cost.toString()+' ');
                        $('#total_users_value_span').text(users_price.toString()+' ');    
                    }
                    final_cost_value_span = total_app_value_span + users_price; 
                    $('#total_app_value_span').text(total_app_value_span.toString()+' ');
                    $('#final_cost_value_span').text(final_cost_value_span.toString()+' ');
                    $('#pay_now_value_span').text(final_cost_value_span.toString()+' ');
                });
            }
        },

        _onSelectApp : function(ev){
            $('#apps_complete_details').hide();
            // var currency_name = $('#currency').text();
            // var billing_type = $('#dropdownmenu3').text().trim();
            // var users = parseInt($('#number_of_users').val());
            // var costing_nature = $('#costing_nature').text();
            // var checked_box = $(event.target).is(':checked');
            var total_count = $('#total_apps_count').text();
            total_count = parseInt(total_count);
            total_count = total_count + 1;
            if (total_count < 10){ 
                $('#total_apps_count').text('0'+total_count.toString());
            }else{
                $('#total_apps_count').text(total_count.toString());
            }
            $(ev.currentTarget).closest('.select_button_div').find('.select_button').css('display', 'none');
            $(ev.currentTarget).closest('.select_button_div').find('.selected_button').css('display', 'inline');
            $(ev.currentTarget).closest('.app_card').css({'background-color': '#3AADAA;', 'border': '1px solid #3AADAA'});            
            $(ev.currentTarget).closest('.col-8').find('.app_name').css({'color': '#FFFFFF;'});            
            $(ev.currentTarget).closest('.col-8').find('.span_price').css({'color': '#FFFFFF;'});       
            $(ev.currentTarget).closest('.col-8').find('.price').css({'color': '#FFFFFF;'});
            var technical_name = $(ev.currentTarget).closest('.app_card').find('.app_tech_name').text();
            var name = $(ev.currentTarget).closest('.app_card').find('span.app_name').text();
            var height = $('#line_complete').css('height');
            height = height.split('p');
            if (height){
                height = parseInt(height[0]);
                height = height + 37;
                $('#line_complete').css('height', height.toString()+'px');
            }
            // if (total_count < 3){
                // $('.line_nodes_div').append('<div class="combine_node d-flex">'+
                //     '<div class="nodes">'+
                //     '</div>'+
                //     '<div class="node_head">'+
                //     '</div>'+
                // '</div>');
                // $('.apps_detail_div').prepend('<div class="apps_name_head d-flex" id="'+technical_name+'">'+                         
                //     '<div class="app_name">'+name+'</div>'+
                //     '<div class="app_price"> 17 USD'+
                //     '</div>'+
                //     '<div class="remove_button_div">'+
                //         '<button class="remove_app_button">'+
                //             'REMOVE'+
                //         '</button>'+
                //     '</div>'+
                // '</div>');
            // }

            // if (total_count == 3){
                // $('#view_more_apps_div').attr('style', 'display : inline');
                // $('#view_more_apps').attr('style', 'display :inline');
            // }
            // var target_app_cost = $(event.target).parent().parent().children('.app_price_div').children('.span_price').children('.price').text();
            // console.log(target_app_cost);            
            // target_app_cost = parseInt(target_app_cost);
            // console.log(technical_name);
            // console.log(target_app_cost);
            rpc.query({
                model: 'saas.module',
                method: 'search_read',
                args: [[['technical_name', '=', technical_name]],['price']],
            })
            .then(function(data){
                var price = parseInt(data[0]['price']);
                var price_1 = price * number;
                rpc.query({
                    model: 'saas.odoo.version',
                    method: 'get_default_saas_values',
                    args: ['call'],
                })
                .then(function(data){
                    var user_cost = data['user_cost'];
                    user_cost = user_cost * number;
                    if (data['is_users']){
                        var users = $('#number_of_users').val();
                        users_price = parseInt(users) * user_cost;

                    }
                    total_app_value_span = total_app_value_span + price_1;
                    final_cost_value_span = total_app_value_span + users_price;
                    $('#total_app_value_span').text(total_app_value_span.toString()+' ');
                    $('#final_cost_value_span').text(final_cost_value_span.toString()+' ');
                    $('#pay_now_value_span').text(final_cost_value_span.toString()+' ');
                    // $('#test_line_nodes_div').append('<div class="combine_node d-flex" id="'+technical_name+'_node">'+
                    //     // '<div class="nodes">'+
                    //     // '</div>'+
                    //     // '<div class="node_head">'+
                    //     // '</div>'+
                    // '</div>');
                    $('#test_apps_detail_div').prepend('<div class="apps_name_head d-flex" id="'+technical_name+'">'+
                        // '<div class="nodes">'+
                        // '</div>'+
                        '<div class="nodes">'+
                        '</div>'+
                        '<div class="node_head">'+
                        '</div>'+ 
                        '<div class="app_name_detail">'+name+'</div>'+
                        '<div class="app_price"> '+price+' USD'+
                        '</div>'+
                        '<div class="remove_button_div">'+
                            '<button class="remove_app_button">'+
                                'REMOVE'+
                            '</button>'+
                        '</div>'+
                    '</div>');
                    apps.push(technical_name);
                });
            });
        },

        _onEnterSelectedButton : function(ev){
            $(ev.currentTarget).closest('.select_button_div').find('.selected_button').css('display', 'none');
            $(ev.currentTarget).closest('.select_button_div').find('.remove_button').css('display', 'inline');
        },

        _onLeaveRemoveButton : function(ev){
            if (remove_button){
                remove_button = false;
            }else{
                $(ev.currentTarget).closest('.select_button_div').find('.selected_button').css('display', 'inline');
                $(ev.currentTarget).closest('.select_button_div').find('.remove_button').css('display', 'none');
            }
        },

        _onClickRemoveButton : function(ev){
            remove_button = true;
            var total_count = $('#total_apps_count').text();
            total_count = parseInt(total_count);
            total_count = total_count - 1;
            if (total_count < 10){ 
                $('#total_apps_count').text('0'+total_count.toString());
            }else{
                $('#total_apps_count').text(total_count.toString());
            }
            $(ev.currentTarget).closest('.select_button_div').find('.selected_button').css('display', 'none');
            $(ev.currentTarget).closest('.select_button_div').find('.remove_button').css('display', 'none');
            $(ev.currentTarget).closest('.select_button_div').find('.selected_button').css('display', 'none');
            $(ev.currentTarget).closest('.select_button_div').find('.select_button').css('display', 'inline');
            $(ev.currentTarget).closest('.app_card').css({'background-color': '#FFFFFF;', 'border': '1px solid #CCCCC'});
            $(ev.currentTarget).closest('.app_card').css('border', '1px solid #CCCCCC');
            $(ev.currentTarget).closest('.col-8').find('.app_name').css({'color': '#000000;'});          
            $(ev.currentTarget).closest('.col-8').find('.price').css({'color': '#000000;'});
            $(ev.currentTarget).closest('.col-8').find('.span_price').css({'color': '#000000;'});
            var technical_name = $(ev.currentTarget).closest('.app_card').find('.app_tech_name').text();
            $('#'+technical_name).remove();
            $('#'+technical_name+'_node').remove();
            var height = $('#line_complete').css('height');
            height = height.split('p');
            if (height){
                height = parseInt(height[0]);
                height = height - 37;
                $('#line_complete').css('height', height.toString()+'px');
            }
            rpc.query({
                model: 'saas.module',
                method: 'search_read',
                args: [[['technical_name', '=', technical_name]],['price']],
            })
            .then(function(data){
                var price = parseInt(data[0]['price']);
                price = price * number;
                total_app_value_span = total_app_value_span - price;
                final_cost_value_span = total_app_value_span + users_price;
                $('#total_app_value_span').text(total_app_value_span.toString()+' ');
                $('#final_cost_value_span').text(final_cost_value_span.toString()+' ');
                $('#pay_now_value_span').text(final_cost_value_span.toString()+' ');
                apps.splice($.inArray(technical_name, apps), 1);
            });

        },

        _onClickRemoveAppButton : function(ev){
            var total_count = $('#total_apps_count').text();
            total_count = parseInt(total_count);
            total_count = total_count - 1;
            if (total_count < 10){ 
                $('#total_apps_count').text('0'+total_count.toString());
            }else{
                $('#total_apps_count').text(total_count.toString());
            }
            var technical_name = $(ev.currentTarget).closest('.apps_name_head').attr('id');
            $('#'+technical_name+'_node').remove();
            $('#'+technical_name).remove();
            $('#'+technical_name+'_main').find();
            $('#'+technical_name+'_main').find('.selected_button').css('display', 'none');
            $('#'+technical_name+'_main').find('.remove_button').css('display', 'none');
            $('#'+technical_name+'_main').find('.selected_button').css('display', 'none');
            $('#'+technical_name+'_main').find('.select_button').css('display', 'inline');
            $('#'+technical_name+'_main').css({'background-color': '#FFFFFF;', 'border': '1px solid #CCCCC'});
            $('#'+technical_name+'_main').css('border', '1px solid #CCCCCC');
            $('#'+technical_name+'_main').find('.app_name').css({'color': '#000000;'});
            $('#'+technical_name+'_main').find('.price').css({'color': '#000000;'});
            $('#'+technical_name+'_main').find('.span_price').css({'color': '#000000;'});
            var height = $('#line_complete').css('height');
            height = height.split('p');
            if (height){
                height = parseInt(height[0]);
                height = height - 37;
                $('#line_complete').css('height', height.toString()+'px');
            }
            rpc.query({
                model: 'saas.module',
                method: 'search_read',
                args: [[['technical_name', '=', technical_name]],['price']],
            })
            .then(function(data){
                var price = parseInt(data[0]['price']);
                price = price * number;
                total_app_value_span = total_app_value_span - price;
                final_cost_value_span = total_app_value_span + users_price;
                $('#total_app_value_span').text(total_app_value_span.toString()+' ');
                $('#final_cost_value_span').text(final_cost_value_span.toString()+' ');
                $('#pay_now_value_span').text(final_cost_value_span.toString()+' ');
                apps.splice($.inArray(technical_name, apps), 1);
            });
        },

        _onClickMoreApps : function(ev){
            $('#apps_details').attr('style', 'visiblity: hidden');
            $('#apps_details').attr('style', 'height: 0px');
            $('#apps_complete_details').attr('style', 'visiblity: visible');
            $('#apps_complete_details').attr('style', 'height: auto');
        },
        
        _onChangeUsers : function(e){
            var users = $('#number_of_users').val();
            rpc.query({
                model: 'saas.odoo.version',
                method: 'get_default_saas_values',
                args: ['call'],
            })
            .then(function(data){
                var user_cost = data['user_cost'];
                users_price = users * user_cost;
                var costing_nature = data['costing_nature'];                
                if (costing_nature == 'per_user'){
                    // $('#app_cost_number').text(users.toString());
                    var app_cost = parseInt($('#app_cost').text());
                    var total = app_cost * users;
                    total_app_value_span = total_app_value_span + total;
                    $('#app_total_cost').text(total.toString());
                }
                $('#user_price_span').text(user_cost.toString());
                $('#total_users_value_span').text(users_price.toString()+' ');
                final_cost_value_span = users_price + total_app_value_span;
                $('#final_cost_value_span').text(final_cost_value_span.toString()+' ');
                $('#pay_now_value_span').text(final_cost_value_span.toString()+' ');
            });            
        },

        _onClickBuyNow : function(ev){
            var billing_type = $('#dropdownmenu3').text().trim();
            if (! billing_type){
                alert("Please select Billing Cycle");
                return;
            }
            if (apps.length == 0){
                alert("Please select Atleast one App..");
                return;
            }
            var recurring_interval = 0;
            if (billing_type == 'Monthly'){
                recurring_interval = 1;
            }
            else{
                recurring_interval = 12;
            }
            var users = $('#number_of_users');
            var version_name = $('#dropdownmenu2').attr('data-code');
            var number_of_users = parseInt(users.val());
            if (users.length && ! number_of_users){
                alert('Please Enter User to Continue');                
            }
            rpc.query({
                model: 'saas.odoo.version',
                method: 'get_default_saas_values',
                args: ['call'],
            })
            .then(function(data){
                var user_cost = data['user_cost'];
                var total_cost = total_app_value_span;
                user_cost = user_cost * number_of_users * number;
                ajax.jsonRpc("/saas/add/plan", 'call', {
                    'apps': apps,
                    'saas_users': number_of_users,
                    'version_name': version_name,
                    'total_cost': total_cost,
                    'users_cost': user_cost,
                    'recurring_interval' : recurring_interval,
                }).then(function(a){
                    location.href='/shop/cart';
                });    
            });
        },
    });
        
});
