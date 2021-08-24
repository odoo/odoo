odoo.define('website_sale_slides.unsubscribe_modal', function (require) {
"use strict";

var SlidesUnsubscribe = require('@website_slides/js/slides_course_unsubscribe')[Symbol.for("default")];

SlidesUnsubscribe.websiteSlidesUnsubscribe.include({
    xmlDependencies: (SlidesUnsubscribe.websiteSlidesUnsubscribe.prototype.xmlDependencies || []).concat(
        ["/website_sale_slides/static/src/xml/website_slides_unsubscribe.xml"]
    ),
});

});
