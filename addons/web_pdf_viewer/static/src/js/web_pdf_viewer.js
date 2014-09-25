
openerp.web_pdf_viewer = function (openerp) {

    openerp.web.ActionManager.include({
        ir_actions_report_xml: function(action, options) {
            var self = this;
            openerp.web.blockUI();
            action = _.clone(action);
            action["pdf_viewer"] = false;

            var eval_contexts = ([openerp.session.user_context] || []).concat([action.context]);
            action.context = openerp.web.pyeval.eval('contexts',eval_contexts);

            if (navigator.userAgent.match(/(iPod|iPhone|iPad)/)) {
                self._super.apply(this, arguments);
            } else if((action.hasOwnProperty('report_type') && action.report_type == 'pdf')) {
                action["pdf_viewer"] = true;
                var c = openerp.webclient.crashmanager;
                return $.Deferred(function (d) {
                    self.session.show_pdf({
                        url: '/web/report',
                        data: {action: JSON.stringify(action)},
                        complete: openerp.web.unblockUI,
                        success: function(){
                            if (!self.dialog) {
                                options.on_close();
                            }
                            self.dialog_stop();
                            d.resolve();
                        },
                        error: function () {
                            c.rpc_error.apply(c, arguments);
                            d.reject();
                        }
                    });
                });
            }
            else self._super.apply(this, arguments);
        },
        
    });
    openerp.web.Session.include({
        show_pdf: function (options) {
            // need to detect when the file is done downloading (not used
            // yet, but we'll need it to fix the UI e.g. with a throbber
            // while dump is being generated), iframe load event only fires
            // when the iframe content loads, so we need to go smarter:
            // http://geekswithblogs.net/GruffCode/archive/2010/10/28/detecting-the-file-download-dialog-in-the-browser.aspx
            var timer, token = new Date().getTime(),
                cookie_name = 'fileToken', cookie_length = cookie_name.length,
                CHECK_INTERVAL = 1000, id = _.uniqueId('get_file_frame'),
                remove_form = false;


            // iOS devices doesn't allow iframe use the way we do it,
            // opening a new window seems the best way to workaround
            if (navigator.userAgent.match(/(iPod|iPhone|iPad)/)) {
                var params = _.extend({}, options.data || {}, {token: token});
                var url = this.url(options.url, params);
                instance.web.unblockUI();
                return window.open(url);
            }

            var $form, $form_data = $('<div>');
            
            var complete = function () {
                if (options.complete) {
                    options.complete();
                }
            };
            $('.oe_view_manager.oe_view_manager_current').children().hide();
            var height_window = ($(window).height()) - 32;
            var $target = $('<iframe style="top:100px;left:1px;z-index:500;width:100%;height:' + height_window + 'px;">')
                .attr({ id: id, name: id })
                .prependTo(".oe_view_manager.oe_view_manager_current");
                $('<a><iframe class="ie_problem" src="about:blank"></iframe><div class="close_print"><div><div>X</div><i>Close</i></div></div></a>')
                        .attr({id: 'close_print'})
                        .prependTo(".oe_view_manager.oe_view_manager_current");
                $("#close_print").click(function () {
                    clearTimeout(timer);
                    $form_data.remove();
                    $target.remove();
                    if (remove_form && $form) {
                        $form.remove();
                    }
                    $("#close_print").remove();
                    $('.oe_view_manager.oe_view_manager_current').children().show();
                });
            
            if (options.form) {
                $form = $(options.form);
            } else {
                remove_form = true;
                $form = $('<form>', {
                    action: options.url,
                    method: 'GET'
                }).appendTo(document.body);
            }

            var hparams = _.extend({}, options.data || {}, {token: token});
            if (this.override_session)
                hparams.session_id = this.session_id;
            _.each(hparams, function (value, key) {
                    var $input = $form.find('[name=' + key +']');
                    if (!$input.length) {
                        $input = $('<input type="hidden" name="' + key + '">')
                            .appendTo($form_data);
                    }
                    $input.val(value)
            });

            $form
                .append($form_data)
                .attr('target', id)
                .get(0).submit();

            var waitLoop = function () {
                var cookies = document.cookie.split(';');
                // setup next check
                timer = setTimeout(waitLoop, CHECK_INTERVAL);
                for (var i=0; i<cookies.length; ++i) {
                    var cookie = cookies[i].replace(/^\s*/, '');
                    if (!cookie.indexOf(cookie_name === 0)) { continue; }
                    var cookie_val = cookie.substring(cookie_length + 1);
                    if (parseInt(cookie_val, 10) !== token) { continue; }
    
                    // clear cookie
                    document.cookie = _.str.sprintf("%s=;expires=%s;path=/",
                        cookie_name, new Date().toGMTString());
                    if (options.success) { options.success(); }
                    complete();
                    return;
                }
            };
            timer = setTimeout(waitLoop, CHECK_INTERVAL);
        },
    });
};