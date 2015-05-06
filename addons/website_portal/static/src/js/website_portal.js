(function () {
    'use strict';

    var website = openerp.website;
    var qweb = openerp.qweb;
    website.ready().done(function() {

        // Address validation using USPS
        var $form = $('#wp-contact-form');
        var validate = $('#wp-contact-form').data('validate') == 'True';
        var mandatory_validation = $form.data('mandatory-valdiation') == 'True';
        
        $("[data-toggle=popover]").popover({html: true, placement: 'top',});

        $('.oe_website_portal').on('change', "select[name='country_id']", function () {
            if (validate && $(this).children(':selected').data('validate')=='True') {
                $('#wp-contact-validate').removeClass('hidden');
                $('#wp-contact-submit').attr('disabled','disabled');
            } else {
                $('#wp-contact-validate').addClass('hidden');
                $('#wp-contact-submit').removeAttr('disabled');
            }
        });

        $form.find('input[name="street2"],input[name="city"],input[name="zipcode"],select[name="state_id"]').on('change', function(ev) {
            if (mandatory_validation) {
                $('#wp-contact-submit').attr('disabled','disabled');
            }
        })
        $('#wp-contact-validate').on('click', function(ev) {
            var need_validation = $form.find("select[name='country_id']").children(':selected').data('validate')=='True';
            

            if (validate && need_validation) {
                validate_address(ev);
            }
        });

        function validate_address(ev){
            var popover = $('#wp-contact-validate').data('bs.popover');
            popover.options.content = "<i class='fa fa-refresh fa-spin'></i> Checking";
            ev.preventDefault();
            popover.show();

            var action = $form.data('validate-action');
            var object= {"jsonrpc": "2.0",
                         "method": "call",
                          "params": getFormData($form),
                          "id": null};
            openerp.jsonRpc(action, 'call', object).then(function (data) {
                if (!data.Error) {
                    popover.options.content = "<i class='fa fa-check'></i> Address is Valid";
                    $form.find('input[name="city"]').val(data.city);
                    $form.find('input[name="street2"]').val(data.street);
                    $form.find('input[name="zipcode"]').val(data.zip);
                    $form.find('option[data-state-code="'+data.state+'"]').attr('selected','selected');
                    if (mandatory_validation) {
                        $('#wp-contact-submit').removeAttr('disabled');
                    }
                } else {
                    popover.options.content = "<i class='fa fa-exclamation'></i> "+data.Error;
                    if (mandatory_validation) {
                        $('#wp-contact-submit').attr('disabled','disabled');
                    }
                }
                popover.show();

            });
        }

        function getFormData($form){
            var unindexed_array = $form.serializeArray();
            var indexed_array = {};

            $.map(unindexed_array, function(n, i){
                indexed_array[n['name']] = n['value'];
            });

            return indexed_array;
        };

        $('.oe_website_portal').on('change', "select[name='country_id']", function () {
            var $select = $("select[name='state_id']");
            $select.find("option:not(:first)").hide();
            var nb = $select.find("option[data-country_id="+($(this).val() || 0)+"]").show().size();
            $select.parent().toggle(nb>1);
        });
        $('.oe_website_portal').find("select[name='country_id']").change();

        $('.wp_show_more').on('click', function(ev) {
            ev.preventDefault();
            $(this).parents('table').find(".to_hide").toggleClass('hidden');
            $(this).find('span').toggleClass('hidden');
        });

        
    });

})();