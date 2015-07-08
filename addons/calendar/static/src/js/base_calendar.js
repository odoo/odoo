odoo.define('base_calendar.base_calendar', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var form_common = require('web.form_common');
var Model = require('web.DataModel');
var WebClient = require('web.WebClient');
var CalendarView = require('web_calendar.CalendarView');
var widgets = require('web_calendar.widgets');

var FieldMany2ManyTags = core.form_widget_registry.get('many2many_tags');
var _t = core._t;
var _lt = core._lt;
var QWeb = core.qweb;


function reload_favorite_list(result) {
    var self = result;
    var current = result;
    if (result.view) {
        self = result.view;
    }
    new Model("res.users")
    .query(["partner_id"])
    .filter([["id", "=",self.dataset.context.uid]])
    .first()
    .done(function(result) {
        var sidebar_items = {};
        var filter_value = result.partner_id[0];
        var filter_item = {
            value: filter_value,
            label: result.partner_id[1] + _lt(" [Me]"),
            color: self.get_color(filter_value),
            avatar_model: self.avatar_model,
            is_checked: true,
            is_remove: false,
        };

        sidebar_items[0] = filter_item ;
        filter_item = {
                value: -1,
                label: _lt("Everybody's calendars"),
                color: self.get_color(-1),
                avatar_model: self.avatar_model,
                is_checked: false
            };
        sidebar_items[-1] = filter_item ;
        //Get my coworkers/contacts
        new Model("calendar.contacts").query(["partner_id"]).filter([["user_id", "=",self.dataset.context.uid]]).all().then(function(result) {
            _.each(result, function(item) {
                filter_value = item.partner_id[0];
                filter_item = {
                    value: filter_value,
                    label: item.partner_id[1],
                    color: self.get_color(filter_value),
                    avatar_model: self.avatar_model,
                    is_checked: true
                };
                sidebar_items[filter_value] = filter_item ;
            });
            self.all_filters = sidebar_items;
            self.now_filter_ids = $.map(self.all_filters, function(o) { return o.value; });
            
            self.sidebar.filter.events_loaded(self.all_filters);
            self.sidebar.filter.set_filters();
            self.sidebar.filter.set_distroy_filters();
            self.sidebar.filter.addInputBox();
            self.sidebar.filter.destroy_filter();
        }).done(function () {
            self.$calendar.fullCalendar('refetchEvents');
            if (current.ir_model_m2o) {
                current.ir_model_m2o.set_value(false);
            }
        });
    });
}

CalendarView.include({
    extraSideBar: function(){
        this._super();
        if (this.useContacts){
            new reload_favorite_list(this);
        }
    }
});

widgets.SidebarFilter.include({
    set_distroy_filters: function() {
        var self = this;
        // When mouse-enter the favorite list it will show the 'X' for removing partner from the favorite list.
        if (self.view.useContacts){
            self.$('.oe_calendar_all_responsibles').on('mouseenter mouseleave', function(e) {
                self.$('.oe_remove_follower').toggleClass('hidden', e.type == 'mouseleave');
            });
        }
    },
    addInputBox: function() {
        var self = this;
        if (this.dfm)
            return;
        this.dfm = new form_common.DefaultFieldManager(self);
        this.dfm.extend_field_desc({
            partner_id: {
                relation: "res.partner",
            },
        });
        var FieldMany2One = core.form_widget_registry.get('many2one');
        this.ir_model_m2o = new FieldMany2One(self.dfm, {
            attrs: {
                class: 'oe_add_input_box',
                name: "partner_id",
                type: "many2one",
                options: '{"no_open": True}',
                placeholder: _t("Add Favorite Calendar"),
            },
        });
        this.ir_model_m2o.insertAfter($('div.oe_calendar_filter'));
        this.ir_model_m2o.on('change:value', self, function() { 
            self.add_filter();
        });
    },
    add_filter: function() {
        var self = this;
        new Model("res.users")
        .query(["partner_id"])
        .filter([["id", "=",this.view.dataset.context.uid]])
        .first()
        .done(function(result){
            $.map(self.ir_model_m2o.display_value, function(element,index) {
                if (result.partner_id[0] != index){
                    self.ds_message = new data.DataSetSearch(self, 'calendar.contacts');
                    self.ds_message.call("create", [{'partner_id': index}]);
                }
            });
        });
        new reload_favorite_list(this);
    },
    destroy_filter: function(e) {
        var self= this;
        this.$(".oe_remove_follower").on('click', function(e) {
            self.ds_message = new data.DataSetSearch(self, 'calendar.contacts');
            if (! confirm(_t("Do you really want to delete this filter from favorite?"))) { return false; }
            var id = $(e.currentTarget)[0].dataset.id;
            self.ds_message.call('search', [[['partner_id', '=', parseInt(id)]]]).then(function(record){
                return self.ds_message.unlink(record);
            }).done(function() {
                new reload_favorite_list(self);
            });
        });
    },
});

WebClient.include({
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
                            var a = self.do_notify(res.title,res.message,true);
                            
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
        clearInterval(this.intervalNotif);
    },
});

var Many2ManyAttendee = FieldMany2ManyTags.extend({
    tag_template: "Many2ManyAttendeeTag",
    get_render_data: function(ids){
        var dataset = new data.DataSetStatic(this, this.field.relation, this.build_context());
        return dataset.call('get_attendee_detail',[ids, this.getParent().datarecord.id || false]);
    }
});

core.form_widget_registry.add('many2manyattendee', Many2ManyAttendee);

});
