/** @odoo-module **/

import cookieUtils from 'web.utils.cookies';

const originFunc = cookieUtils.isAllowedCookie;
cookieUtils.isAllowedCookie = (type) => {
    const result = originFunc.apply(cookieUtils, [type]);
    if (result && type === 'optional') {
        if (!document.getElementById('cookies-consent-essential')) {
            // Cookies bar is disabled on this website.
            return true;
        }
        const consents = JSON.parse(cookieUtils.getCookie('website_cookies_bar') || '{}');

        // pre-16.0 compatibility, `website_cookies_bar` was `"true"`.
        // In that case we delete that cookie and let the user choose again.
        if (typeof consents !== 'object') {
            cookieUtils.deleteCookie('website_cookies_bar');
            return false;
        }

        if ('optional' in consents) {
            return consents['optional'];
        }
        return false;
    }
    // Pass-through if already forbidden for another reason or a type that is
    // not restricted by the website module.
    return result;
};
