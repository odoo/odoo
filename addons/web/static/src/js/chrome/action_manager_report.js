odoo.define('web.ReportActionPlugin', function (require) {
    "use strict";

    /**
     * The purpose of this file is to add the support of Odoo actions of type
     * 'ir.actions.report' to the ActionManager.
     */

    const ActionManager = require('web.ActionManager');
    const core = require('web.core');
    const session = require('web.session');

    const _t = core._t;
    const _lt = core._lt;

    // Messages that might be shown to the user dependening on the state of wkhtmltopdf
    const link = '<br><br><a href="http://wkhtmltopdf.org/" target="_blank">wkhtmltopdf.org</a>';
    const WKHTMLTOPDF_MESSAGES = {
        broken: _lt('Your installation of Wkhtmltopdf seems to be broken. The report will be shown ' +
                    'in html.') + link,
        install: _lt('Unable to find Wkhtmltopdf on this system. The report will be shown in ' +
                     'html.') + link,
        upgrade: _lt('You should upgrade your version of Wkhtmltopdf to at least 0.12.0 in order to ' +
                     'get a correct display of headers and footers as well as support for ' +
                     'table-breaking between pages.') + link,
        workers: _lt('You need to start Odoo with at least two workers to print a pdf version of ' +
                     'the reports.'),
    };

    class ReportActionPlugin extends ActionManager.AbstractPlugin {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Executes actions of type 'ir.actions.report'.
         *
         * @override
         */
        async executeAction(action, options) {
            if (action.report_type === 'qweb-html') {
                return this._executeReportClientAction(action, options);
            } else if (action.report_type === 'qweb-pdf') {
                // check the state of wkhtmltopdf before proceeding
                const state = await this.env.services.report.checkWkhtmltopdf();
                // display a notification according to wkhtmltopdf's state
                if (state in WKHTMLTOPDF_MESSAGES) {
                    this.env.services.notification.notify({
                        title: _t('Report'),
                        message: WKHTMLTOPDF_MESSAGES[state],
                        sticky: true,
                    });
                }
                if (state === 'upgrade' || state === 'ok') {
                    // trigger the download of the PDF report
                    return this._triggerDownload(action, options, 'pdf');
                } else {
                    // open the report in the client action if generating the PDF is not possible
                    return this._executeReportClientAction(action, options);
                }
            } else if (action.report_type === 'qweb-text') {
                return this._triggerDownload(action, options, 'text');
            } else {
                console.error(`The ActionManager can't handle reports of type ${action.report_type}`, action);
                return Promise.reject();
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * Downloads a PDF report for the given url. It blocks the UI during the
         * report generation and download.
         *
         * @private
         * @param {string} url
         * @returns {Promise} resolved when the report has been downloaded ;
         *   rejected if something went wrong during the report generation
         */
        _downloadReport(url) {
            this.env.services.blockUI();
            return new Promise((resolve, reject) => {
                const type = `qweb-${url.split('/')[2]}`;
                const blocked = !this.env.session.get_file({
                    url: '/report/download',
                    data: {
                        data: JSON.stringify([url, type]),
                        // AAB: the user_context should be automatically given by get_file
                        context: JSON.stringify(session.user_context),
                    },
                    success: resolve,
                    error: error => {
                        this.env.services.crash_manager.rpc_error(error);
                        reject();
                    },
                    complete: this.env.services.unblockUI,
                });
                if (blocked) {
                    // AAB: this check should be done in get_file service directly,
                    // should not be the concern of the caller (and that way, get_file
                    // could return a promise)
                    const message = _t('A popup window with your report was blocked. You ' +
                                     'may need to change your browser settings to allow ' +
                                     'popup windows for this page.');
                    this.env.services.notification.notify({
                        title: _t('Warning'),
                        type: 'danger',
                        message: message,
                        sticky: true,
                    });
                }
            });
        }
        /**
         * Executes the report client action, either because the report_type is
         * 'qweb-html', or because the PDF can't be generated by wkhtmltopdf (in
         * the case of 'qweb-pdf' reports).
         *
         * @private
         * @param {Object} action
         * @param {Object} [options]
         * @returns {Promise} resolved when the client action has been executed
         */
        _executeReportClientAction(action, options) {
            const urls = this._makeReportUrls(action);
            const clientActionOptions = Object.assign({}, options, {
                context: action.context,
                data: action.data,
                display_name: action.display_name,
                name: action.name,
                report_file: action.report_file,
                report_name: action.report_name,
                report_url: urls.html,
            });
            return this.doAction('report.client_action', clientActionOptions);
        }
        /**
         * Generates an object containing the report's urls (as value) for every
         * qweb-type we support (as key). It's convenient because we may want to use
         * another report's type at some point (for example, when `qweb-pdf` is not
         * available).
         *
         * @private
         * @param {Object} action
         * @returns {Object}
         */
        _makeReportUrls(action) {
            let reportUrls = {
                html: `/report/html/${action.report_name}`,
                pdf: `/report/pdf/${action.report_name}`,
                text: `/report/text/${action.report_name}`,
            };
            // We may have to build a query string with `action.data`. It's the place
            // were report's using a wizard to customize the output traditionally put
            // their options.
            if (action.data === undefined || action.data === null ||
                (_.isObject(action.data) && _.isEmpty(action.data))) {
                if (action.context.active_ids) {
                    const activeIDsPath = action.context.active_ids.join(',');
                    for (const type in reportUrls) {
                        reportUrls[type] = `${reportUrls[type]}/${activeIDsPath}`;
                    }
                }
            } else {
                const options = encodeURIComponent(JSON.stringify(action.data));
                const context = encodeURIComponent(JSON.stringify(action.context));
                for (const type in reportUrls) {
                    reportUrls[type] = `${reportUrls[type]}?${options}&${context}`;
                }
            }
            return reportUrls;
        }
        /**
         * @private
         * @param {Object} action the description of the action to execute
         * @param {Object} options
         * @param {function} options.on_close
         * @returns {Promise} resolved when the action has been executed
         */
        async _triggerDownload(action, options, type) {
            const reportUrls = this._makeReportUrls(action);
            await this._downloadReport(reportUrls[type]);
            if (action.close_on_report_download) {
                const closeAction = { type: 'ir.actions.act_window_close' };
                return this.doAction(closeAction, { on_close: options.on_close });
            } else {
                return options.on_close();
            }
        }
    }
    ReportActionPlugin.type = 'ir.actions.report';

    ActionManager.registerPlugin(ReportActionPlugin);

    return ReportActionPlugin;

});
