$(function () {
    $(document).on('click', 'button[name=subscribe]', function (e) {
        var div = $(this).parent();
        var parent = $(this).parent().parent();
        var groupid = $(this).siblings('input[name=group_id]').val();
        var id = $(this).parent().parent().attr('id');
        var email = $(this).siblings('div').find('input[name=email]').val();
        if (!email) return;
        openerp.jsonRpc('/recruitment/message_get_subscribed', 'call', {'email': email, 'id': id, 'mail_group_id': groupid}).then(function (result) {
            if (result == 1) {
                div.removeClass('show').addClass('hidden');
                parent.find('div:gt(0)').find('input[type=hidden][name=email]').val(email);
                parent.find('div:gt(0)').removeClass('hidden');
            }
        });
       
        // $(this).siblings('div').find('input[name=email]').attr("value", "");
    });
    $(document).on('click', 'button[name=unsubscribe]', function (e) {
        var div = $(this).parent();
        var parent = $(this).parent().parent();
        var id = $(this).parent().parent().attr('id');
        var groupid = $(this).siblings('input[name=group_id]').val();

        openerp.jsonRpc('/recruitment/message_get_unsubscribed', 'call', {'email': $(this).siblings('input[name=email]').val(), 'id': id, 'mail_group_id': groupid}).then(function (result) {
            if (result == 1) {
                parent.find('div:first').removeClass('hidden').addClass('show');
                div.addClass('hidden');
            }
        });
    });
    $(document).on('click', '.js_publish', function (e) {
        var id = $(this).data('id');
        var row = $(this).parents().find('tr#'+id);
        var counting = row.find('td:first').find('span#counting');
        var msg = row.find('td:first').find('span#norecruit');
        var div = row.find('td:first').find('div#'+id+' div:first');
        var job_post = row.find('td:first').find('span#job_post');
        var no_job_post = row.find('td:first').find('span#no_job_post');

        var loadpublish = function () {
            return openerp.jsonRpc('/recruitment/published', 'call', {'id': id}).then(function (result) {
                if (result['published']) {
                    msg.addClass('hidden');
                    counting.removeClass('hidden');
                    counting.find('span#counting_num').html(result['count']);
                    div.addClass('hidden');
                } else {
                    msg.removeClass('hidden');
                    counting.addClass('hidden');
                    div.removeClass('hidden');
                }
            });
        }
        var i = 0;
        $(this).ajaxComplete(function(el, xhr, settings) {
            if (settings.url == "/website/publish") {
                i++;
                if (i == 1)
                    settings.jsonpCallback = loadpublish()
            }
        });
    });
});