openerp.report = function(instance) {

    instance.web.ActionManager = instance.web.ActionManager.extend({
        ir_actions_report_xml: function(action, options) {
            var self = this;
            instance.web.blockUI();
            action = _.clone(action);
            var eval_contexts = ([instance.session.user_context] || []).concat([action.context]);
            action.context = instance.web.pyeval.eval('contexts',eval_contexts);

            // QWeb reports
            if ('report_type' in action && (action.report_type == 'qweb-html' || action.report_type == 'qweb-pdf')) {
                var report_url = '';

                if (action.report_type == 'qweb-html') {
                    report_url = '/report/' + action.report_name;
                } else {
                    report_url = '/report/pdf/report/' + action.report_name;
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
                        if(key.substring(0, 12) === 'used_context') {
                            delete action.datas.form[key];                                
                        }

                        if ($.type(value) === 'array') {
                            action.datas.form[key] = value.join(',');
                        }
                    });
                    report_url += "?" + $.param(action.datas.form);
                }

                instance.web.unblockUI();
                window.open(report_url);
                return;
            } else {
                return self._super(action, options);
            }
        }
    });
};
