// define the 'web.web_client' module because some other modules require it
odoo.define('web.web_client', async function (require) {
    "use strict";

    const session = require("web.session");
    const { bus } = require('web.core');
    const makeTestEnvironment = require('web.test_env');
    require('web.test_utils');

    // listen to unhandled rejected promises, and when the rejection is not due
    // to a crash, prevent the browser from displaying an 'unhandledrejection'
    // error in the console, which would make tests crash on each Promise.reject()
    // something similar is done by the CrashManagerService, but by default, it
    // isn't deployed in tests
    bus.on('crash_manager_unhandledrejection', this, function (ev) {
        if (!ev.reason || !(ev.reason instanceof Error)) {
            ev.stopPropagation();
            ev.stopImmediatePropagation();
            ev.preventDefault();
        }
    });

    owl.config.mode = "dev";

    await session.is_bound;
    session.owlTemplates = session.owlTemplates.replace(/t-transition/g, 'transition');


    /**
     * Before each test, we want owl.Component.env to be a fresh test environment.
     */
    QUnit.on('OdooBeforeTestHook', function () {
        owl.Component.env = makeTestEnvironment();
    });

    // this is done with the hope that tests are
    // only started all together...
    QUnit.start();
});
