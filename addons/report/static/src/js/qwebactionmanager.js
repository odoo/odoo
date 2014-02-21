openerp.report = function(instance) {

    instance.web.ActionManager = instance.web.ActionManager.extend({
        ir_actions_report_xml: function(action, options) {
            var self = this;
            instance.web.blockUI();
            action = _.clone(action);
            var eval_contexts = ([instance.session.user_context] || []).concat([action.context]);
            action.context = instance.web.pyeval.eval('contexts',eval_contexts);

            // QWeb reports
            if ('report_type' in action && (action.report_type == 'qweb-html' || action.report_type == 'qweb-pdf' || action.report_type == 'controller')) {
                
                var report_url = ''
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
                    window.open(report_url);
                    instance.web.unblockUI();
                    return;
                } else {
                    // Trigger the download of the pdf/custom controller report
                    var c = openerp.webclient.crashmanager;
                    var response = new Array()
                    response[0] = report_url
                    response[1] = action.report_type

                    this.session.get_file({
                        url: '/report/download',
                        data: {data: JSON.stringify(response)},
                        complete: openerp.web.unblockUI,
                        error: c.rpc_error.bind(c)
                    });
                    return;
                }
            } else {
                return self._super(action, options);
            }
        }
    });
};
