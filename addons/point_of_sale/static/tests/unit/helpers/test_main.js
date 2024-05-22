odoo.define('web.web_client', function (require) {
    // this module is required by the test
    const { bus } = require('web.core');
    const WebClient = require('web.AbstractWebClient');

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

    const webClient = new WebClient();
    return webClient;
});
