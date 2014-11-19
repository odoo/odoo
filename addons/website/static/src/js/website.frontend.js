(function () {
    'use strict';

    var _t = openerp._t,
    website = openerp.website;
    website.add_template_file('/website/static/src/xml/website.frontend.xml');

    website.social_share = openerp.Widget.extend({
        /*
            element:Element to bind popover
            social_list: List of social media avialable
            configure: To configure socail pluging (url, width, height)
        */
        template: 'website.social_share',
        init: function(element, social_list, configure){
            //Initialization
            this._super.apply(this, arguments);
            var self = this;
            this.element = element;
            this.social_list = social_list;
            this.target = 'social_share';
            // this.element.data = {'toggle' : 'popover', 'container' : 'body', 'placement' : 'bottom', 'target' : '#' + this.target};
            this.renderElement();
            this.bind_events();
        },
        // set_value: function(type, description, title, url, image){   
        //     console.log("call set_value");
        // },
        bind_events: function() {
            var self = this;
            $('.fa-facebook').on('click', self.proxy('facebook'));
            $('.fa-twitter').on('click', self.proxy('twitter'));
            $('.fa-linkedin').on('click', self.proxy('linkedin'));
            $('.fa-google-plus').on('click', self.proxy('google_plus'));
        },
        renderElement: function() {
            var self = this;
            this.$el.append(openerp.qweb.render(this.template, {medias: this.social_list, id: this.target}));
            console.log("calll renderElement",this.element, this.$el);
            
            self.element.popover({
                'content': self.$el.html(),
                'placement': 'bottom',
                'container': 'body',
                'html': true,
                'trigger': 'manual',
                'animation': false,
            }).popover("show")
            .on("mouseleave", function () {
                var _this = this;
                setTimeout(function () {
                    if (!$(".popover:hover").length) {
                        $(_this).popover("hide")
                    }
                }, 100);
            });
            $('.popover').on("mouseleave", function () {
                $(this).hide();
            });
        },
        google_plus: function(){
            //call schema template
            console.log("call google-plus");
            this.renderSocial('google-plus');
        },
        facebook: function(){
            // call opengraphtemplate
            console.log("call facebook");
            this.renderSocial('facebook');
        },
        twitter: function(){
            console.log("call twitter");
            this.renderSocial('twitter');
        },
        linkedin: function(){
            console.log("call linkedin");
            this.renderSocial('linkedin');
        },
        renderSocial: function(social){
            var url = this.element.data('url') || window.location.href.split(/[?#]/)[0]; // get current url without query string if not pass 
            var text_to_share = this.element.data('share_content');
            console.log("url", url, text_to_share);
            var social_network = {
                'facebook':'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(url),
                'twitter': 'https://twitter.com/intent/tweet?original_referer=' + encodeURIComponent(url) + '&amp;text=' + encodeURIComponent(text_to_share + ' - ' + url),
                'linkedin': 'https://www.linkedin.com/shareArticle?mini=true&url=' + encodeURIComponent(url) + '&title=' + encodeURIComponent(text_to_share) + '&summary=' + encodeURIComponent(this.element.data('description')),
                'google-plus': 'https://plus.google.com/share?url=' + encodeURIComponent(url)
            };
            if (_.contains(_.keys(social_network), social)){
                console.log("cllllll")
                var window_height = 500, window_width = 500, left = (screen.width/2)-(window_width/2), top = (screen.height/2)-(window_height/2);
                window.open(social_network[social], '', 'menubar=no, toolbar=no, resizable=yes, scrollbar=yes, height=' + window_height + ',width=' + window_width + ', top=' + top + ', left=' + left);
            }
            //find on which social icon click and reneder one of below function
        },
    });

    website.ready().done(function() {
        $(document.body).on('hover', 'a.social_share', function() {
            var self = $(this);
            var default_social_list = ['facebook','twitter', 'linkedin', 'google-plus']
            var social_list = _.intersection(eval($(this).data('social')) || default_social_list, default_social_list);
            new website.social_share(
                        $(this),
                        social_list,
                        {'facebook': {'width':100, 'height':100}}
                    );
            // social_share_obj.set_value('type', 'description', 'title', 'url', 'image');
        });
    });
})();