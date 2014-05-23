openerp.google_calendar = function(instance) {
    var _t = instance.web._t,
       _lt = instance.web._lt;
    var QWeb = instance.web.qweb;

    instance.web_calendar.CalendarView.include({
        view_loading: function(r) {
            var self = this;
            this.$el.on('click', 'div.oe_cal_sync_button', function() {
                self.sync_calendar(r);
            });
            return this._super(r);
        },
        sync_calendar: function(res, button) {
            var self = this;
            var context = instance.web.pyeval.eval('context');
            //$('div.oe_cal_sync_button').hide();
            $('div.oe_cal_sync_button').prop('disabled', true);

            self.rpc('/google_calendar/sync_data', {
                arch: res.arch,
                fields: res.fields,
                model: res.model,
                fromurl: window.location.href,
                local_context: context
            }).done(function(o) {
                if (o.status === "need_auth") {
                    alert(_t("You will be redirected on gmail to authorize your OpenErp to access your calendar !"));
                    instance.web.redirect(o.url);
                }
                else if (o.status === "need_config_from_admin"){
                    if (!_.isUndefined(o.action) && parseInt(o.action)){
                        if (confirm(_t("An admin need to configure Google Synchronization before to use it, do you want to configure it now ? !"))){
                            self.do_action(o.action);
                        }
                    }
                    else{
                        alert(_t("An admin need to configure Google Synchronization before to use it !"));
                    }
                }
                else if (o.status === "need_refresh"){
                    self.$calendar.fullCalendar('refetchEvents');
                }
                else if (o.status === "need_reset"){
                    if (confirm(_t("The account that you are trying to synchronize (" + o.info.new_name + "), is not the same that the last one used \
(" + o.info.old_name + "! )" + "\r\n\r\nDo you want remove all references from the old account ?"))){

                        self.rpc('/google_calendar/remove_references', {
                            model:res.model,
                            local_context:context
                        }).done(function(o) {
                            if (o.status === "OK") {
                                alert(_t("All old references have been deleted. You can now restart the synchronization"));
                            }
                            else if (o.status === "KO") {
                                alert(_t("An error has occured when we was removing all old references. Please retry or contact your administrator."));
                            }
                            //else NOP
                        });
                    }
                }
            }).always(function(o) { $('div.oe_cal_sync_button').prop('disabled',false); });
        }
    });
    
    instance.web_calendar.CalendarView.include({
        extraSideBar: function() {
            this._super();
            if (this.dataset.model == "calendar.event") {
                this.$el.find('.oe_calendar_filter').prepend(QWeb.render('GoogleCalendar.buttonSynchro'));
            }
        }
    });

};
