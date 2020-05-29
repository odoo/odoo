odoo.define('web.web_client', function (require) {
    // this module is required by the test
    const WebClient = require('web.AbstractWebClient');
    const webClient = new WebClient();
    return webClient;
});
