$(document).ready(function () {

    /* Hitting the payment button: payment transaction process begins
     * We redirect the user to a custom shop page in oder to create the
     * transaction. The form POST data will be used to perform the post
     * query.
     */
    $('input#payment_submit').on('click', function (ev) {  // TDEFIXME: change input#ID to input inside payment form, less strict
        var acquirer_id = $(this).closest('form').closest('div').data().id || 0;
        var form_action = $(this).closest("form").attr('action');
        console.log('cliking on submit for payment - redirecting from', form_action, 'to shop with acqurier_id', acquirer_id);
        $(this).closest("form").attr("action", '/shop/payment/transaction/' + acquirer_id + '/');
    });
});
