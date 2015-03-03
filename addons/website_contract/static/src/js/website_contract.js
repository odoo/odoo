(function () {
    'use strict';

    var website = openerp.website;
    var qweb = openerp.qweb;
    website.add_template_file('/website_contract/static/src/xml/website_contract.modals.xml');
    website.ready().done(function() {

        $('.contract-submit').off('click').on('click', function () {
            $(this).closest('form').submit();
        });

        $('.wc-remove-option,.wc-add-option').off('click').on('click', function() {
            console.log("prout");
            var data = {};
            data.option_name = $(this).parent().siblings('.line-description').html();
            data.option_id = $(this).data('option-id');
            data.option_price = $(this).data('option-subtotal');
            data.account_id = $('#wrap').data('account-id');
            data.next_date = $('#wc-next-invoice').html();
            console.log(data);
            var template = 'website_contract.modal_'+$(this).data('target');

            $('#wc-modal-confirm .modal-content').html(qweb.render(template, {data: data}));

            $('#wc-modal-confirm').modal();
        });

        $('#wc-close-account').off('click').on('click', function() {
            console.log('plop');
            var data = {};
            data.account_id = $('#wrap').data('account-id');
            data.next_date = $('#wc-next-invoice').html();
            var template = 'website_contract.modal_close';

            $('#wc-modal-confirm .modal-content').html(qweb.render(template, {data: data}));

            $('#wc-modal-confirm').modal();
        });

    });

})();