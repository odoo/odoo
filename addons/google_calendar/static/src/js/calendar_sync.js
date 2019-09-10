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
                    alert(_t("You will be redirected to Google to authorize access to your calendar!"));
                    instance.web.redirect(o.url);
                }
                else if (o.status === "need_config_from_admin"){
                    if (!_.isUndefined(o.action) && parseInt(o.action)){
                        if (confirm(_t("The Google Synchronization needs to be configured before you can use it, do you want to do it now?"))) {
                            self.do_action(o.action);
                        }
                    }
                    else{
                        alert(_t("An administrator needs to configure Google Synchronization before you can use it!"));
                    }
                }
                else if (o.status === "need_refresh"){
                    self.$calendar.fullCalendar('refetchEvents');
                }
                else if (o.status === "need_reset"){
                    var confirm_text1 = _t("The account you are trying to synchronize (%s) is not the same as the last one used (%s)!");
                    var confirm_text2 = _t("In order to do this, you first need to disconnect all existing events from the old account.");
                    var confirm_text3 = _t("Do you want to do this now?");
                    var text = _.str.sprintf(confirm_text1 + "\n" + confirm_text2 + "\n\n" + confirm_text3, o.info.new_name, o.info.old_name);
                    if (confirm(text)) {
                        self.rpc('/google_calendar/remove_references', {
                            model:res.model,
                            local_context:context
                        }).done(function(o) {
                            if (o.status === "OK") {
                                alert(_t("All events have been disconnected from your previous account. You can now restart the synchronization"));
                            }
                            else if (o.status === "KO") {
                                alert(_t("An error occured while disconnecting events from your previous account. Please retry or contact your administrator."));
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
