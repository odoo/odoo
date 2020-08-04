odoo.define('test_event_full.tour.register', function (require) {
"use strict";

var tour = require('web_tour.tour');

/**
 * TALKS STEPS
 */

var discoverTalkSteps = function (talkName, fromList, reminderOn, toggleReminder) {
    var steps;
    if (fromList) {
        steps = [{
            content: 'Go on "' + talkName + '" talk in List',
            trigger: 'a:contains("' + talkName + '")',
        }];
    }
    else {
        steps = [{
            content: 'Click on Live Track',
            trigger: 'article span:contains("' + talkName + '")',
            run: 'click',
        }];
    }
    if (reminderOn) {
        steps = steps.concat([{
            content: "Check Reminder is on",
            trigger: 'div.o_wetrack_js_reminder i.fa-bell',
            extra_trigger: 'small.o_wetrack_js_reminder_text:contains("Reminder On")',
            run: function () {}, // it's a check
        }]);
    }
    else {
        steps = steps.concat([{
            content: "Check Reminder is Off",
            trigger: 'small.o_wetrack_js_reminder_text:contains("Set Reminder")',
            run: function () {}, // it's a check
        }]);
        if (toggleReminder) {
            steps = steps.concat([{
                content: "Set Reminder",
                trigger: 'small.o_wetrack_js_reminder_text',
                run: 'click',
            }, {
                content: "Check Reminder is On",
                trigger: 'div.o_wetrack_js_reminder i.fa-bell',
                extra_trigger: 'small.o_wetrack_js_reminder_text:contains("Reminder On")',
                run: function () {}, // it's a check
            }]);
        }
    }
    return steps;
};


/**
 * ROOMS STEPS
 */

var discoverRoomSteps = function (roomName) {
    var steps = [{
        content: 'Go on "' + roomName + '" room in List',
        trigger: 'a.o_wevent_meeting_room_card h3:contains("' + roomName + '")',
        run: 'click',
    }];
    return steps;
};


/**
 * REGISTER STEPS
 */

var registerSteps = [{
    content: 'Go on Register',
    trigger: 'li.btn-primary a:contains("Register")',
}, {
    content: "Select 2 units of 'Standard' ticket type",
    extra_trigger: '#wrap:not(:has(a[href*="/event"]:contains("Conference for Architects")))',
    trigger: 'select:eq(0)',
    run: 'text 2',
}, {
    content: "Click on 'Register' button",
    extra_trigger: 'select:eq(0):has(option:contains(2):propSelected)',
    trigger: '.btn-primary:contains("Register")',
    run: 'click',
}, {
    content: "Fill attendees details",
    trigger: 'form[id="attendee_registration"] .btn:contains("Continue")',
    run: function () {
        $("input[name='1-name']").val("Raoulette Poiluchette");
        $("input[name='1-phone']").val("0456112233");
        $("input[name='1-email']").val("raoulette@example.com");
        $("input[name='2-name']").val("Michel Tractopelle");
        $("input[name='2-phone']").val("0456332211");
        $("input[name='2-email']").val("michel@example.com");
    },
}, {
    content: "Validate attendees details",
    extra_trigger: "input[name='1-name'], input[name='2-name'], input[name='3-name']",
    trigger: 'button:contains("Continue")',
    run: 'click',
}];

/**
 * MAIN STEPS
 */

var initTourSteps = function (eventName) {
    return [{
        content: 'Go on "' + eventName + '" page',
        trigger: 'a[href*="/event"]:contains("' + eventName + '"):first',
    }];
};

var browseTalksSteps = [{
    content: 'Browse Talks',
    trigger: 'a:contains("Talks")',
}];

var browseExhibitorsSteps = [{
    content: 'Browse Exhibitors',
    trigger: 'a:contains("Exhibitors")',
}];

var browseMeetSteps = [{
    content: 'Browse Meet',
    trigger: 'a:contains("Community")',
}];


tour.register('wevent_register', {
    url: '/event',
    test: true
}, [].concat(
        initTourSteps('Online Reveal'),
        browseTalksSteps,
        discoverTalkSteps('What This Event Is All About', true, true),
        browseTalksSteps,
        discoverTalkSteps('Live Testimonial', false, false, true),
        browseMeetSteps,
        discoverRoomSteps('Best wood for furniture'),
        registerSteps,
    )
);

});
