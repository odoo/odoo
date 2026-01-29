/** @odoo-module **/

import { registry } from "@web/core/registry";

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
    steps = steps.concat([{
        content: `Check we are on the "${talkName}" talk page`,
        trigger: 'div.o_wesession_track_main',
        run: function () {}, // it's a check
    }]);

    if (reminderOn) {
        steps = steps.concat([{
            content: `Check Favorite for ${talkName} was already on`,
            trigger: 'div.o_wetrack_js_reminder i.fa-bell',
            run: function () {}, // it's a check
        }]);
    }
    else {
        steps = steps.concat([{
            content: `Check Favorite for ${talkName} was off`,
            trigger: 'div.o_wetrack_js_reminder i.fa-bell-o',
            run: function () {}, // it's a check
        }]);
        if (toggleReminder) {
            steps = steps.concat([{
                content: "Set Favorite",
                trigger: 'div.o_wetrack_js_reminder',
                run: 'click',
            }, {
                content: `Check Favorite for ${talkName} is now on`,
                trigger: 'div.o_wetrack_js_reminder i.fa-bell',
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
        trigger: 'a.o_wevent_meeting_room_card h4:contains("' + roomName + '")',
        run: function() {
            // can't click on it, it will try to launch Jitsi and fail on chrome headless
        },
    }];
    return steps;
};


/**
 * REGISTER STEPS
 */

var registerSteps = [{
    content: 'Go on Register',
    trigger: 'a.btn-primary:contains("Register")',
}, {
    content: 'Open ticket modal',
    trigger: 'button.btn-primary:contains("Register")',
}, {
    content: "Select 2 units of 'Standard' ticket type",
    trigger: '.o_wevent_ticket_selector select',
    run: 'text 2',
}, {
    content: "Click on 'Register' button",
    trigger: '#o_wevent_tickets .btn-primary:contains("Register"):not(:disabled)',
    run: 'click',
}, {
    content: "Fill attendees details",
    trigger: 'form[id="attendee_registration"] .btn[type=submit]',
    run: function () {
        $("input[name*='1-name']").val("Raoulette Poiluchette");
        $("input[name*='1-phone']").val("0456112233");
        $("input[name*='1-email']").val("raoulette@example.com");
        $("select[name*='1-simple_choice']").val($("select[name*='1-simple_choice'] option:contains('Consumers')").val());
        $("input[name*='2-name']").val("Michel Tractopelle");
        $("input[name*='2-phone']").val("0456332211");
        $("input[name*='2-email']").val("michel@example.com");
        $("select[name*='2-simple_choice']").val($("select[name*='1-simple_choice'] option:contains('Research')").val());
        $("textarea[name*='text_box']").text("An unicorn told me about you. I ate it afterwards.");
    },
}, {
    content: "Validate attendees details",
    extra_trigger: "input[name*='1-name'], input[name*='2-name'], input[name*='3-name']",
    trigger: 'button[type=submit]',
    run: 'click',
}, {
    trigger: 'div.o_wereg_confirmed_attendees span:contains("Raoulette Poiluchette")',
    run: function () {} // check
}, {
    trigger: 'div.o_wereg_confirmed_attendees span:contains("Michel Tractopelle")',
    run: function () {} // check
},  {
    content: "Click on 'register favorites talks' button",
    trigger: 'a:contains("register to your favorites talks now")',
    run: 'click',
},  {
    trigger: 'h4:contains("Book your talks")',
    run: function() {},
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
}, {
    content: 'Check we are on the talk list page',
    trigger: 'h4:contains("Book your talks")',
    run: function () {} // check
}];

var browseMeetSteps = [{
    content: 'Browse Meet',
    trigger: 'a:contains("Community")',
}, {
    content: 'Check we are on the community page',
    trigger: 'h3:contains("Join a room")',
    run: function () {} // check
}];


registry.category("web_tour.tours").add('wevent_register', {
    url: '/event',
    test: true,
    steps: () => [].concat(
        initTourSteps('Online Reveal'),
        browseTalksSteps,
        discoverTalkSteps('What This Event Is All About', true, true),
        browseTalksSteps,
        discoverTalkSteps('Live Testimonial', false, false, false),
        browseTalksSteps,
        discoverTalkSteps('Our Last Day Together!', true, false, true),
        browseMeetSteps,
        discoverRoomSteps('Best wood for furniture'),
        registerSteps,
    )
});
