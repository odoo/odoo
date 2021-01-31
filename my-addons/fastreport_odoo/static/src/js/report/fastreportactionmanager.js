odoo.define('fastreport_action.report', function (require) {
    'use strict';

    var core = require("web.core");
    var ActionManager = require("web.ActionManager");
   // var crash_manager = require("web.crash_manager");
    var framework = require("web.framework");
    var session = require("web.session");
    var rpc = require("web.rpc")
    var _t = core._t;
    var ReportClientAction = require("report.client_action")

    ActionManager.include({

        _executeReportAction: function (action, options) {
            var self = this;
            if (action.report_type === 'fastreport') {
                return self._triggerDownload(action, options, 'fastreport');
            }
            return this._super.apply(this, arguments);
        },

        _downloadReportJasper: async function (url, actions,options) {
           
            var self = this;
            var def = $.Deferred();
            var type = "fastreport";
            var cloned_action = _.clone(actions);

            if (_.isUndefined(cloned_action.data) ||
                _.isNull(cloned_action.data) ||
                (_.isObject(cloned_action.data) &&
                    _.isEmpty(cloned_action.data))) {
                if (cloned_action.context.active_ids) {
                    url += "/" + cloned_action.context.active_ids.join(',');
                }
            } else {
                url += "?options=" + encodeURIComponent(
                    JSON.stringify(cloned_action.data));
                url += "&context=" + encodeURIComponent(
                    JSON.stringify(cloned_action.context));
            }

            //let test_model = await rpc.query({
            //    model: actions.type,
            //    method: 'get_test_data',
            //    args: []
            //});


            let is_download = false;
            let is_client_open = false;
            let rpt_model = await rpc.query({
                model: actions.type,
                method: 'get_report_from_name',
                args: [actions.report_name],
                limit: 1
            })
            if (rpt_model) {
                is_download = rpt_model.is_download;
                is_client_open = rpt_model.is_client_open;
            }
            if (is_client_open) {
                return this._executeReportClientAction(actions, options, type);
            } else {
                if (!is_download) {
                    return self._downloadReport(url);
                }
            }

            framework.blockUI();
            var blocked = !session.get_file({
                url: url,
                data: {
                    data: JSON.stringify([url, type]),
                },
                success: def.resolve.bind(def),
                error: function () {
                   // crash_manager.rpc_error.apply(crash_manager, arguments);
                    def.reject();
                },
                complete: framework.unblockUI,
            });
            if (blocked) {
                // AAB: this check should be done in get_file service directly,
                // should not be the concern of the caller
                // (and that way, get_file could return a deferred)
                var message = _t(
                    'A popup window with your report was blocked. You ' +
                    'may need to change your browser settings to allow ' +
                    'popup windows for this page.');
                this.do_warn(_t('Warning'), message, true);
            }
            return def;
        },

        _triggerDownload: function (action, options, type) {
            var self = this;
            var reportUrls = this._makeReportUrls(action);
            if (type === "fastreport") {
                return this._downloadReportJasper(
                    reportUrls[type], action,options).then(function () {
                    if (action.close_on_report_download) {
                        var closeAction = {
                            type: 'ir.actions.act_window_close',
                        };
                        return self.doAction(
                            closeAction, _.pick(options, 'on_close'));
                    } else {
                        return options.on_close();
                    }
                });
            }
            return this._super.apply(this, arguments);
        },
        _executeReportClientAction: function (action, options,type) {

            var self = this;
            var reportUrls = this._makeReportUrls(action);
            if (type === "fastreport") {
                var clientActionOptions = _.extend({}, options, {
                    context: action.context,
                    data: action.data,
                    display_name: action.display_name,
                    name: action.name,
                    report_file: action.report_file,
                    report_name: action.report_name,
                    report_url: reportUrls.fastreport,
                });
                return this.doAction('report.client_action', clientActionOptions);
            }
            return this._super.apply(this, arguments);
        },

        _makeReportUrls: function (action) {
            var reportUrls = this._super.apply(this, arguments);
            reportUrls.fastreport = '/report/fastreport/' + action.report_name;
            return reportUrls;
        },
        _downloadReport: function (url) {
            var def = $.Deferred();
            console.log("Report!", url)

            if (!window.open(url)) {
                // AAB: this check should be done in get_file service directly,
                // should not be the concern of the caller (and that way, get_file
                // could return a deferred)
                var message = _t('A popup window with your report was blocked. You ' +
                    'may need to change your browser settings to allow ' +
                    'popup windows for this page.');
                this.displayNotification({
                    type: 'Warning',
                    title: title,
                    message: message,
                    sticky: true,
                });
                //this.do_warn(_t('Warning'), message, true);
            }

            return def;
        },

    });

    ReportClientAction.include(
        {
            on_click_print: function () {
                var self = this;
                if (self.report_url.includes("/fastreport/")) {
                    //self.iframe.contentWindow.postMessage({
                    //    message:""}, '*');
                    //self.iframe.contentWindow.print();
                    if (!window.open(self.report_url)) {

                        var message = _t('A popup window with your report was blocked. You ' +
                            'may need to change your browser settings to allow ' +
                            'popup windows for this page.');
                        this.displayNotification({
                            type: 'Warning',
                            title: title,
                            message: message,
                            sticky: true,
                        });
                        //this.do_warn(_t('Warning'), message, true);
                    }
                } else {
                    return this._super.apply(this, arguments);
                }
                //var action = {
                //    'type': 'ir.actions.report',
                //    'report_type': 'fastreport',
                //    'report_name': this.report_name,
                //    'report_file': this.report_file,
                //    'data': this.data,
                //    'context': this.context,
                //    'display_name': this.title,
                //};
                //return this.do_action(action);
                
            }
        }

    );
});
