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
            this.element = element;
            this.social_list = social_list;
            this.target = 'social_share';
            // this.element.data = {'toggle' : 'popover', 'container' : 'body', 'placement' : 'bottom', 'target' : '#' + this.target};
            this.renderElement();
            this.bind_events();
        },
        set_value: function(type, description, title, url, image){   
            console.log("call set_value");
        },
        bind_events: function() {
            $('.fa-facebook').on('click', this.facebook);
            $('.fa-twitter').on('click', this.twitter);
            $('.fa-linkedin').on('click', this.linkedin);
            $('.fa-google-plus').on('click', this.google_plus);
        },
        renderElement: function() {
            var self = this;
            this.$el.append(openerp.qweb.render(this.template, {medias: this.social_list, id: this.target}));
            console.log("calll renderElement",this.element, this.$el);
            
            self.element.popover({
                'content': this.$el.html(),
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
        render: function(){
            //find on which social icon click and reneder one of below function
        },
        google_plus: function(){
            //call schema template
            console.log("call google-plus");
        },
        facebook: function(){
            // call opengraphtemplate
            console.log("call facebook");
        },
        twitter: function(){
            console.log("call twitter");
        },
        linkedin: function(){
            console.log("call linkedin");
        },
    });

    website.ready().done(function() {
        $(document.body).on('hover', 'a.social_share', function() {
            var social_list = eval($(this).data('social')) || ['facebook','twitter', 'linkedin', 'google-plus']
            new website.social_share(
                        $(this),
                        social_list,
                        {'facebook': {'width':100, 'height':100}}
                    );
            //social_share_obj.set_value('type', 'description', 'title', 'url', 'image');
        });
    });
})();