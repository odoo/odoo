
openerp.web_uservoice = function(instance) {

var QWeb = instance.web.qweb;
QWeb.add_template('/web_uservoice/static/src/xml/web_uservoice.xml');

$(function() {
    var src = ("https:" == document.location.protocol ? "https://" : "http://") + "cdn.uservoice.com/javascripts/widgets/tab.js";
    $.getScript(src);
});


instance.web_uservoice.UserVoice = instance.web.Widget.extend({
    template: 'Header-UserVoice',
    default_forum: '77459',

    init: function() {
        this._super.apply(this, arguments);
        this.uservoiceOptions = {
            key: 'openerpsa',
            host: 'feedback.openerp.com',
            forum: this.default_forum,
            lang: 'en',
            showTab: false
        };

        instance.webclient.menu.do_menu_click.add_last(this.do_menu_click);
    },

    start: function() {
        this._super();

        var self = this;
        this.$element.find('a').click(function(e) {
            e.preventDefault();
            UserVoice.Popin.show(self.uservoiceOptions);
            return false;
        });
    },


    do_menu_click: function($clicked_menu, manual) {
        var id = $clicked_menu.attr('data-menu');
        if (id) {
            var self = this;
            this.rpc('/web_uservoice/uv/forum', {menu_id: id}, function(result) {
                self.uservoiceOptions.forum = result.forum || self.default_forum;
            });
        }
    },

});


instance.webclient.uservoice = new instance.web_uservoice.UserVoice(instance.webclient);
instance.webclient.uservoice.prependTo('div.header_corner');

};

