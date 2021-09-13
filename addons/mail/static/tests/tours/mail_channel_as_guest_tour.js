/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('mail/static/tests/tours/mail_channel_as_guest_tour.js', {
    test: true,
}, [{
    content: "Click join",
    trigger: '.o_WelcomeView_joinButton',
    extraTrigger: '.o_ThreadView',
}, {
    content: "Check that we are on channel page",
    trigger: '.o_ThreadView',
    run() {
        if (!window.location.pathname.startsWith('/discuss/channel')) {
            console.error('Clicking on join button did not redirect to channel page');
        }
        // Wait for modules to be loaded or failed for the next step
        odoo.__DEBUG__.didLogInfo.then(() => {
            const { missing, failed, unloaded } = odoo.__DEBUG__.jsModules;
            if ([missing, failed, unloaded].some(arr => arr.length)) {
                console.error("Couldn't load all JS modules.", JSON.stringify({ missing, failed, unloaded }));
            }
            document.body.classList.add('o_mail_channel_as_guest_tour_modules_loaded');
        });
    },
    extraTrigger: '.o_mail_channel_as_guest_tour_modules_loaded',
}, {
    content: "Wait for all modules loaded check in previous step",
    trigger: '.o_mail_channel_as_guest_tour_modules_loaded',
}]);
