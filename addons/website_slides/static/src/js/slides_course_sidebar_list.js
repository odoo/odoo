odoo.define('website_slides.sidebar', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');

    var SideBar = publicWidget.Widget.extend({
        init: function (el){
            this._super.apply(this,arguments);
        },
        start: function (){
            $('.o_wslides_fullscreen_toggle_sidebar').click(function (ev){
                ev.preventDefault();
                $(ev.currentTarget).toggleClass('active');
                $('.o_wslides_fullscreen_sidebar').toggleClass('o_wslides_fullscreen_sidebar_hidden');
                $('.o_wslides_fullscreen_player').toggleClass('o_wslides_fullscreen_player_no_sidebar')
            })
            return this._super.apply(this, arguments);
        },
    });

    publicWidget.registry.websiteSlidesSidebarList = publicWidget.Widget.extend({
        selector: '.o_wslides_fullscreen_toggle_sidebar',
        // xmlDependencies: ['/website_slides/static/src/xml/website_slides.xml'],
        init: function (el){
            this._super.apply(this, arguments);
        },
        start: function (){
            this._super.apply(this, arguments);
            var sideBar = new SideBar(this);
            sideBar.appendTo(".oe_js_side_bar_list");
        }
    });
});
