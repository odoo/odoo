odoo.define('odoo_saas_kit.subdomain_page', function(require) {
    "use strict";

    var rpc = require('web.rpc');
    var ajax = require('web.ajax');

    $(document).ready(function() {

        $('.get_subdomain_email').click(function() {
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
        $('.confirm_domain').click(function(){
            var subdomain_name = $("#subdomain_name").val();
            var contract_id = $("#contract_id").attr('value');
            if(subdomain_name.length == 0)
                $("#subdomain_name").css("border", "1px solid #ff1414")
            else{
                var domain_name = subdomain_name
                $.blockUI({ 
                    message: '<h1 style="color: #c9d0d6;"><i class="fa fa-spinner fa-spin" style="font-size:24px"></i>Please wait!</h1><center><p style="color: #f0f8ff;">We are creating your SaaS Instance.</p></center></div>',
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
                        location.href='/client/domain-created/redirect?contract_id='+contract_id
             //           window.open(return_dict.url, "_self");
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

        $('.go_to_account').click(function(ev){
            var contract_id = $(ev.currentTarget).val();
            rpc.query({
                model: 'saas.contract',
                method: 'redirect_invitation_url',
                args: [contract_id],
            })
            .then(function(url){
                console.log(url);
                location.href=url;
            });
        });
        $('.instance_login').click(function(ev){
            var client_id = parseInt($('.instance_login').attr('client_id'));
            rpc.query({
                model: 'saas.client',
                method: 'read',
                args: [[client_id], ['client_url']],
            }).then(function(url){
                location.href = url[0]['client_url'];
            });
        });

        $('.revoke_domain').click(function(ev){
            var answer = confirm("Are You Sure You want to Revoke this domain..?");
            if (answer == true){
                var domain_id = parseInt($(ev.currentTarget).attr('domain_id'));
                rpc.query({
                    model: 'custom.domain',
                    method: 'revoke_subdomain_call',
                    args: [domain_id],
                }).then(function(url){
                    location.href = url
                });
            }
        });
    });
});