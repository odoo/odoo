odoo.define('website_forum.share', function (require) {
'use strict';

var core = require('web.core');
var publicWidget = require('web.public.widget');
require('website.content.snippets.animation');

var qweb = core.qweb;

// FIXME There is no reason to inherit from socialShare here
var ForumShare = publicWidget.registry.socialShare.extend({
    selector: '',
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
        this.socialAlertEl = null;
        this.socialModalEl = null;
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
        var questionEl = this.el.querySelector('article.question');
        const parser = new DOMParser();
        if (!this.targetType) {
            this._super.apply(this, arguments);
        } else if (this.targetType === 'social-alert') {
            this.socialAlertEl = parser.parseFromString(
                qweb.render('website.social_alert',{
                    medias: this.socialList
                }), "text/html").body.firstChild;
            questionEl.insertBefore(this.socialAlertEl);
        } else {
            this.socialModalEl = parser.parseFromString(
                qweb.render('website.social_modal', {
                    medias: this.socialList,
                    target_type: this.targetType,
                    state: questionEl.dataset.state,
                }), "text/html").body.firstChild;
            document.querySelector('body').appendChild(this.socialModalEl);
            // TODO in master, remove the modal from the DOM when it is closed.
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
    /**
    * @override
    * TODO remove me in master. This has been introduced as a stable fix to not
    * remove the document body at the `destroy()` of the `ForumShare` public
    * widget.
    *
    * Background: The `ForumShare` public widget is initially attached to the document
    * body upon instantiation, which means its root element (`this.$el`) is set
    * to the document body. Normally, when a widget is destroyed, its root
    * element is removed which, in this case, would result in the document body
    * removal.
    *
    * To prevent this, the fix assigns `null` to the root element before
    * invoking the `destroy()` method, ensuring that the document body remains
    * intact.
    */
    destroy: function () {
        this.setElement(null);
        if (this.socialAlertEl) {
            this.socialAlertEl.remove();
        }
        if (this.socialModalEl) {
            this.socialModalEl.remove();
        }
        this._super();
    },
});

publicWidget.registry.websiteForumShare = publicWidget.Widget.extend({
    selector: '.website_forum',

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
});
});
