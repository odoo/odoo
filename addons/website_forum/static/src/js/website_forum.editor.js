(function() {
    "use strict";

    var website = openerp.website;
    var _t = openerp._t;

    website.EditorBarContent.include({
        start: function() {
            var self = this;
            $('a[data-action=new_forum]').on('click', this, function() {
                self.new_forum();
            });
            return this._super();
        },
        new_forum: function() {
            website.prompt({
                id: "editor_new_forum",
                window_title: _t("New Forum"),
                input: "Forum Name",
            }).then(function (forum_name) {
                website.form('/forum/new', 'POST', {
                    forum_name: forum_name
                });
            });
        },
    });
})();
