(function () {
    'use strict';

    var website = openerp.website;
    var _t = openerp._t;

    website.snippet.options.subscribe = website.snippet.Option.extend({
        on_prompt: function () {
            var self = this;
            return website.prompt({
                id: "editor_new_subscribe_button",
                window_title: _t("Add a Subscribe Button"),
                select: _t("Discussion List"),
                init: function (field) {
                    return website.session.model('mail.group')
                            .call('name_search', ['', [['public','=','public']]], { context: website.get_context() });
                },
            }).then(function (mail_group_id) {
                self.$target.attr("data-id", mail_group_id);
            });
        },
        drop_and_build_snippet: function() {
            var self = this;
            this._super();
            this.on_prompt().fail(function () {
                self.editor.on_remove();
            });
        },
        start : function () {
            var self = this;
            this.$el.find(".js_mailing_list").on("click", _.bind(this.on_prompt, this));
            this._super();
        },
        clean_for_save: function () {
            this.$target.addClass("hidden");
        },
    });
})();


