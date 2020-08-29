/* Copyright 2017 Openworx.
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

odoo.define('backend_theme_v13.sidebar-toggle', function (require) {
    "use strict";
    
    var session = require('web.session');
    var rpc = require('web.rpc');
    var id = session.uid;
    rpc.query({
                model: 'res.users',
                method: 'read',
                args: [[id], ['sidebar_visible']],
            }).then(function(res) {
                var dbfield = res[0];
                var toggle = dbfield.sidebar_visible;
                if (toggle === true) {
                    $("#app-sidebar").removeClass("toggle-sidebar");
                } else {
                    $("#app-sidebar").addClass("toggle-sidebar");
                };
    });
                             
});
    
