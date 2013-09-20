$(function () {
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