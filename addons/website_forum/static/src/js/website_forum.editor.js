odoo.define('website_forum.editor', function (require) {
"use strict";

var core = require('web.core');
var contentMenu = require('website.contentMenu');
var website = require('website.website');

var _t = core._t;

contentMenu.TopBar.include({
    new_forum: function() {
        website.prompt({
            id: "editor_new_forum",
            window_title: _t("New Forum"),
            input: "Forum Name",init: function () {
                var $group = this.$dialog.find("div.form-group");
                $group.removeClass("mb0");

                var $add = $(
                    '<div class="form-group mb0">'+
                        '<label class="col-sm-offset-3 col-sm-9 text-left">'+
                        '    <input type="checkbox" required="required"/> '+
                        '</label>'+
                    '</div>');
                $add.find('label').append(_t("Add page in menu"));
                $group.after($add);
            }
        }).then(function (forum_name, field, $dialog) {
            var add_menu = ($dialog.find('input[type="checkbox"]').is(':checked'));
            website.form('/forum/new', 'POST', {
                forum_name: forum_name,
                add_menu: add_menu || ""
            });
        });
    },
});

});
