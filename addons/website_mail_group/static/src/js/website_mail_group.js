$(document).ready(function () {
    $('a.js_group').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var href = $link.attr("href");
        var group_id = href.match(/subscription\/([0-9]+)/)[1];
        var action = href.match(/action=(.*)/)[1] == 'subscribe' ? true : false;
        openerp.jsonRpc("/groups/subscription/", 'call', {
                    'group_id': parseInt(group_id),
                    'action' : action,
                })
                .then(function (data) {
                    if(data[0])
                        return window.location ='/web/login?redirect=/groups/';
                    if (action){
                        $('li#'+ group_id).toggleClass('hidden visible');
                        $('.unfollow_' + group_id).toggleClass('visible hidden');
                        $('.follow_' + group_id).toggleClass('hidden visible');
                    }
                    else {
                        $('li#'+ group_id).toggleClass('visible hidden');
                        $('.unfollow_' + group_id).toggleClass('hidden visible');
                        $('.follow_' + group_id).toggleClass('visible hidden');
                    }
                });
        return false;
    });
});
