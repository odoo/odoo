odoo.define('website_forum.share', function (require) {
'use strict';

var sAnimations = require('website.content.snippets.animation');
var core = require('web.core');
var qweb = core.qweb;

var ForumShare = sAnimations.registry.socialShare.extend({
    xmlDependencies: sAnimations.registry.socialShare.prototype.xmlDependencies
        .concat(['/website_forum/static/src/xml/website_forum_share_templates.xml']),

    /**
     * @override
     * @param {Object} parent
     * @param {Boolean} editableMode
     * @param {String} targetType
     */
    init: function (parent, editableMode, targetType) {
        this._super.apply(this, arguments);
        this.targetType = targetType;
    },
    /**
     * @override
     * @param {Object} parent
     */
    start: function (parent) {
        var def = this._super.apply(this, arguments);
        this._onMouseEnter();
        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _bindSocialEvent: function () {
        this._super.apply(this, arguments);
        $('.oe_share_bump').click($.proxy(this._postBump, this));
    },
    /**
     * @private
     */
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
    /**
     * @private
     */
    _postBump: function () {
        this._rpc({ // FIXME
            route: '/forum/post/bump',
            params: {
                post_id: this.element.data('id'),
            },
        });
    },

});

sAnimations.registry.websiteForumShare = sAnimations.Class.extend({
    selector: '.website_forum',
    read_events: {
        'click :not(.karma_required).oe_social_share_call': '_onBody'
    },

    /**
     * @override
     * @param {Object} parent
     */
    start: function (parent) {
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
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Store social share data to display modal on next page
     *
     * @override
     */
    _onBody: function () {
        sessionStorage.setItem('social_share', JSON.stringify({
            targetType: $(this).data('social-target-type'),
        }));
    },

});

});
