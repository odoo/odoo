/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

/**
 * Global use case:
 * - a user lands on the article of a course;
 *
 * This tour tests a fix because a traceback error would appear when
 * selecting an article of a course.
 *
 */
 wTourUtils.registerWebsitePreviewTour('course_article', {
    url: '/slides/all',
    test: true,
}, () => [{
    trigger: 'iframe a:contains("Furniture Technical Specifications")'
}, {
    trigger: 'iframe a:contains("Foreword")',
    run: function () {} // check we land on the articleand no traceback appears
}]);
