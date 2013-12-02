/*---------------------------------------------------------
 * OpenERP web_calendar
 *---------------------------------------------------------*/

openerp.google_calendar = function(instance) {
    var _t = instance.web._t,
       _lt = instance.web._lt;
    var QWeb = instance.web.qweb;

    instance.web_calendar.FullCalendarView.include({
        view_loading: function(r) {
            var self = this;
            this.$el.on('click', 'div.oe_dhx_cal_sync_button', function() {
                self.sync_calendar(r);
            });
            return this._super(r);
        },
        sync_calendar: function(res) {
            var self = this;
            var context = instance.web.pyeval.eval('context');
            console.log("Model is..." + res.model);
            
            self.rpc('/web_calendar_sync/sync_calendar/sync_data', {
                arch: res.arch,
                fields: res.fields,
                model:res.model,
                fromurl: window.location.href,
                LocalContext:context
            }).always(function(o) {
                if (o.status == "NeedAuth") {
                    alert(_t("You will be redirected on gmail to authorize your OpenErp to access your calendar !"));
                    window.location = o.url;
                }
                console.log(o);
                //self.reload();
            });
        }
    });

};
