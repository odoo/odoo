odoo.define('website_twitter.editor', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var options = require('web_editor.snippets.options');

var qweb = core.qweb;


options.registry.twitter = options.registry.marginAndResize.extend({
    start: function(){
        this._super();
        this.make_hover_config();
        this.$target.find('.lnk_configure').click(function(e){
             window.location = e.target.href;
        });
        if (this.$target.data("snippet-view")) {
            this.$target.data("snippet-view").stop();
        }
    },
    twitter_reload: function(){
        ajax.jsonRpc('/twitter_reload','call', {});
    },
    make_hover_config: function(){
        var self = this;
        var $configuration = $(qweb.render("website.Twitter.Reload")).hide().appendTo(document.body).click(function (e) {
            e.preventDefault();
            e.stopPropagation();
            self.twitter_reload();
        });
        this.$target.on('mouseover', '', function () {
            var $selected = $(this);
            var position = $selected.offset();
            $configuration.show().offset({
                    top: $selected.outerHeight() / 2
                            + position.top
                            - $configuration.outerHeight() / 2,
                    left: $selected.outerWidth() / 2
                            + position.left
                            - $configuration.outerWidth() / 2,
                })
        }).on('mouseleave', '', function (e) {
            var current = document.elementFromPoint(e.clientX, e.clientY);
            if (current === $configuration[0]) {
                return;
            }
            $configuration.hide();
        });
    },
    clean_for_save: function () {
        this.$target.find(".twitter_timeline").empty();
    },
});

});
