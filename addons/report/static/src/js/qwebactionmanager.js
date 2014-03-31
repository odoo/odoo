openerp.report = function(instance) {
    var wkhtmltopdf_state;

    instance.web.ActionManager = instance.web.ActionManager.extend({
        ir_actions_report_xml: function(action, options) {
            var self = this;
            instance.web.blockUI();
            action = _.clone(action);
            var eval_contexts = ([instance.session.user_context] || []).concat([action.context]);
            action.context = instance.web.pyeval.eval('contexts',eval_contexts);
            _t =  instance.web._t;

            // QWeb reports
            if ('report_type' in action && (action.report_type == 'qweb-html' || action.report_type == 'qweb-pdf' || action.report_type == 'controller')) {
                var report_url = '';
                switch (action.report_type) {
                    case 'qweb-html':
                        report_url = '/report/' + action.report_name;
                        break;
                    case 'qweb-pdf':
                        report_url = '/report/pdf/report/' + action.report_name;
                        break;
                    case 'controller':
                        report_url = action.report_file;
                        break;
                    default:
                        report_url = '/report/' + action.report_name;
                        break;
                }

                // single/multiple id(s): no query string
                // wizard: query string of action.datas.form
                if (!('datas' in action)) {
                    if ('active_ids' in action.context) {
                        report_url += "/" + action.context.active_ids.join(',');
                    }
                } else {
                    _.each(action.datas.form, function(value, key) {
                        // will be erased when all wizards are rewritten
                        if (key.substring(0, 12) === 'used_context') {
                            delete action.datas.form[key];                                
                        }

                        if ($.type(value) === 'array') {
                            action.datas.form[key] = value.join(',');
                        }
                    });
                    report_url += "?" + $.param(action.datas.form);
                }
                if (action.report_type == 'qweb-html') {
                    // Open the html report in a popup
                    window.open(report_url, '_blank', 'height=900,width=1280');
                    instance.web.unblockUI();
                    return;
                } else {
                    // Trigger the download of the pdf/controller report
                    var c = openerp.webclient.crashmanager;
                    var response = new Array();
                    response[0] = report_url;
                    response[1] = action.report_type;

                    if (action.report_type == 'qweb-pdf') {
                        (wkhtmltopdf_state = wkhtmltopdf_state || openerp.session.rpc('/report/check_wkhtmltopdf')).then(function (presence) {
                            // Fallback of qweb-pdf if wkhtmltopdf is not installed
                            if (presence == 'install' && action.report_type == 'qweb-pdf') {
                                self.do_notify(_t('Report'), _t('Unable to find Wkhtmltopdf on this \
    system. The report will be shown in html.<br><br><a href="http://wkhtmltopdf.org/" target="_blank">\
    wkhtmltopdf.org</a>'), true);
                                window.open(report_url.substring(12), '_blank', 'height=768,width=1024');
                                instance.web.unblockUI();
                            } else {
                                if (presence == 'upgrade') {
                                    self.do_notify(_t('Report'), _t('You should upgrade your version of\
     Wkhtmltopdf to at least 0.12.0 in order to get a correct display of headers and footers as well as\
     support for table-breaking between pages.<br><br><a href="http://wkhtmltopdf.org/" \
     target="_blank">wkhtmltopdf.org</a>'), true);
                                }
                                self.session.get_file({
                                    url: '/report/download',
                                    data: {data: JSON.stringify(response)},
                                    complete: openerp.web.unblockUI,
                                    error: c.rpc_error.bind(c)
                                });
                            }
                        });
                    } else {
                        self.session.get_file({
                            url: '/report/download',
                            data: {data: JSON.stringify(response)},
                            complete: openerp.web.unblockUI,
                            error: c.rpc_error.bind(c)
                        });          
                    }   
                }                     
            } else {
                return self._super(action, options);
            }
        }
    });
};
