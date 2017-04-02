odoo.define('website_forum.share', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var base = require('web_editor.base');
var SocialShare = require('website.share');
var website = require('website.website');
var qweb = core.qweb;
ajax.loadXML('/website_forum/static/src/xml/website_forum_share_templates.xml', qweb);


if(!$('.website_forum').length) {
    return $.Deferred().reject("DOM doesn't contain '.website_forum'");
}


var ForumShare = SocialShare.extend({
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
        ajax.jsonRpc('/forum/post/bump', 'call', {
            'post_id': this.element.data('id'),
        });
    }
});

base.ready().done(function() {

    // Store social share data to display modal on next page
    $(document.body).on('click', ':not(.karma_required).oe_social_share_call', function() {
        var social_data = {};
        social_data['target_type'] = $(this).data('social-target-type');
        sessionStorage.setItem('social_share', JSON.stringify(social_data));
    });

    // Retrieve stored social data
    if(sessionStorage.getItem('social_share')){
        var social_data = JSON.parse(sessionStorage.getItem('social_share'));
        new ForumShare($(this), social_data['target_type']);
        sessionStorage.removeItem('social_share');
    }

    // Display an alert if post has no reply and is older than 10 days
    if ($('.oe_js_bump').length) {
        var $question_container = $('.oe_js_bump');
        new ForumShare($question_container, 'social-alert');
    }

});
return {};

});
