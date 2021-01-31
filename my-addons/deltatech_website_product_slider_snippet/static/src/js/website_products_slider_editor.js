odoo.define("deltatech_website_product_slider_snippet.product_slider_editor", function(require) {
    "use strict";

    var core = require("web.core");

    var wUtils = require("website.utils");
    var options = require("web_editor.snippets.options");

    var _t = core._t;

    options.registry.edit_product_list = options.Class.extend({
        select_product_list: function() {
            var self = this;
            return wUtils
                .prompt({
                    id: "editor_product_list_slider",
                    window_title: _t("Select a Product List"),
                    select: _t("Product List"),
                    init: function() {
                        return self._rpc({
                            model: "product.list",
                            method: "name_search",
                            args: ["", []],
                        });
                    },
                })
                .then(function(result) {
                    self.$target.attr("data-id", result.val);
                });
        },
        onBuilt: function() {
            var self = this;
            this._super();
            this.select_product_list("click").guardedCatch(function() {
                self.getParent().removeSnippet();
            });
        },
        cleanForSave: function() {
            this.$target.addClass("d-none");
        },
    });
});
