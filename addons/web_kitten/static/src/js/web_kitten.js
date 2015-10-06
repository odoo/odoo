odoo.define('web.Kitten', function (require) {
"use strict";

var Webclient = require('web.WebClient');
var session = require('web.session');

Webclient.include({
    start: function() {
        var self = this;
        return this._super.apply(this, arguments).then(function() {
            if ($.deparam($.param.querystring()).kitten !== undefined) {
                self.to_kitten_mode();
            }
        });
    },
    to_kitten_mode: function() {
        this.$el.addClass("o_kitten_mode_activated");
        this.$el.css("background-image", "url(" + session.origin + "/web_kitten/static/src/img/back-enable.jpg" + ")");
        var imgkit = Math.floor(Math.random() * 2 + 1);
        $.blockUI.defaults.message = '<img src="/web_kitten/static/src/img/k-waiting' + imgkit + '.gif" class="o_loading_kitten">';
    },
});

});