(function() {
    "use strict";

    var website = openerp.website;
    website.add_template_file('/website_sale/static/src/xml/website_sale.xml');

    website.EditorBar.include({
        events: _.extend({}, website.EditorBar.prototype.events, {
            'click a[data-action=new_product]': function (ev) {
                ev.preventDefault();
                website.prompt({
                    window_title: "New Product",
                    input: "Product Name",
                }).then(function (name) {
                    website.form('/shop/add_product', 'POST', {
                        name: name
                    });
                });
            }
        }),
    });
})();
