odoo.define('http_routing.http_cookie', function (require) {
'use strict';

const utils = require('web.utils');

const originFunc = utils.checkCookie;
utils.checkCookie = function (type, name) {
    const supportedType = ["required", "preference", "marketing", "statistic"];
    if (!supportedType.includes(type)) {
        console.error(`Cookie '${name}' of type '${type}' is unknown.`);
        type = 'required';
    }

    const result = originFunc.apply(this, arguments);
    if (type == 'required') {
        return true && result;
    }

    const consents = JSON.parse(utils.get_cookie('cookies_consent') || "{}");
    if(!consents) {
        return !odoo.session_info.has_cookie_bar && result;
    }
    else if (type in consents) {
        return consents[type] && result;
    }

    // error, consent not complete in cookie ? -> we accept by default
    console.error(`Cookie '${name}'' of type '${type}' not found in consents ${consents}.`);
    return true && result;
}

});
