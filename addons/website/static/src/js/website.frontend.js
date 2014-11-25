(function () {
    'use strict';

    var _t = openerp._t;
    var website = openerp.website;
    var qweb = openerp.qweb;
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
            if (template) {
                this.template='website.'+template;
            }
            this.renderElement();

        },
        bind_events: function() {
            $('.fa-facebook').on('click', $.proxy(this.facebook, this));
            $('.fa-twitter').on('click', $.proxy(this.twitter, this));
            $('.fa-linkedin').on('click', $.proxy(this.linkedin, this));
            $('.fa-google-plus').on('click', $.proxy(this.google_plus, this));
        },
        renderElement: function(configure) {
            if (this.template == 'website.social_share_dialog'){
                console.log('dialog mode detected');
                $('body').append(qweb.render(this.template, {medias: this.social_list}));
                $('#social_share_modal').modal('show');
//                 this.$el.append(qweb.render('website.social_share', {medias: this.social_list, id: this.target}));
//                 this.element.popover({
//                     'content': this.$el.html(),
//                     'placement': 'right',
//                     'container': this.element,
//                     'html': true,
//                     'trigger': 'hover',
//                     'animation': false,
//                 }).popover("show");

            } else {
                this.$el.append(qweb.render(this.template, {medias: this.social_list, id: this.target}));
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
            }
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
            var title = document.title.split(" | ")[0];
            var content = $($(this.element).parents().find('.row').find('p')[0]).html();
            if (!content) {
                content = 'You should check this out!';
            }
            var hashtag = document.title.split(" | ")[1].replace(' ','').toLowerCase();
            var social_network = {
                'facebook':'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(url),
                'twitter': 'https://twitter.com/intent/tweet?original_referer=' + encodeURIComponent(url) + '&text=' + encodeURIComponent(title + ' - ' + url + ' #' + hashtag),
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

    //displaying banner after new question/answer
    $(document.body).on('click', '.social_share_call', function() {
        var default_social_list = ['facebook','twitter', 'linkedin', 'google-plus']
        var social_list = _.intersection(eval($(this).data('social')) || default_social_list, default_social_list);

        // var url = self.data('url') || window.location.href.split(/[?#]/)[0];
        // var text_to_share = self.data('share_content');
        // var description =  self.data('description');
        var dataObject = {};
        dataObject_func('social_list', social_list);
        dataObject_func('url', $(this).data('url'));
        dataObject_func('title', $('input[name=post_name]').val());
        function dataObject_func(propertyName, propertyValue)
        {
            if(propertyValue) dataObject[propertyName] = propertyValue;
        };
        // Put the object into storage
        localStorage.setItem('social_share', JSON.stringify(dataObject));
    });
    website.ready().done(function() {
        if(localStorage.getItem('social_share')){
            // Retrieve the object from storage
            var dataObject = JSON.parse(localStorage.getItem('social_share'));
            new website.social_share(
                'social_share_dialog',
                $('a[data-oe-expression="question.name"]'),
                dataObject['social_list'],
                {}
            );
            localStorage.removeItem('social_share');
        }
    });
})();
