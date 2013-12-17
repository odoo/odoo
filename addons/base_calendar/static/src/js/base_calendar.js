openerp.base_calendar = function(instance) {
    var _t = instance.web._t;
    var QWeb = instance.web.qweb;
    instance.base_calendar = {}
    

    instance.web.WebClient = instance.web.WebClient.extend({
        getMyNotifBox: function(me) {
            return $(me).closest(".ui-notify-message-style");
        },
        get_next_event: function() {
            var self= this;
            this.rpc("/calendar/NextNotify", { 
                type: "GET" 
            })
            .then( 
                function(result) { 
                    console.log(result);
                    _.each(result,  function(res) {
                        setTimeout(function() {
                            //If notification not already displayed, we add button and action on it
                            if (!($.find(".eid_"+res.event_id)).length) {
                                res.title = "<span class='link2event eid_" + res.event_id + "'>" + res.title + "</span>";
                                res.message += "<br/><br/><button class='link2showed oe_highlight oe_form oe_button'><span>OK</span></button> \
                                                <button class='link2event'>Details</button>                                                   \
                                                <button class='link2recall ' >Snooze</button> ";
                                a = self.do_notify(res.title,res.message,true);
                                
                                 $(".link2event").on('click', function() { 
                                    self.rpc("/web/action/load", {
                                        action_id: "base_calendar.action_crm_meeting_notify",
                                    }).then( function(r) { 
                                        r.res_id = res.event_id;
                                        return self.action_manager.do_action(r);                                         
                                    });
                                    
                                });
                                a.element.find(".link2recall").on('click',function() { 
                                    self.getMyNotifBox(this).find('.ui-notify-close').trigger("click");
                                });
                                
                                a.element.find(".link2showed").on('click',function() { 
                                    self.getMyNotifBox(this).find('.ui-notify-close').trigger("click");
                                    self.rpc("/calendar/NextNotify", { 
                                        type: "UPDATE" 
                                    });
                                });
                            }
                            //If notification already displayed in the past, we remove the css attribute which hide this notification
                            else if (self.getMyNotifBox($.find(".eid_"+res.event_id)).attr("style") !== ""){
                                self.getMyNotifBox($.find(".eid_"+res.event_id)).attr("style","");                                
                            }
                        },res.timer * 1000);
                    });
                }
            );
        },
        check_notifications: function() {
            var self= this;
            self.get_next_event();                        
            setInterval(function(){
                self.get_next_event();
            }, 5 * 60  * 1000 );
        },
        
        //Override the show_application of addons/web/static/src/js/chrome.js       
        show_application: function() {
            this._super();
            this.check_notifications();
        }
    });
    

    instance.base_calendar.invitation = instance.web.Widget.extend({

        init: function(parent, db, action, id, view, attendee_data) {
            this._super();
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
            if(view == "form") {
                action_url = _.str.sprintf('/?db=%s#id=%s&view_type=%s&model=crm.meeting', db, meeting_id, view, meeting_id);
            } else {
                action_url = _.str.sprintf('/?db=%s#view_type=%s&model=crm.meeting&action=%s',self.db,self.view,self.action);
            }
            var reload_page = function(){
                return location.replace(action_url);
            }
            reload_page();
        },
    });

    instance.web.form.Many2ManyAttendee = instance.web.form.FieldMany2ManyTags.extend({
        tag_template: "many2manyattendee",
        initialize_texttext: function() {
            return _.extend(this._super(),{
                html : {
                    tag: '<div class="text-tag"><div class="text-button"><a class="oe_invitation custom-edit"/><span class="text-label"/><a class="text-remove"/></div></div>'
                }
            });
        },
        map_tag: function(value){
            return _.map(value, function(el) {return {name: el[1], id:el[0], state: el[2]};})
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
                    $(tag_element[key]).find(".custom-edit").addClass(data[key][2])
                });
            }
        }
    });
    instance.web.form.widgets = instance.web.form.widgets.extend({
        'many2manyattendee' : 'instance.web.form.Many2ManyAttendee',
    });

    instance.base_calendar.event = function (db, action, id, view, attendee_data) {
        instance.session.session_bind(instance.session.origin).done(function () {
            new instance.base_calendar.invitation(null,db,action,id,view,attendee_data).appendTo($("body").addClass('openerp'));
        });
    }
    
    
    
    
   
};

