odoo.define('website_slides.sidebar', function (require) {
'use strict';

var sAnimations = require('website.content.snippets.animation');
var Widget = require('web.Widget');

var SideBar = Widget.extend({
    events: {
        'click .o_wslides_fullscreen_toggle_sidebar': '_onClickToggleSideBar'
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickToggleSideBar: function (ev) {
        ev.preventDefault();
        $(ev.currentTarget).toggleClass('active');
        this.$('.o_wslides_fullscreen_sidebar').toggleClass('o_wslides_fullscreen_sidebar_hidden');
        this.$('.o_wslides_fullscreen_player').toggleClass('o_wslides_fullscreen_player_no_sidebar');
    }
});

sAnimations.registry.websiteSlidesSidebarList = sAnimations.Class.extend({
    selector: '.o_wslides_fullscreen_toggle_sidebar',
    start: function (){
        this._super.apply(this, arguments);
        var sideBar = new SideBar(this);
        sideBar.attachTo(".o_wslides");
    }
});

return {
    sideBar: SideBar,
    websiteSlidesSidebarList: sAnimations.registry.websiteSlidesSidebarList
};

});
