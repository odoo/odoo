odoo.define('website.website', function (require) {
'use strict';

var session = require('web.session');

session.user_context.website_id = html.getAttribute('data-website-id') | 0;

});
