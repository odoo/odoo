odoo.define('website_sale_slides.unsubscribe_modal', function (require) {
"use strict";

var SlidesUnsubscribe = require('website_slides.unsubscribe_modal');

SlidesUnsubscribe.websiteSlidesUnsubscribe.include({
    xmlDependencies: (SlidesUnsubscribe.websiteSlidesUnsubscribe.prototype.xmlDependencies || []).concat(
        ["/website_sale_slides/static/src/xml/website_slides_unsubscribe.xml"]
    ),
});

});
