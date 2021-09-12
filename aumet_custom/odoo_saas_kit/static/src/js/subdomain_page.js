odoo.define('odoo_saas_kit.subdomain_page', function(require) {
    "use strict";

    var rpc = require('web.rpc');
    var ajax = require('web.ajax');

    $(document).ready(function() {

        $('.o_portal_wrap').each(function() {
            var o_portal_wrap = this;
            $(o_portal_wrap).on('click', '.get_subdomain_email', function() {
                var contract_id = $("#contract_id").attr('value');
                rpc.query({
                    model: 'saas.contract',
                    method: 'get_subdomain_email',
                    args: [contract_id],
                })
                .then(function(){
                    console.log("--Email sent--")
                });
            });
            $(o_portal_wrap).on('click', '.confirm_domain', function(){
                var subdomain_name = $("#subdomain_name").val();
                var contract_id = $("#contract_id").attr('value');
                if(subdomain_name.length == 0)
                    $("#subdomain_name").css("border", "1px solid #ff1414")
                else{
                    var domain_name = subdomain_name
                    $.blockUI({ 
                        message: '<h1 style="color: #c9d0d6;"><i class="fa fa-spinner fa-spin" style="font-size:24px"></i>Please wait!</h1><center><p style="color: #f0f8ff;">We are creating the your SaaS Instance.</p></center></div>',
                        css: {
                            'z-index': '1011',
                            'position': 'fixed',
                            'padding': '0px',
                            'margin': '0px',
                            'width': '30%',
                            'top': '46%',
                            'left': '35%',
                            'text-align': 'center',
                            'color': 'rgb(0, 0, 0)',
                            'cursor': 'wait',
                            'border': 'none',
                            'background-color': 'rgba(255, 255, 255, 0)',
                        }
                    });
                    ajax.jsonRpc("/mail/confirm_domain", 'call', {
                        'domain_name': domain_name,
                        'contract_id': contract_id
                    }).then(function (return_dict) {
                        $.unblockUI();
                        if(return_dict.status == 1){
                            $("#taken_warning").show();
    
                        }else if(return_dict.status == 2){
                            $("#taken_warning").hide();
                            // window.close();
                            location.href='/client/domain-created/redirect'
                            // window.open(return_dict.url, "_self");
                        }
                        else{
                            $("#taken_warning").hide();
                            $("#status_link").show();
                        }
                    });
                }
            });
            $('form').on('keyup keypress', function(e) {
                var keyCode = e.keyCode || e.which;
                if (keyCode === 13) { 
                    e.preventDefault();
                    return false;
                }
            });
        });
    });
});