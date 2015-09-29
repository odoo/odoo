odoo.define('website.share', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var Widget = require('web.Widget');
var base = require('web_editor.base');

var _t = core._t;
var qweb = core.qweb;

ajax.loadXML('/website/static/src/xml/website.share.xml', qweb);

var SocialShare = Widget.extend({
    template: 'website.social_hover',
    /**
        :param element: element to bind popover
        :param social_list: list of social media strings available from
                            ['facebook','twitter', 'linkedin', 'google-plus']
        :param hashtags: string of hashtags for twitter
    */
    init: function (parent) {
        this._super.apply(this, arguments);
        this.element = parent;
        if (parent.data('social')) {
            this.social_list = (parent.data('social')).split();
        } else {
            this.social_list = ['facebook','twitter', 'linkedin', 'google-plus'];
        }
        this.hashtags = parent.data('hashtags') || '';
        this.renderElement();
        this.bind_events();
    },
    bind_events: function () {
        $('.oe_social_facebook').click($.proxy(this.renderSocial, this, 'facebook'));
        $('.oe_social_twitter').click($.proxy(this.renderSocial, this, 'twitter'));
        $('.oe_social_linkedin').click($.proxy(this.renderSocial, this, 'linkedin'));
        $('.oe_social_google-plus').click($.proxy(this.renderSocial, this, 'google-plus'));
    },
    renderElement: function () {
        this.$el.append(
            qweb.render('website.social_hover', {medias: this.social_list}));
        //we need to re-render the element on each hover; popover has the nasty habit of not hiding but completely removing its
        // code from the page
        //so the binding is lost if we simply trigger on hover.
        this.element.popover({
            'content': this.$el.html(),
            'placement': 'bottom',
            'container': this.element,
            'html': true,
            'trigger': 'manual',
            'animation': false,
        }).popover("show").on("mouseleave", function () {
            var self = this;
            setTimeout(function () {
                if (! $(".popover:hover").length) {
                    $(self).popover("destroy");
                }
            }, 200);
        });
    },
    renderSocial: function(social) {
        var url = document.URL.split(/[?#]/)[0];  // get current url without query string
        var title = document.title.split(" | ")[0];  // get the page title without the company name
        var hashtags = ' #'+ document.title.split(" | ")[1].replace(' ','') + ' ' + this.hashtags;  // company name without spaces (for hashtag)
        var social_network = {
            'facebook':'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(url),
            'twitter': 'https://twitter.com/intent/tweet?original_referer=' + encodeURIComponent(url) + '&text=' + encodeURIComponent(title + hashtags + ' - ' + url),
            'linkedin': 'https://www.linkedin.com/shareArticle?mini=true&url=' + encodeURIComponent(url) + '&title=' + encodeURIComponent(title),
            'google-plus': 'https://plus.google.com/share?url=' + encodeURIComponent(url)
        };
        if (! _.contains(_.keys(social_network), social)) return;
        var window_height = 500, window_width = 500;
        window.open(social_network[social], '', 'menubar=no, toolbar=no, resizable=yes, scrollbar=yes, height=' + window_height + ',width=' + window_width);
    },
});

// Initialize all social_share links when ready
base.ready().done(function() {
    $('.oe_social_share').mouseenter(function() {
        new SocialShare($(this));
    });
});

return SocialShare;

});
