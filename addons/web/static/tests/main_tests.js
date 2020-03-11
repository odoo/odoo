// define the 'web.web_client' module because some other modules require it
odoo.define('web.web_client', async function (require) {
    "use strict";

    const session = require("web.session");
    const WebClient = require('web.WebClient');

    owl.config.mode = "dev";

    const webClient = new WebClient();

    await session.is_bound;
    session.owlTemplates = session.owlTemplates.replace(/t-transition/g, 'transition');

    return webClient;
});
