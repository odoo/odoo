/*---------------------------------------------------------
 * OpenERP base_calendar
 *---------------------------------------------------------*/

openerp.base_calendar = function(openerp) {

openerp.base_calendar.CalendarView = openerp.base.Controller.extend({
// Dhtmlx scheduler ?
});

//openerp.base.Action = openerp.base.Action.extend({
//    do_action_window: function(action) {
//        this._super.apply(this,arguments);
//        for(var i = 0; i < action.views.length; i++)  {
//            if(action.views[i][1] == "calendar") {
//                this.calendar_id = action.views[i][0];
//                break;
//            }
//        }
//        // IF there is a view calender
//        // if(this.calendar_id
//    },
//});

};

// DEBUG_RPC:rpc.request:('execute', 'addons-dsh-l10n_us', 1, '*', ('ir.filters', 'get_filters', u'res.partner'))
// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
