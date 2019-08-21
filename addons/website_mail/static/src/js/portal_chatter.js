odoo.define('website_mail.thread', function (require) {
'use strict';

var portalChatter = require('portal.chatter');

/**
 * Extends Frontend Chatter to handle rating
 */
portalChatter.PortalChatter.include({
    xmlDependencies: (portalChatter.PortalChatter.prototype.xmlDependencies || [])
        .concat(['/website_mail/static/src/xml/portal_chatter.xml']),
});
});
