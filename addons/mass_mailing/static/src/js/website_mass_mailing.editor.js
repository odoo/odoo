(function () {
    'use strict';

    var website = openerp.website;
    var _t = openerp._t;

    website.snippet.options.mailing_list_subscribe = website.snippet.Option.extend({
        on_prompt: function () {
            var self = this;
            return website.prompt({
                id: "editor_new_mailing_list_subscribe_button",
                window_title: _t("Add a Newsletter Subscribe Button"),
                select: _t("Newsletter"),
                init: function (field) {
                    return website.session.model('mail.mass_mailing.list')
                            .call('name_search', ['', []], { context: website.get_context() });
                },
            }).then(function (mailing_list_id) {
                self.$target.attr("data-list-id", mailing_list_id);
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


