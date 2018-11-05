odoo.define('website_slides.slides_like', function (require) {
'use strict';

var core = require('web.core');
var Widget = require('web.Widget');
var localStorage = require('web.local_storage');
var sAnimations = require('website.content.snippets.animation');
require('website_slides.slides');

var _t = core._t;

var LikeButton = Widget.extend({
    events: {
        'click': '_onClick',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} ev
     */
    _applyAction: function (ev) {
        var button = $(ev.currentTarget);
        var slideID = button.data('slide-id');
        var userID = button.data('user-id');
        var isPublic = button.data('public-user');
        var href = button.data('href');
        if (isPublic) {
            this._popoverAlert(button, _.str.sprintf(_t('Please <a href="/web?redirect=%s">login</a> to vote this slide'), (document.URL)));
        } else {
            var target = button.find('.fa');
            if (localStorage.getItem('slide_vote_' + slideID) !== userID.toString()) {
                this._rpc({
                    route: href,
                    params: {
                        slide_id: slideID,
                    },
                }).then(function (data) {
                    target.text(data);
                    localStorage.setItem('slide_vote_' + slideID, userID);
                });
            } else {
                this._popoverAlert(button, _t('You have already voted for this slide'));
            }
        }
    },
    /**
     * @private
     * @param {Object} $el
     * @param {String} message
     */
    _popoverAlert: function ($el, message) {
        $el.popover({
            trigger: 'focus',
            placement: 'bottom',
            container: 'body',
            html: true,
            content: function () {
                return message;
            }
        }).popover('show');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClick: function () {
        this._applyAction();
    },
});

sAnimations.registry.websiteSlidesLike = sAnimations.Class.extend({
    selector: '#wrapwrap',

    /**
     * @override
     * @param {Object} parent
     */
    start: function (parent) {
        var defs = [this._super.apply(this, arguments)];
        defs.push(new LikeButton(this).attachTo($('.oe_slide_js_like')));
        defs.push(new LikeButton(this).attachTo($('.oe_slide_js_unlike')));
        return $.when.apply($, defs);
    },
});
});
