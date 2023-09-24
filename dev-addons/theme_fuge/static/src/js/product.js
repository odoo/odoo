odoo.define('theme_fuge.product', function(require){
    'use strict';

    var Animation = require('website.content.snippets.animation');
    var ajax = require('web.ajax');

      Animation.registry.get_blog_post = Animation.Class.extend({
        selector : '.blog',
        start: function(){
            var self = this;
            ajax.jsonRpc('/get_blog_post', 'call', {})
            .then(function (data) {
                if(data){
                    self.$target.empty().append(data);
                }
            });
        }
    });

     Animation.registry.get_main_product = Animation.Class.extend({
        selector : '.product',
        start: function(){
            var self = this;
            ajax.jsonRpc('/get_main_product', 'call', {})
            .then(function (data) {
                if(data){
                    self.$target.empty().append(data);
                }
            });
        }
    });
});