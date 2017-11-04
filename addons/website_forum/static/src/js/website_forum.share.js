odoo.define('website_forum.share', function (require) {
'use strict';

require('web.dom_ready');
var core = require('web.core');
var base = require('web_editor.base');
var sAnimation = require('website.content.snippets.animation');

var qweb = core.qweb;

if (!$('.website_forum').length) {
    return $.Deferred().reject("DOM doesn't contain '.website_forum'");
}

// FIXME There is no reason to inherit from socialShare here
var ForumShare = sAnimation.registry.socialShare.extend({
    xmlDependencies: sAnimation.registry.socialShare.prototype.xmlDependencies
        .concat(['/website_forum/static/src/xml/website_forum_share_templates.xml']),
    read_events: {},

    init: function (parent, editableMode, targetType) {
        this._super.apply(this, arguments);
        this.targetType = targetType;
    },
    start: function () {
        var def = this._super.apply(this, arguments);
        this._onMouseEnter();
        return def;
    },
    _bindSocialEvent: function () {
        this._super.apply(this, arguments);
        $('.oe_share_bump').click($.proxy(this._postBump, this));
    },
    _render: function () {
        if (!this.targetType) {
            this._super.apply(this, arguments);
        } else if (this.targetType === 'social-alert') {
            $('.row .question').before(qweb.render('website.social_alert', {medias: this.socialList}));
        } else {
            $('body').append(qweb.render('website.social_modal', {medias: this.socialList, target_type: this.targetType}));
            $('#oe_social_share_modal').modal('show');
        }
    },
    _postBump: function () {
        this._rpc({ // FIXME
            route: '/forum/post/bump',
            params: {
                post_id: this.element.data('id'),
            },
        });
    },
});

base.ready().then(function () {
    // Store social share data to display modal on next page
    $(document.body).on('click', ':not(.karma_required).oe_social_share_call', function () {
        sessionStorage.setItem('social_share', JSON.stringify({
            targetType: $(this).data('social-target-type'),
        }));
    });

    // Retrieve stored social data
    if (sessionStorage.getItem('social_share')) {
        var socialData = JSON.parse(sessionStorage.getItem('social_share'));
        (new ForumShare(null, false, socialData.targetType)).attachTo($(document.body));
        sessionStorage.removeItem('social_share');
    }

    // Display an alert if post has no reply and is older than 10 days
    var $questionContainer = $('.oe_js_bump');
    if ($questionContainer.length) {
        new ForumShare(null, false, 'social-alert').attachTo($questionContainer);
    }
});
});
