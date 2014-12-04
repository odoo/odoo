(function () {
    'use strict';

    var _t = openerp._t;
    var website = openerp.website;
    var qweb = openerp.qweb;
    website.add_template_file('/website_forum/static/src/xml/website_forum.share_templates.xml');

    website.ready().done(function() {
        if (Date.now()-Date.parse($('.question').attr('data-last-update')) > 864*10e5 && (openerp.get_cookie('session_id'))) { //If the question is older than 864*10e5 seconds (=10 days)
            var hashtag_list = ['question'];
            var social_list = ['facebook','twitter', 'linkedin', 'google-plus'];
            new website.social_share('social_alert',$(this), social_list, hashtag_list);
            $('.share').on('click', $.proxy(updateDateWrite));
        }
        function updateDateWrite() {
            var model = $('.question').attr('data-model');
            var record_id = parseInt($('.question').attr('data-id'));
            var Post = new openerp.Model(model);
            Post._session = new openerp.Session;
            Post._session['session_id'] = openerp.get_cookie('session_id');
            Post.call('update_write_date',[[record_id],website.get_context()]).then(function(result) {console.log(record_id);});

        };
    });
})();
