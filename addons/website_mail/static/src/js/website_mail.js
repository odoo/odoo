odoo.define('website_mail.thread', function(require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');

var qweb = core.qweb;

var PortalChatter = require('portal.chatter').PortalChatter;

/**
 * Extends Frontend Chatter to handle rating
 */
PortalChatter.include({
    _loadTemplates: function(){
        return $.when(this._super(), ajax.loadXML('/website_mail/static/src/xml/website_mail.xml', qweb));
    },
});

});
