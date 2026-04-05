/** @odoo-module **/

import PublicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

PublicWidget.registry.ProductInfoWidget = PublicWidget.Widget.extend({
    selector: '#blog_search_form',
    events: {
        'click': '_onBlogInfoClick',
    },

    _onBlogInfoClick: function(ev) {
        ev.preventDefault();
         const query = this.$el.find('input[name="search"]').val().trim();

        if (!query) {
            return;  // Don't search if query is empty
        }

        rpc('/product_info', {  // This should be renamed to match the route purpose
            query: query
        }).then((response) => {
            if (response.url) {
                // Redirect to the found blog post
                window.location.href = response.url;
            } else {
                // Show a message that no post was found
                alert("No matching blog post found");
                // Or show in your modal if you prefer:
                // const modalBody = $("#modal-content-placeholder");
                // modalBody.html("<p style='color: red; font-size: 16px;'>No matching blog post found</p>");
                // $("#product_info_model").modal("show");
            }
        }).catch((error) => {
            alert("Error searching for blog post");
        });
    },
});
