odoo.define('website_forum.share', function (require) {
'use strict';

var core = require('web.core');
var publicWidget = require('web.public.widget');

var qweb = core.qweb;

// FIXME There is no reason to inherit from socialShare here
var ForumShare = publicWidget.registry.socialShare.extend({
    selector: '',
    xmlDependencies: publicWidget.registry.socialShare.prototype.xmlDependencies
        .concat(['/website_forum/static/src/xml/website_forum_share_templates.xml']),
    events: {},

    /**
     * @override
     * @param {Object} parent
     * @param {Object} options
     * @param {string} targetType
     */
    init: function (parent, options, targetType) {
        this._super.apply(this, arguments);
        this.targetType = targetType;
    },
    /**
     * @override
     */
    start: function () {
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

publicWidget.registry.websiteForumShare = publicWidget.Widget.extend({
    selector: '.website_forum',
    events: {
        'click :not(.karma_required).oe_social_share_call': '_onShareCallClick',
    },

    /**
     * @override
     */
    start: function () {
        // Retrieve stored social data
        if (sessionStorage.getItem('social_share')) {
            var socialData = JSON.parse(sessionStorage.getItem('social_share'));
            (new ForumShare(this, false, socialData.targetType)).attachTo($(document.body));
            sessionStorage.removeItem('social_share');
        }
        // Display an alert if post has no reply and is older than 10 days
        var $questionContainer = $('.oe_js_bump');
        if ($questionContainer.length) {
            new ForumShare(this, false, 'social-alert').attachTo($questionContainer);
        }

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Stores social share data to display modal on next page.
     *
     * @private
     */
    _onShareCallClick: function (ev) {
        sessionStorage.setItem('social_share', JSON.stringify({
            targetType: $(ev.currentTarget).data('social-target-type'),
        }));
    },
});
});
