odoo.define('web.ReportService', function (require) {
"use strict";

/**
 * This file defines the service for the report generation in Odoo.
 */

var AbstractService = require('web.AbstractService');

var ReportService = AbstractService.extend({
    name: 'report',
    dependencies: ['ajax'],

    /**
     * Checks the state of the installation of wkhtmltopdf on the server.
     * Implements an internal cache to do the request only once.
     *
     * @returns {Deferred} resolved with the state of wkhtmltopdf on the server
     *   (possible values are 'ok', 'broken', 'install', 'upgrade', 'workers').
     */
    checkWkhtmltopdf: function () {
        if (!this.wkhtmltopdfState) {
            this.wkhtmltopdfState = this._rpc({
                route:'/report/check_wkhtmltopdf'
            });
        }
        return this.wkhtmltopdfState;
    },
});

return ReportService;

});
