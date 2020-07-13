odoo.define('test_event_full.tour.register', function (require) {
"use strict";

var tour = require('web_tour.tour');

/**
 * The purpose of this tour is to check the whole certification flow:
 *
 * -> student (= demo user) checks 'on payment' course content
 * -> clicks on "buy course"
 * -> is redirected to webshop on the product page
 * -> buys the course
 * -> fails 3 times, exhausting his attempts
 * -> is removed to the members of the course
 * -> buys the course again
 * -> succeeds the certification
 * -> has the course marked as completed
 * -> has the certification in his user profile
 *
 */


var initTourSteps = [{
    content: 'Go on Online Reveal page',
    trigger: 'a[href*="/event"]:contains("Online Reveal"):first',
}];

var browseSessionsSteps = [{
    content: 'Browse Sessions',
    trigger: 'a:contains("Sessions")',
}, {
    content: 'Go on "Main Gathering" talk',
    trigger: 'a:contains("Main Gathering")',
}];

var registerSteps = [{
    content: 'Go on Register',
    trigger: 'li.btn-primary a:contains("Register")',
}];

tour.register('wevent_register', {
    url: '/event',
    test: true
}, [].concat(
        initTourSteps,
        browseSessionsSteps,
        registerSteps
    )
);

});
