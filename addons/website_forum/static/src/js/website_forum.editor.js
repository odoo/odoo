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
                if (data == 0) {
                    $link.parent().find(".text-success").removeClass("text-success");
                    $link.parent().find(".text-warning").removeClass("text-warning");
                } else {
                    if (value == 1) {
                        $link.addClass("text-success");
                    } else {
                        $link.addClass("text-warning");
                    }
                }
            });
        return false;
    });

    $('.delete').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        openerp.jsonRpc("/forum/post_delete/", 'call', {
            'post_id': $link.attr("id")})
            .then(function (data) {
                $link.parents('#answer').remove();
            });
        return false;
    });

    $('.fa-check').on('click', function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        openerp.jsonRpc("/forum/correct_answer/", 'call', {
              'post_id': $link.attr("id")})
              .then(function (data) {
                  if (data) {
                    $link.removeClass("oe_answer_false").addClass('oe_answer_true');
                  }
                  else {
                    $link.removeClass("oe_answer_true").addClass('oe_answer_false');
                  }
             });
        return false;
    });

});