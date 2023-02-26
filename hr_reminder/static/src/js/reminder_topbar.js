odoo.define('hr_reminder.reminder_topbar', function (require) {
"use strict";

var core = require('web.core');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');
var QWeb = core.qweb;
var rpc = require('web.rpc');
var ajax = require('web.ajax');
var publicWidget = require('web.public.widget');
//var rem;
var reminder_menu = publicWidget.Widget.extend({
    template:'hr_reminder.reminder_menu',

    events: {
        "click .dropdown-toggle": "on_click_reminder",
        "click .reminders_list": "reminder_active",
    },

    willStart: function(){
            var self = this;
            self.all_reminder = [];
            return this._super()
            .then(function() {
             var def1 = ajax.jsonRpc("/hr_reminder/all_reminder", 'call',{}

            ).then(function(all_reminder){
            self.all_reminder = all_reminder

            });
        });
            },


    on_click_reminder: function (event) {
        var self = this
        self.all_reminder = []
         ajax.jsonRpc("/hr_reminder/all_reminder", 'call',{}
        ).then(function(all_reminder){
        self.all_reminder = all_reminder

        self.$('.reminders_list').html(QWeb.render('reminder_menu',{
                values: self.all_reminder,
                widget: self

            }));
        });
        },


    reminder_active: function(){

        var self = this;
        var value =$("#reminder_select").val();

        ajax.jsonRpc("/hr_reminder/reminder_active", 'call',{'reminder_name':value}
        ).then(function(reminder){
            self.reminder = reminder
            console.log('reminder on click selection',self.reminder)


             for (var i=0;i<1;i++){
                    var model = self.reminder[i]

                    var date = self.reminder[i+2]
                    var field = self.reminder[i+1]

                    var id = self.reminder[i+6]
                    var today = self.reminder[i+7]


                    if (self.reminder[i+2] == 'today'){

                        return self.do_action({
                             type: 'ir.actions.act_window',
                            res_model: model,
                            view_mode: 'list',

                            domain: [[field,'=',today]],
                            views: [[false, 'list']],
                            target: 'new',})
                        }

                    else if (self.reminder[i+2] == 'set_date'){
                        return self.do_action({
                            type: 'ir.actions.act_window',
                            res_model: model,
                            view_mode: 'list',
                            domain: [[date, '=', self.reminder[i+3]]],
                            views: [[false, 'list']],
                            target: 'new',
                            })
                        }

                    else if (self.reminder[i+2] == 'set_period'){
                        return self.do_action({
                            type: 'ir.actions.act_window',
                            res_model: model,
                            view_mode: 'list',
                            domain: [[date, '<', self.reminder[i+5]],[date, '>', self.reminder[i+4]]],
                            views: [[false, 'list']],
                            target: 'new',
                            })
                            }

                        }

             });
        },
});

SystrayMenu.Items.push(reminder_menu);
});
