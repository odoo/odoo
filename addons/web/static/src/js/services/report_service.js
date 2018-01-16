odoo.define('web.ReportService', function (require) {
"use strict";

/**
 * This file defines the service for the report generation in Odoo.
 */

var AbstractService = require('web.AbstractService');
var session = require('web.session');

var wkhtmltopdfState;

var ReportService = AbstractService.extend({
    name: 'report',

    /**
     * Checks the state of the installation of wkhtmltopdf on the server.
     * Implements an internal cache to do the request only once.
     *
     * @returns {Deferred} resolved with the state of wkhtmltopdf on the server
     *   (possible values are 'ok', 'broken', 'install', 'upgrade', 'workers').
     */
    checkWkhtmltopdf: function () {
        if (!wkhtmltopdfState) {
            // AAB: for now, services aren't available for each other, so we
            // can't use this._rpc (the ajax service)
            wkhtmltopdfState = session.rpc('/report/check_wkhtmltopdf');
        }
        return wkhtmltopdfState;
    },
});

return ReportService;

});
