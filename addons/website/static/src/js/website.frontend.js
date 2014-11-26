(function () {
    'use strict';

    var _t = openerp._t;
    var website = openerp.website;
    var qweb = openerp.qweb;
    website.add_template_file('/website/static/src/xml/website.frontend.xml');

    website.social_share = openerp.Widget.extend({
        /*
            template: Template for widget rendering. 'social_share' for popover, 'social_share_modal' for modal
            element: Element to bind popover (can ba any element if template is modal)
            social_list: List of social media available from ['facebook','twitter', 'linkedin', 'google-plus']
        */
        template: 'website.social_share',
        init: function(template, element, social_list, hashtag_list){

            //Initialization
            this._super.apply(this, arguments);
            this.element = element;
            this.social_list = social_list;
            this.target = 'social_share';
            this.template='website.'+template;
            this.hashtag_list = hashtag_list;
            this.renderElement();
            this.bind_events();

        },
        bind_events: function() {
            $('.fa-facebook').on('click', $.proxy(this.renderSocial, this, 'facebook', this.hashtag_list));
            $('.fa-twitter').on('click', $.proxy(this.renderSocial, this, 'twitter', this.hashtag_list));
            $('.fa-linkedin').on('click', $.proxy(this.renderSocial, this, 'linkedin', this.hashtag_list));
            $('.fa-google-plus').on('click', $.proxy(this.renderSocial, this, 'google-plus', this.hashtag_list));
        },
        renderElement: function() {
            if (this.template == 'website.social_share_modal'){
                $('body').append(qweb.render(this.template, {medias: this.social_list}));
                $('#social_share_modal').modal('show');
            } else {
                this.$el.append(qweb.render(this.template, {medias: this.social_list, id: this.target}));
                //we need to re-render the element on each hover; popover has the nasty habit of not hiding but completely removing its code from the page
                //so the binding is lost if we simply trigger on hover.
                this.element.popover({
                    'content': this.$el.html(),
                    'placement': 'bottom',
                    'container': this.element,
                    'html': true,
                    'trigger': 'manual',
                    'animation': false,
                }).popover("show")
                .on("mouseleave", function () {
                    var self = this;
                    setTimeout(function () {
                        if (!$(".popover:hover").length) {
                            $(self).popover("destroy")
                        }
                    }, 200);
                });
            }
        },
        // Proxy functions, they are in the technical spec but are not necessary. Should I delete them?
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
        renderSocial: function(social, hashtag_list){
            var url = document.URL.split(/[?#]/)[0] // get current url without query string
            var title = document.title.split(" | ")[0]; // get the page title without the company name
            var content = $($(this.element).parents().find('.row').find('p')[0]).html(); // fetch the first paragraph in the parent 'row' div (norally related to the content we want to share)
            if (!content) {
                content = 'You should check this out!';
            }
            var hashtags = ' #'+ document.title.split(" | ")[1].replace(' ',''); // company name without spaces (for hashtag)
            if (hashtag_list!='') {
                for (var i=0; i<hashtag_list.length; i++) {
                    hashtags = hashtags + " #" + hashtag_list[i].replace(' ','');
                }
            }

            var social_network = {
                'facebook':'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(url),
                'twitter': 'https://twitter.com/intent/tweet?original_referer=' + encodeURIComponent(url) + '&text=' + encodeURIComponent(title + hashtags + ' - ' + url),
                'linkedin': 'https://www.linkedin.com/shareArticle?mini=true&url=' + encodeURIComponent(url) + '&title=' + encodeURIComponent(title) + '&summary=' + encodeURIComponent(content),
                'google-plus': 'https://plus.google.com/share?url=' + encodeURIComponent(url)
            };
            if (_.contains(_.keys(social_network), social)){
                var window_height = 500, window_width = 500;
                window.open(social_network[social], '', 'menubar=no, toolbar=no, resizable=yes, scrollbar=yes, height=' + window_height + ',width=' + window_width);
            }
        },
    });

    // Initialize all social_share links when ready
    website.ready().done(function() {
        $('.social_share').on('hover', function() {
            var default_social_list = ['facebook','twitter', 'linkedin', 'google-plus']
            var hashtag_list = eval($(this).data('hashtag_list'));
            var social_list = _.intersection(eval($(this).data('social')) || default_social_list, default_social_list);
            new website.social_share('social_share',$(this), social_list, hashtag_list);
        });
    });

    // Display modal after new question/answer
    $(document.body).on('click', '.social_share_call', function() {
        var default_social_list = ['facebook','twitter', 'linkedin', 'google-plus']
        var hashtag_list = eval($(this).data('hashtag_list'));
        var social_list = _.intersection(eval($(this).data('social')) || default_social_list, default_social_list);

        var dataObject = {};
        dataObject_func('social_list', social_list);
        dataObject_func('hashtag_list', hashtag_list);
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
                'social_share_modal',
                $(this),
                dataObject['social_list'],
                dataObject['hashtag_list']
            );
            localStorage.removeItem('social_share');
        }
    });
})();
