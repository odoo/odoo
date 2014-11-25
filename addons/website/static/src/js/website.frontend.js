(function () {
    'use strict';

    var _t = openerp._t;
    var website = openerp.website;
    website.add_template_file('/website/static/src/xml/website.frontend.xml');

    website.social_share = openerp.Widget.extend({
        /*
            element:Element to bind popover
            social_list: List of social media avialable
            configure: To configure socail pluging (url, width, height)
        */
        template: 'website.social_share',
        init: function(template, element, social_list, configure){
            //Initialization
            this._super.apply(this, arguments);
            this.element = element;
            this.social_list = social_list;
            this.target = 'social_share';
            this.renderElement();
            //this.bind_events();
        },
        // set_value: function(type, description, title, url, image){
        //     console.log("call set_value");
        // },
        bind_events: function() {
            $('.fa-facebook').on('click', $.proxy(this.facebook, this));
            $('.fa-twitter').on('click', $.proxy(this.twitter, this));
            $('.fa-linkedin').on('click', $.proxy(this.linkedin, this));
            $('.fa-google-plus').on('click', $.proxy(this.google_plus, this));
        },
        renderElement: function() {
            this.$el.append(openerp.qweb.render(this.template, {medias: this.social_list, id: this.target}));
            this.element.popover({
                'content': this.$el.html(),
                'placement': 'bottom',
                'container': this.element,
                'html': true,
                'trigger': 'hover',
                'animation': false,
            }).popover("show")
                .on("mouseleave", function () {
                    var _this = this;
                    setTimeout(function () {
                        if (!$(".popover:hover").length) {
                            $(_this).popover("destroy")
                        }
                    }, 100);
                });
                $('.popover').on("mouseleave", function () {
                    $(this).hide();
                });
            this.bind_events();
        },
        google_plus: function(){
            this.renderSocial('google-plus');
        },
        facebook: function(){
            this.renderSocial('facebook');
        },
        twitter: function(){
            this.renderSocial('twitter');
        },
        linkedin: function(){
            this.renderSocial('linkedin');
        },
        renderSocial: function(social){
            var url = this.element.data('url') || window.location.href.split(/[?#]/)[0]; // get current url without query string if not pass
            var title = this.element.data('share_content');
            var content = this.element.data('description');
            content=content.replace(/<(?:.|\n)*?>/gm, ''); //removing html tags from description
            var hashtag = document.title.split(" | ")[1].replace(' ','').toLowerCase();
            var social_network = {
                'facebook':'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(url),
                'twitter': 'https://twitter.com/intent/tweet?original_referer=' + encodeURIComponent(url) + '&text=' + encodeURIComponent(title + ' - ' + url + ' #' + encodeURIComponent(hashtag)),
                'linkedin': 'https://www.linkedin.com/shareArticle?mini=true&url=' + encodeURIComponent(url) + '&title=' + encodeURIComponent(title) + '&summary=' + encodeURIComponent(content),
                'google-plus': 'https://plus.google.com/share?url=' + encodeURIComponent(url)
            };
            if (_.contains(_.keys(social_network), social)){
                var window_height = 500, window_width = 500;
                window.open(social_network[social], '', 'menubar=no, toolbar=no, resizable=yes, scrollbar=yes, height=' + window_height + ',width=' + window_width);
            }
        },
    });

    website.ready().done(function() {
        $('.social_share').on('hover', function() {
            var default_social_list = ['facebook','twitter', 'linkedin', 'google-plus']
            var social_list = _.intersection(eval($(this).data('social')) || default_social_list, default_social_list);
            new website.social_share('social_share',$(this), social_list, {});
        });
    });
})();
