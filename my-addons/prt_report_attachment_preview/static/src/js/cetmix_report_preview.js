/**********************************************************************************
* 
*    Copyright (C) 2020 Cetmix OÜ
*
*    This program is free software: you can redistribute it and/or modify
*    it under the terms of the GNU LESSER GENERAL PUBLIC LICENSE as
*    published by the Free Software Foundation, either version 3 of the
*    License, or (at your option) any later version.
*
*    This program is distributed in the hope that it will be useful,
*    but WITHOUT ANY WARRANTY; without even the implied warranty of
*    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
*    GNU LESSER GENERAL PUBLIC LICENSE for more details.
*
*    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
*    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*
**********************************************************************************/

odoo.define('prt_report_attachment_preview.ReportPreview', function (require) {
"use strict";

var ActionManager = require('web.ActionManager');
var core = require('web.core');
var _t = core._t;

// Action Manager
ActionManager.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Downloads a PDF report for the given url. It blocks the UI during the
     * report generation and download.
     *
     * @param {string} url
     * @returns {Deferred} resolved when the report has been downloaded ;
     *   rejected if something went wrong during the report generation
     */
    _downloadReport: function (url) {
        var def = $.Deferred();
        console.log("Report!",url)

        if (!window.open(url)) {
            // AAB: this check should be done in get_file service directly,
            // should not be the concern of the caller (and that way, get_file
            // could return a deferred)
            var message = _t('A popup window with your report was blocked. You ' +
                             'may need to change your browser settings to allow ' +
                             'popup windows for this page.');
            this.do_warn(_t('Warning'), message, true);
                    }

        return def;
            },
    })
});
