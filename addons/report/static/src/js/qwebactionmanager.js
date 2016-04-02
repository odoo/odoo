odoo.define('report.report', function (require) {

var ActionManager = require('web.ActionManager');
var core = require('web.core');
var crash_manager = require('web.crash_manager');
var framework = require('web.framework');
var session = require('web.session');

var _t = core._t;
var wkhtmltopdf_state;

var trigger_download = function(session, response, c, action, options) {
    session.get_file({
        url: '/report/download',
        data: {data: JSON.stringify(response)},
        complete: framework.unblockUI,
        error: c.rpc_error.bind(c),
        success: function(){
            if (action && options && !action.dialog) {
                options.on_close();
            }
        },
    });
};

ActionManager.include({
    ir_actions_report_xml: function(action, options) {
        var self = this;
        framework.blockUI();
        action = _.clone(action);
        _t =  core._t;

        // QWeb reports
        if ('report_type' in action && (action.report_type == 'qweb-html' || action.report_type == 'qweb-pdf' || action.report_type == 'controller')) {
            var report_url = '';
            switch (action.report_type) {
                case 'qweb-html':
                    report_url = '/report/html/' + action.report_name;
                    break;
                case 'qweb-pdf':
                    report_url = '/report/pdf/' + action.report_name;
                    break;
                case 'controller':
                    report_url = action.report_file;
                    break;
                default:
                    report_url = '/report/html/' + action.report_name;
                    break;
            }

            // generic report: no query string
            // particular: query string of action.data.form and context
            if (!('data' in action) || !(action.data)) {
                if ('active_ids' in action.context) {
                    report_url += "/" + action.context.active_ids.join(',') + "?enable_editor=1";
                }
            } else {
                report_url += "?enable_editor=1";
                report_url += "&options=" + encodeURIComponent(JSON.stringify(action.data));
                report_url += "&context=" + encodeURIComponent(JSON.stringify(action.context));
            }

            var response = new Array();
            response[0] = report_url;
            response[1] = action.report_type;
            var c = crash_manager;

            if (action.report_type == 'qweb-html') {
                window.open(report_url, '_blank', 'scrollbars=1,height=900,width=1280');
                framework.unblockUI();
            } else if (action.report_type === 'qweb-pdf') {
                // Trigger the download of the pdf/controller report
                (wkhtmltopdf_state = wkhtmltopdf_state || session.rpc('/report/check_wkhtmltopdf')).then(function (presence) {
                    // Fallback on html if wkhtmltopdf is not installed or if OpenERP is started with one worker
                    if (presence === 'install') {
                        self.do_notify(_t('Report'), _t('Unable to find Wkhtmltopdf on this \
system. The report will be shown in html.<br><br><a href="http://wkhtmltopdf.org/" target="_blank">\
wkhtmltopdf.org</a>'), true);
                        report_url = report_url.substring(12);
                        window.open('/report/html/' + report_url, '_blank', 'height=768,width=1024');
                        framework.unblockUI();
                        return;
                    } else if (presence === 'workers') {
                        self.do_notify(_t('Report'), _t('You need to start OpenERP with at least two \
workers to print a pdf version of the reports.'), true);
                        report_url = report_url.substring(12);
                        window.open('/report/html/' + report_url, '_blank', 'height=768,width=1024');
                        framework.unblockUI();
                        return;
                    } else if (presence === 'upgrade') {
                        self.do_notify(_t('Report'), _t('You should upgrade your version of\
Wkhtmltopdf to at least 0.12.0 in order to get a correct display of headers and footers as well as\
support for table-breaking between pages.<br><br><a href="http://wkhtmltopdf.org/" \
target="_blank">wkhtmltopdf.org</a>'), true);
                    }
                    return trigger_download(self.session, response, c, action, options);
                });
            } else if (action.report_type === 'controller') {
                return trigger_download(self.session, response, c, action, options);
            }                     
        } else {
            return self._super(action, options);
        }
    }
});

});
