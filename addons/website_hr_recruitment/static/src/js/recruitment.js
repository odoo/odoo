$(function () {
    $(document).on('click', 'button[name=subscribe]', function (e) {
        div = $(this).parent();
        parent = $(this).parent().parent();
        id = $(this).parent().parent().attr('id');
        email = $(this).siblings('div').find('input[name=email]').val();
        openerp.jsonRpc('/recruitment/message_get_subscribed', 'call', {'email': email, 'id': id}).then(function (result) {
            if (result == 1) {
                div.hide();
                parent.find('.hidden').find('input[type=hidden]').val(email);
                parent.find('.hidden').removeClass('hidden');
            }
        });
    });
    $(document).on('click', 'button[name=unsubscribe]', function (e) {
        div = $(this).parent();
        parent = $(this).parent().parent();
        id = $(this).parent().parent().attr('id');
        openerp.jsonRpc('/recruitment/message_get_unsubscribed', 'call', {'email': $(this).siblings('input[name=email]').val(), 'id': id}).then(function (result) {
            if (result == 1) {
                parent.find('.subscribedetails').show();
                div.addClass('hidden');
            }
        });
    });
});
