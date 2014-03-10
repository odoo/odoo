(function() {
    "use strict";

    var website = openerp.website;
    var _t = openerp._t;
    website.add_template_file('/website_forum/static/src/xml/website_forum.xml');

    website.is_editable = true;
    website.EditorBar.include({
        start: function() {
            website.is_editable_button = website.is_editable_button || !!$("#wrap").size();
            var res = this._super();
            this.$(".dropdown:has(.oe_content_menu)").removeClass("hidden");
            return res;
        },
        events: _.extend({}, website.EditorBar.prototype.events, {
            'click a[data-action=new_question]': function (ev) {
                ev.preventDefault();
                website.prompt({
                    id: "editor_new_forum",
                    window_title: _t("New Forum"),
                    input: "Forum Name",
                }).then(function (forum_name) {
                    website.form('/forum/add_forum', 'POST', {
                        forum_name: forum_name
                    });
                });
            }
        }),
    });
})();


$(document).ready(function () {

    $('.fa-thumbs-up ,.fa-thumbs-down').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var value = $link.attr("value")
        openerp.jsonRpc("/forum/post_vote/", 'call', {
                'post_id': $link.attr("id"),
                'vote': value})
            .then(function (data) {
                $link.parent().find("#vote_count").html(data);
                //TODO: set proper class
                $link.addClass("text-success");
            });
        return false;
    });
});