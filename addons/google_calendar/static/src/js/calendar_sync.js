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
        sync_calendar: function(res,button) {
            var self = this;
            var context = instance.web.pyeval.eval('context');
            //$('div.oe_cal_sync_button').hide();
            $('div.oe_cal_sync_button').prop('disabled',true);
            
            self.rpc('/google_calendar/sync_data', {
                arch: res.arch,
                fields: res.fields,
                model:res.model,
                fromurl: window.location.href,
                local_context:context
            }).done(function(o) {
                if (o.status == "need_auth") {
                    alert(_t("You will be redirected on gmail to authorize your OpenErp to access your calendar !"));
                    instance.web.redirect(o.url);
                }
                else if (o.status == "need_config_from_admin") {
                    
                    if (!_.isUndefined(o.action) && parseInt(o.action)) {
                        if (confirm(_t("An admin need to configure Google Synchronization before to use it, do you want to configure it now ? !"))) {
                            self.do_action(o.action);                        
                        }
                    }
                    else {
                        alert(_t("An admin need to configure Google Synchronization before to use it !"));
                    }
                }
                else if (o.status == "need_refresh"){
                    self.$calendar.fullCalendar('refetchEvents');
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
