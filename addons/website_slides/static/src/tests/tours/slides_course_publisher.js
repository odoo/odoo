odoo.define('website_slides.tour.slide.course.publisher', function (require) {
'use strict';

var tour = require('web_tour.tour');
var slidesTourTools = require('website_slides.tour.tools');

/**
 * Global use case:
 * a user (website publisher) creates a course;
 * he updates it;
 * he creates some lessons in it;
 * he publishes it;
 */
tour.register('course_publisher', {
    url: '/slides',
    test: true
}, [].concat(
    slidesTourTools.addTrainingCourse(),
    slidesTourTools.checkCourseMembership(),
    slidesTourTools.addExistingCourseTag(),
    slidesTourTools.addNewCourseTag('The Most Awesome Course'),
    slidesTourTools.addSection('Introduction'),
    slidesTourTools.addVideoToSection('Introduction'),
    slidesTourTools.addVideoAndCreateSectionOnTheFly(),
    slidesTourTools.addVideoToSectionCreatedOnTheFly(),
    slidesTourTools.dragAndDropSlide(),
    slidesTourTools.addVideoWithNoSection(),
    slidesTourTools.publishNewlyAddedSlide(),
    slidesTourTools.archiveSlide(),
    slidesTourTools.testSlideOrder()
));

});
