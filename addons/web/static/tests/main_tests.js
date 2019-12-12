// define the 'web.web_client' module because some other modules require it
odoo.define('web.web_client', async function (require) {
    "use strict";

    const session = require("web.session");

    owl.config.mode = "dev";

    await session.is_bound;
    session.owlTemplates = session.owlTemplates.replace(/t-transition/g, 'transition');
});
