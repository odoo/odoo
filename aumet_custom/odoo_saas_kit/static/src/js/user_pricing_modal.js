odoo.define('odoo_saas_kit.user_pricing_modal', function(require){
    "use strict";
    
    var rpc = require('web.rpc');
    $('document').ready(function(){
        $('#modal_target').click(function(){
            var min_users = parseInt($('#min_user')).text;
            $('#new_min_user').attr('value',min_users);
            var product_id = parseInt($('.product_id').attr('value'));
            min_users = $('#new_min_user').val()
            $('#total_cost').text('');                
            rpc.query({
                model: 'product.product',
                method: 'read',
                args: [[product_id],['user_cost']],
            })
            .then(function(data){
                var total_amount = min_users * (parseInt(data[0]['user_cost']));
                $('#total_cost').text(total_amount);
                $("#modify_min_users").modal("toggle");
            });            
        });

        $('#new_min_user').change(function(){
            var min_users = parseInt($('#min_user_quantity').attr('value'));
            var max_users = parseInt($('#max_user_quantity').attr('value'));
            var new_user = parseInt($('#new_min_user').val());
            var product_id = parseInt($('.product_id').attr('value'));
            if (new_user < min_users){
                alert("User must me more than or equal to "+ min_users);
            }
            else if(new_user > max_users){
                alert("User must me less than or equal to "+ max_users);
            }else{
                rpc.query({
                    model: 'product.product',
                    method: 'read',
                    args: [[product_id],['user_cost']],
                })
                .then(function(data){
                    var total_amount = new_user * parseFloat(data[0]['user_cost']);
                    $('#total_cost').text(total_amount);
                });
            }
        });

        $('#min_user_submit').click(function(){
            var min_users = parseInt($('#min_user_quantity').attr('value'));
            var max_users = parseInt($('#max_user_quantity').attr('value'));
            var new_user = parseInt($('#new_min_user').val());
            if (new_user < min_users){
                alert("User must me more than or equal to "+ min_users);
            }
            else if(new_user > max_users){
                alert("User must me less than or equal to "+ max_users);
            }else{
                $('#min_user').text(new_user);
                $('#number_of_user').attr('value',new_user);
                $('#modify_min_users').modal('hide');
            }
        });
    });
});