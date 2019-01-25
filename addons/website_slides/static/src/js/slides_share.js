odoo.define('website_slides.slides_share', function (require) {
'use strict';

var Widget = require('web.Widget');
var sAnimations = require('website.content.snippets.animation');
require('website_slides.slides');

var ShareMail = Widget.extend({
    events: {
        'click button': '_sendMail',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _sendMail: function () {
        var self = this;
        var input = this.$('input');
        var slideID = this.$('button').data('slide-id');
        if (input.val() && input[0].checkValidity()) {
            this.$el.removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');
            this._rpc({
                route: '/slides/slide/send_share_email',
                params: {
                    slide_id: slideID,
                    email: input.val(),
                },
            }).then(function () {
                self.$el.html($('<div class="alert alert-info" role="alert"><strong>Thank you!</strong> Mail has been sent.</div>'));
            });
        } else {
            this.$el.addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
            input.focus();
        }
    },
});

sAnimations.registry.websiteSlidesShare = sAnimations.Class.extend({
    selector: '#wrapwrap',
    read_events: {
        'click a.o_slides_social_share': '_onSlidesSocialShare',
    },

    /**
     * @override
     * @param {Object} parent
     */
    start: function (parent) {
        var self = this;
        var defs = [this._super.apply(this, arguments)];
        defs.push(new ShareMail(this).attachTo($('.oe_slide_js_share_email')));

        if ($('div#statistic').length) {
            var slideURL = $('div#statistic').attr('slide-url');
            var socialURLs = {
                linkedin: 'https://www.linkedin.com/countserv/count/share?url=',
                twitter: 'https://cdn.api.twitter.com/1/urls/count.json?url=',
                facebook: 'https://graph.facebook.com/?id=',
                gplus: 'https://clients6.google.com/rpc',
            };
        }

        _.each(socialURLs, function (value, key) {
            self._updateStatistics(key, slideURL);
        });

        return $.when.apply($, defs);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} socialSite
     * @param {string} slide_url
     */
    _updateStatistics: function (socialSite, slideURL) {
        if (socialSite === 'gplus') {
            $.ajax({
                url: this.social_urls['gplus'],
                type: 'POST',
                dataType: 'json',
                contentType: 'application/json',
                data: JSON.stringify([{
                    method: 'pos.plusones.get',
                    id: 'p',
                    params: {
                        nolog: true,
                        id: slideURL,
                        source: 'widget',
                        userId: '@viewer',
                        groupId: '@self'
                    },
                    // TDE NOTE: should there be a key here ?
                    jsonrpc: '2.0',
                    apiVersion: 'v1'
                }]),
                success: function (data) {
                    $('#google-badge').text(data[0].result.metadata.globalCounts.count || 0);
                    $('#total-share').text(parseInt($('#total-share').text()) + parseInt($('#google-badge').text()));
                },
            });
        } else {
            $.ajax({
                url: this.social_urls[socialSite] + slideURL,
                dataType: 'jsonp',
                success: function (data) {
                    var shareCount = (socialSite === 'facebook' ? data.shares : data.count) || 0;
                    $('#' + socialSite + '-badge').text(shareCount);
                    $('#total-share').text(parseInt($('#total-share').text()) + parseInt($('#' + socialSite + '-badge').text()));
                },
            });
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {Object} ev
     */
    _onSlidesSocialShare: function (ev) {
        ev.preventDefault();
        var key = $(ev.currentTarget).attr('social-key');
        var popUpURL = $(ev.currentTarget).attr('href');
        var popUp = window.open(popUpURL, 'Share Dialog', 'width=626,height=436');
        $(window).on('focus', function () {
            if (popUp.closed) {
                this._updateStatistics(key, this.slide_url);
                $(window).off('focus');
            }
        });
    },
});
});
