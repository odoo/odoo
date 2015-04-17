odoo.define('website_twitter_wall.editor', function (require) {
"use strict";

var ajax = require('web.ajax');
var website = require('website.website');
var editor = require('website.editor');
var snippet_editor = require('website.snippets.editor');

website.if_dom_contains('.odoo-tw-walls', function() {

    // Storify View
    //----------------------------------------------

    // Change cover image snippets
    editor.EditorBar.include({
        save: function() {
            var res = this._super();
            if ($('.odoo-tw-view-cover').length) {
                ajax.jsonRpc("/twitter_wall/cover/", 'call', {
                    'wall_id': $(".odoo-tw-walls").attr("wall_id"),
                    'url': $('.odoo-tw-view-cover').css('background-image').replace(/url\(|\)|"|'/g,'')
                });
            }
            return res;
        },
    });
    snippet_editor.options.twitter_wall_cover = snippet_editor.Option.extend({
        start: function(type, value, $li) {
            this._super();
            this.src = this.$target.css("background-image").replace(/url\(|\)|"|'/g,'').replace(/.*none$/,'');
            this.$image = $('<image src="'+this.src+'">');
        },
        clear: function(type, value, $li) {
            if (type !== 'click') return;
            this.src = null;
            this.$target.css({"background-image": ''});
            this.$image.removeAttr("src");
        },
        change: function(type, value, $li) {
            if (type !== 'click') return;
            var self = this;
            var _editor  = new editor.MediaDialog(this.$image, this.$image[0], {only_images: true});
            _editor.appendTo('body');
            _editor.on('saved', self, function (event, img) {
                var url = self.$image.attr('src');
                self.$target.css({"background-image": url ? 'url(' + url + ')' : ""});
            });
        },
    });
});
});