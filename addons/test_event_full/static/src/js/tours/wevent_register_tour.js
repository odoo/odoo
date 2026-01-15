import { registry } from "@web/core/registry";
import { session } from "@web/session";

/**
 * TALKS STEPS
 */
const reminderToggleSteps = function (talkName, reminderOn, toggleReminder) {
    let steps = [];
    if (reminderOn) {
        steps = steps.concat([{
            content: `Check Favorite for ${talkName} was already on`,
            trigger: "div.o_wetrack_js_reminder i.fa-bell",
        }]);
    }
    else {
        steps = steps.concat([{
            content: `Check Favorite for ${talkName} was off`,
            trigger: "div.o_wetrack_js_reminder i.fa-bell-o",
        }]);
        if (toggleReminder) {
            steps = steps.concat([{
                content: "Set Favorite",
                trigger: "i[title='Set Favorite']",
                run: "click",
            }]);
            if (session.is_public){
                steps = steps.concat([{
                    content: "The form of the email reminder modal is filled",
                    trigger: "#o_wetrack_email_reminder_form input[name='email']",
                    run: "fill visitor@odoo.com",
                },
                {
                    content: "The form is submit",
                    trigger: "#o_wetrack_email_reminder_form button[type='submit']",
                    run: "click",
                }]);
            }
            steps = steps.concat([{
                content: `Check Favorite for ${talkName} is now on`,
                trigger: "div.o_wetrack_js_reminder i.fa-bell",
            }]);
        }
    }
    return steps;
};

const discoverTalkSteps = function (talkName, fromList, checkToggleReminder, reminderOn, toggleReminder) {
    var steps;
    if (fromList) {
        steps = [{
            content: 'Go on "' + talkName + '" talk in List',
            trigger: 'a:contains("' + talkName + '")',
            run: "click",
            expectUnloadPage: true,
        }];
    }
    else {
        steps = [{
            content: 'Click on Live Track',
            trigger: 'article span:contains("' + talkName + '")',
            run: 'click',
            expectUnloadPage: true,
        }];
    }
    steps = steps.concat([{
        content: `Check we are on the "${talkName}" talk page`,
        trigger: 'div.o_wesession_track_main',
    }]);
    if (checkToggleReminder){
        steps = steps.concat(reminderToggleSteps(talkName, reminderOn, toggleReminder));
    }
    return steps;
};

/**
 * REGISTER STEPS
 */

const registerSteps = [
    {
        content: "Open ticket modal",
        trigger: "button.btn-primary:contains(Register):enabled",
        run: "click",
    },
    {
        content: "Edit 2 units of 'Standard' ticket type",
        trigger: ".modal .o_wevent_ticket_selector input",
        run: "edit 2",
    },
    {
        content: "Click on 'Register' button",
        trigger: ".modal #o_wevent_tickets .btn-primary:contains(Register):enabled",
        run: "click",
    },
    {
        content: "Wait the modal is shown before continue",
        trigger: ".modal.modal_shown.show form[id=attendee_registration]",
    },
    {
        trigger: ".modal input[name*='1-name']",
        run: "edit Raoulette Poiluchette",
    },
    {
        trigger: ".modal input[name*='1-phone']",
        run: "edit 0456112233",
    },
    {
        trigger: ".modal input[name*='1-email']",
        run: "edit raoulette@example.com",
    },
    {
        trigger: ".modal select[name*='1-simple_choice']",
        run: "selectByLabel Consumers",
    },
    {
        trigger: ".modal input[name*='2-name']",
        run: "edit Michel Tractopelle",
    },
    {
        trigger: ".modal input[name*='2-phone']",
        run: "edit 0456332211",
    },
    {
        trigger: ".modal input[name*='2-email']",
        run: "edit michel@example.com",
    },
    {
        trigger: ".modal select[name*='2-simple_choice']",
        run: "selectByLabel Research",
    },
    {
        trigger: ".modal textarea[name*='text_box']",
        run: "edit An unicorn told me about you. I ate it afterwards.",
    },
    {
        trigger: ".modal input[name*='1-name'], input[name*='2-name'], input[name*='3-name']",
    },
    {
        content: "Validate attendees details",
        trigger: ".modal button[type=submit]:enabled",
        run: "click",
        expectUnloadPage: true,
    },
    {
        content: "Click on 'register favorites talks' button",
        trigger: "a:contains(register to your favorites talks now)",
        run: "click",
        expectUnloadPage: true,
    },
    {
        trigger: "h5:contains(Book your talks)",
    },
];

/**
 * MAIN STEPS
 */

var initTourSteps = function (eventName) {
    return [{
        content: 'Go on "' + eventName + '" page',
        trigger: 'a[href*="/event"]:contains("' + eventName + '"):first',
        run: "click",
        expectUnloadPage: true,
    }];
};

var browseTalksSteps = [{
    content: 'Browse Talks Menu',
    trigger: 'a[href*="#"]:contains("Talks")',
    run: "click",
}, {
    content: 'Browse Talks Submenu',
    trigger: 'a.dropdown-item span:contains("Talks")',
    run: "click",
    expectUnloadPage: true,
}, {
    content: 'Check we are on the talk list page',
    trigger: 'h5:contains("Book your talks")',
}];

var browseBackSteps = [{
    content: 'Browse Back',
    trigger: 'a:contains("All Talks")',
    run: "click",
    expectUnloadPage: true,
}, {
    content: 'Check we are back on the talk list page',
    trigger: 'h5:contains("Book your talks")',
}];

registry.category("web_tour.tours").add('wevent_register', {
    url: '/event',
    steps: () => [].concat(
        initTourSteps('Online Reveal'),
        browseTalksSteps,
        discoverTalkSteps('What This Event Is All About', true, true, true),
        browseBackSteps,
        discoverTalkSteps('Live Testimonial', false, false, false, false),
        browseBackSteps,
        discoverTalkSteps('Our Last Day Together!', true, true, false, true),
        browseBackSteps,
        registerSteps,
    )
});
