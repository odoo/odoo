/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

odoo.define('saas_kit_custom_plan.update_app', function (require) {
    var rpc = require('web.rpc');
    $('document').ready(function(){
        $('#modal_for_apps').click(function(){
            var contract_id = parseInt($('#add_apps_submit').attr('value'));
            rpc.query({
                model: 'saas.contract',
                method: 'get_module',
                args: ['', contract_id],
            })
            .then(function(data){
                if (data){
                    $("#add_apps").modal("toggle");
                }
            });
        });

        $('#add_apps_submit').click(function(){
            var checkbox = $('input:checkbox:checked');
            if (checkbox.length == 0){
                alert('Please Select Atleast One App to continue !')
                return
            }
            var contract_id = parseInt($('#add_apps_submit').attr('value'));
            var apps = new Array();
            checkbox.each(function(i, el){
                console.log($(this).parent().parent().parent().children('.product_div'));
                apps.push($(this).parent().parent().parent().children('.product_div').children('.product_name').attr('data-value'));
            });
            rpc.query({
                model: 'saas.contract',
                method: 'add_apps',
                args: ['', apps, contract_id],
            })
            .then(function(data){
                $('#add_apps').modal('hide');
                $('input:checkbox').removeAttr('checked');
                location.href='/my/saas/contract/'+contract_id+'?access_token='+data
            });
        });
    });
});
