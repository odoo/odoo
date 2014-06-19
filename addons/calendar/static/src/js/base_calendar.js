openerp.calendar = function(instance) {
    var _t = instance.web._t;
    var QWeb = instance.web.qweb;

    instance.calendar = {};
    

    instance.web.WebClient = instance.web.WebClient.extend({
        

        get_notif_box: function(me) {
            return $(me).closest(".ui-notify-message-style");
        },
        get_next_notif: function() {
            var self= this;
            this.rpc("/calendar/notify")
            .done(
                function(result) {
                    _.each(result,  function(res) {
                        setTimeout(function() {
                            //If notification not already displayed, we add button and action on it
                            if (!($.find(".eid_"+res.event_id)).length) {
                                res.title = QWeb.render('notify_title', {'title': res.title, 'id' : res.event_id});
                                res.message += QWeb.render("notify_footer");
                                a = self.do_notify(res.title,res.message,true);
                                
                                $(".link2event").on('click', function() {
                                    self.rpc("/web/action/load", {
                                        action_id: "calendar.action_calendar_event_notify",
                                    }).then( function(r) {
                                        r.res_id = res.event_id;
                                        return self.action_manager.do_action(r);
                                    });
                                });
                                a.element.find(".link2recall").on('click',function() {
                                    self.get_notif_box(this).find('.ui-notify-close').trigger("click");
                                });
                                a.element.find(".link2showed").on('click',function() {
                                    self.get_notif_box(this).find('.ui-notify-close').trigger("click");
                                    self.rpc("/calendar/notify_ack");
                                });
                            }
                            //If notification already displayed in the past, we remove the css attribute which hide this notification
                            else if (self.get_notif_box($.find(".eid_"+res.event_id)).attr("style") !== ""){
                                self.get_notif_box($.find(".eid_"+res.event_id)).attr("style","");
                            }
                        },res.timer * 1000);
                    });
                }
            )
            .fail(function (err, ev) {
                if (err.code === -32098) {
                    // Prevent the CrashManager to display an error
                    // in case of an xhr error not due to a server error
                    ev.preventDefault();
                }
            });
        },
        check_notifications: function() {
            var self= this;
            self.get_next_notif();
            self.intervalNotif = setInterval(function(){
                self.get_next_notif();
            }, 5 * 60 * 1000 );
        },
        
        //Override the show_application of addons/web/static/src/js/chrome.js       
        show_application: function() {
            this._super();
            this.check_notifications();
        },
        //Override addons/web/static/src/js/chrome.js       
        on_logout: function() {
            this._super();
            clearInterval(self.intervalNotif);
        },
    });
    

    instance.calendar.invitation = instance.web.Widget.extend({

        init: function(parent, db, action, id, view, attendee_data) {
            this._super(parent); // ? parent ?
            this.db =  db;
            this.action =  action;
            this.id = id;
            this.view = view;
            this.attendee_data = attendee_data;
        },
        start: function() {
            var self = this;
            if(instance.session.session_is_valid(self.db) && instance.session.username != "anonymous") {
                self.redirect_meeting_view(self.db,self.action,self.id,self.view);
            } else {
                self.open_invitation_form(self.attendee_data);
            }
        },
        open_invitation_form : function(invitation){
            this.$el.html(QWeb.render('invitation_view', {'invitation': JSON.parse(invitation)}));
        },
        redirect_meeting_view : function(db, action, meeting_id, view){
            var self = this;
            var action_url = '';

            action_url = _.str.sprintf('/web?db=%s#id=%s&view_type=form&model=calendar.event', db, meeting_id);
            
            var reload_page = function(){
                return location.replace(action_url);
            };
            reload_page();
        },
    });

    instance.web.form.Many2ManyAttendee = instance.web.form.FieldMany2ManyTags.extend({
        tag_template: "many2manyattendee",
        initialize_texttext: function() {
            return _.extend(this._super(),{
                html : {
                        tag: QWeb.render('m2mattendee_tag')
                }
            });
        },
        map_tag: function(value){
            return _.map(value, function(el) {return {name: el[1], id:el[0], state: el[2]};});
        },
        get_render_data: function(ids){
            var self = this;
            var dataset = new instance.web.DataSetStatic(this, this.field.relation, self.build_context());
            return dataset.call('get_attendee_detail',[ids, self.getParent().datarecord.id || false]);
        },
        render_tag: function(data){
            this._super(data);
            var self = this;
            if (! self.get("effective_readonly")) {
                var tag_element = self.tags.tagElements();
                _.each(data,function(value, key){
                    $(tag_element[key]).find(".custom-edit").addClass(data[key][2]);
                });
            }
        }
    });
    instance.web.form.widgets = instance.web.form.widgets.extend({
        'many2manyattendee' : 'instance.web.form.Many2ManyAttendee',
    });

    instance.calendar.event = function (db, action, id, view, attendee_data) {
        instance.session.session_bind(instance.session.origin).done(function () {
            new instance.calendar.invitation(null,db,action,id,view,attendee_data).appendTo($("body").addClass('openerp'));
        });
    };
    
    
    
    
   
};

