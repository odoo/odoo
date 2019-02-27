odoo.define('website_sale_slides.course_purchase_tour', function (require) {
"use strict";

var tour = require('web_tour.tour');

/**
 * Global use case:
 * - student (= demo user) checks 'on payment' course content
 * - clicks on "buy course"
 * - is redirected to webshop on the product page
 *
 * Ideally this test should check the whole process by actually buying
 * the course but it's tricky because the default payment acquirer ("wire transfer")
 * does not validate the sale order by default and thus does not grant access to
 * the course content.
 */
tour.register('course_purchase_tour', {
    url: '/slides',
    test: true
}, [{
    trigger: 'a:contains("DIY Furniture")'
}, {
    trigger: '.o_wslides_course_main',
    run: function () {
        // check that user doesn't have access to course content
        if ($('.o_wslides_slides_list_slide .o_wslides_js_slides_list_slide_link').length === 0) {
            $('.o_wslides_course_main').addClass('empty-content-success');
        }
    }
}, {
    trigger: '.o_wslides_course_main.empty-content-success',
    run: function () {} // check that previous step succeeded
}, {
    trigger: 'a:contains("Buy Course")'
}, {
    trigger: '.oe_website_sale h1:contains("DIY Furniture")',
    run: function () {} // check that user is redirected on product's webshop page
}
]);

});
