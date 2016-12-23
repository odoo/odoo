(function() {
    'use strict';
    var website = openerp.website;

    website.banner = openerp.Class.extend({
        init: function(options) {
            var self = this ;
            var defaults = {
                aggressive: false,
                sensitivity: 40,
                timer: 1000,
                delay: 0,
                cookie_expire: 1,
                container: $(document),
                el: ''
            };
            self.opts = $.extend({}, defaults, options);
            setTimeout(_.bind(self.do_render, self), self.opts.timer)
        },
        do_render: function() {
            var self = this;
            self.opts.container.on('mouseleave', _.bind(self.handle_mouseleave, self));
        },
        handle_mouseleave: function(e) {
            var self =  this;
            if (e.clientY > self.opts.sensitivity || (self.check_cookievalue('expires', new Date()) && !self.opts.aggressive)) return;
            setTimeout(_.bind(self.show_banner,self), self.opts.delay);
        },
        set_cookie_expire: function(days) {
            var ms = days*24*60*60*1000;
            var date = new Date();
            date.setTime(date.getTime() + ms);
            document.cookie = "expires=" + date.toUTCString();
        },
        check_cookievalue: function(cookie_name, current_date) {
            var self = this;
            var expire_date = self.parse_cookies()[cookie_name]
            if(expire_date) {
                if (new Date(expire_date) >= current_date) {
                    return true;
                }
            }
            return false;
        },
        parse_cookies: function() {
            var self = this;
            var cookies = document.cookie.split('; ');
            var res = {};
            _.each(cookies, function(cookie) {
                var el = cookie.split('=');
                res[el[0]] = el[1];
            })
            return res;
        },
        show_banner: function() {
            var self = this;
            if (self.opts.el) self.opts.el.modal('show');
            self.set_cookie_expire(self.opts.cookie_expire);
        },
    });
})();

$(document).ready(function() {
    new openerp.website.banner({'el': $('#banner_modal')});
});
