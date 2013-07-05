openerp.base_calendar = function(instance) {
var _t = instance.web._t;
instance.base_calendar = {}

    instance.base_calendar.invite = instance.web.Widget.extend({

        init: function(parent,db,token,action,view_type,status) {
            this._super();
            this.db = db;
            this.token = token;
            this.status = status;
            this.action = action;
            this.view_type = view_type;
            this.ds_attendee = new instance.web.DataSetSearch(this, 'calendar.attendee');
        },
        start: function() {
            var self = this;
            if (instance.session.session_is_valid(self.db)) {
                self.show_meeting();
            } else {
                self.show_login()
            }
        },
        show_login: function(action) {
            var self =  this;
            this.destroy_content();
            this.login = new instance.web.Login_extended(this,self.action);
            this.login.appendTo(this.$el);
            this.login.on('db_loaded',self,function(db,login){
                if (instance.session.session_is_valid(db)) {
                    (self.show_meeting()).done(function(){
                        self.login.off('db_loaded');
                    });
                }
                else{
                    self.show_login();
                }
            })
        },
        destroy_content: function() {
            _.each(_.clone(this.getChildren()), function(el) {
                el.destroy();
            });
            this.$el.children().remove();
        },
        show_meeting : function(){
            var db = this.db;
            var att_status = "do_decline";
            var self = this;
            if(self.status === 'accepted'){att_status = "do_accept";}
            return this.ds_attendee.call(att_status,[[parseInt(this.token)]]).done(function(res){
                location.replace(_.str.sprintf('/?db=%s&debug=#view_type=%s&model=crm.meeting&action=%s&active_id=%s',self.db,self.view_type,self.action,self.token));
            });
        },
    });
    instance.web.Login_extended = instance.web.Login.extend({
        do_login: function (db, login, password) {
            var self = this;
            (this._super.apply(this,arguments)).done(function(){
               self.trigger('db_loaded',db,login)
            });
        }
    });
    instance.base_calendar.event = function (db, token, action, view_type, status) {
        instance.session.session_bind(instance.session.origin).done(function () {
            new instance.base_calendar.invite(null,db,token,action,view_type,status).appendTo($("body").addClass('openerp'));
        });
    }
};
//vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
