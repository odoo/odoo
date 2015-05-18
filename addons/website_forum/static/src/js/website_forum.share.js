(function () {
    'use strict';

    openerp.website.if_dom_contains('.website_forum', function () {

        var website = openerp.website;
        var qweb = openerp.qweb;

        website.add_template_file('/website_forum/static/src/xml/website_forum_share_templates.xml');

        website.forum_share = website.social_share.extend({
            init: function (parent, target_type) {
                this.target_type = target_type;
                this._super(parent);
            },
            bind_events: function () {
                this._super.apply(this, arguments);
                $('.oe_share_bump').click($.proxy(this.post_bump, this));
            },
            renderElement: function () {
                if (! this.target_type) {
                    this._super();
                }
                else if (this.target_type == 'social-alert') {
                    $('.row .question').before(qweb.render('website.social_alert', {medias: this.social_list}));
                }
                else {
                    this.template = 'website.social_modal';
                    $('body').append(qweb.render(this.template, {medias: this.social_list, target_type: this.target_type}));
                    $('#oe_social_share_modal').modal('show');
                }
            },
            post_bump: function () {
                openerp.jsonRpc('/forum/post/bump', 'call', {
                    'post_id': this.element.data('id'),
                });
            }
        });

        website.ready().done(function() {

            // Store social share data to display modal on next page
            $(document.body).on('click', ':not(.karma_required).oe_social_share_call', function() {
                var social_data = {};
                social_data['target_type'] = $(this).data('social-target-type');
                sessionStorage.setItem('social_share', JSON.stringify(social_data));
            });

            // Retrieve stored social data
            if(sessionStorage.getItem('social_share')){
                var social_data = JSON.parse(sessionStorage.getItem('social_share'));
                new website.forum_share($(this), social_data['target_type']);
                sessionStorage.removeItem('social_share');
            }

            // Display an alert if post has no reply and is older than 10 days
            if ($('.oe_js_bump').length) {
                var $question_container = $('.oe_js_bump');
                new website.forum_share($question_container, 'social-alert');
            }
        });
    });
})();
