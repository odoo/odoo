odoo.define('website_slides.slides_share', function (require) {
"use strict";
var ajax = require('web.ajax');
var Widget = require('web.Widget');
var sAnimations = require('website.content.snippets.animation');
var slides = require('website_slides.slides');

// Send by email Widget
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
        var slide_id = this.$('button').data('slide-id');
        if (input.val() && input[0].checkValidity()){
            this.$el.removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');
            ajax.jsonRpc('/slides/slide/send_share_email', 'call', {
                slide_id: slide_id,
                email: input.val(),
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
    selector: 'main',
    read_events: {
        'click a.o_slides_social_share': '_onSlidesSocialShare'
    },

    /**
     * @override
     * @param {Object} parent
     */
    start: function (parent) {
        var widget_parent = $('body');
        slides.page_widgets['share_mail'] = new ShareMail(widget_parent).setElement($('.oe_slide_js_share_email'));

        if ($('div#statistic').length) {
            var slide_url = $("div#statistic").attr('slide-url');
            var social_urls = {
                'linkedin': 'https://www.linkedin.com/countserv/count/share?url=',
                'twitter': 'https://cdn.api.twitter.com/1/urls/count.json?url=',
                'facebook': 'https://graph.facebook.com/?id=',
                'gplus': 'https://clients6.google.com/rpc'
            };
        }

        $.each(social_urls, function (key, value) {
            this._updateStatistics(key, slide_url);
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} social_site
     * @param {string} slide_url
     */
    _updateStatistics: function (social_site, slide_url) {
        if (social_site === 'gplus') {
            $.ajax({
                url: this.social_urls['gplus'],
                type: "POST",
                dataType: 'json',
                contentType: 'application/json',
                data: JSON.stringify([{
                    "method": "pos.plusones.get",
                    "id": "p",
                    "params": {
                        "nolog": true,
                        "id": slide_url,
                        "source": "widget",
                        "userId": "@viewer",
                        "groupId": "@self"
                    },
                    // TDE NOTE: should there be a key here ?
                    "jsonrpc": "2.0",
                    "apiVersion": "v1"
                }]),
                success: function (data) {
                    $('#google-badge').text(data[0].result.metadata.globalCounts.count || 0);
                    $('#total-share').text(parseInt($('#total-share').text()) + parseInt($('#google-badge').text()));
                },
            });
        } else {
            $.ajax({
                url: this.social_urls[social_site] + slide_url,
                dataType: 'jsonp',
                success: function (data) {
                    var shareCount = (social_site === 'facebook' ? data.shares : data.count) || 0;
                    $('#' + social_site + '-badge').text(shareCount);
                    $('#total-share').text(parseInt($('#total-share').text()) + parseInt($('#' + social_site+ '-badge').text()));
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
        var popUp = window.open(
            popUpURL,
            'Share Dialog',
            'width=626,height=436');
        $(window).on('focus', function () {
            if (popUp.closed) {
                this._updateStatistics(key, this.slide_url);
                $(window).off('focus');
            }
        });
    },
});
});
