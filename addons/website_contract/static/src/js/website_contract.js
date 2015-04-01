(function () {
    'use strict';

    var website = openerp.website;
    var qweb = openerp.qweb;
    website.ready().done(function() {

        $('.contract-submit').off('click').on('click', function () {
            $(this).closest('form').submit();
        });

        var $new_payment_method = $('div[id="new_payment_method"]');
        $('#wc-payment-form select[name="pay_meth"]').change(function() {
            var $form = $(this).parents('form');
            if ($(this).val() == -1) {
                $new_payment_method.removeClass('hidden');
                $form.find('button').addClass('hidden');
            } else {
                $new_payment_method.addClass('hidden');
                $form.find('button').removeClass('hidden');
            }

        });

        // When creating new pay method: create by json-rpc then continue with the new id in the form
        $new_payment_method.on("click", 'button[type="submit"],button[name="submit"]', function (ev) {
          ev.preventDefault();
          ev.stopPropagation();
          var $form = $(ev.currentTarget).parents('form');
          var $main_form = $('#wc-payment-form');
          var action = $form.attr('action');
          var object= {"jsonrpc": "2.0",
                       "method": "call",
                        "params": getFormData($form),
                        "id": null};
          openerp.jsonRpc(action, 'call', object).then(function (data) {
            $main_form.find('select option[value="-1"]').val(data[0]);
            $main_form.find('select').val(data[0]);
            $main_form.submit();
          });
        });

        function getFormData($form){
            var unindexed_array = $form.serializeArray();
            var indexed_array = {};

            $.map(unindexed_array, function(n, i){
                indexed_array[n['name']] = n['value'];
            });

            return indexed_array;
        };

    });

})();
