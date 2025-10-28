/** @odoo-module **/
import { registry } from '@web/core/registry';
//const  { Component, useState } = owl
import { Component, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
class ReminderMenu extends Component {
//   Setup function which will run after the component is constructed
    setup(){
        this.action = useService("action");
        this.select = useRef('reminder_menu');
        this.reminder = [];
        this.rpc = this.env.services.rpc
        this.state = useState({
            all_remainders:[],
        })
    }
//    Function to work when clicked on the reminder in systray
    async showReminder(ev){
        ev.stopPropagation();
        ev.preventDefault();
        const data= await rpc("/hr_reminder/all_reminder")
        this.state.all_remainders = data
    }
//    Function to work when clicked on the view button from systray
    async reminderActive(ev){
        ev.stopPropagation();
        ev.preventDefault();
        var self = this;
        var value = (this.select.el.querySelector("#reminder_select")).value;
        await rpc('/hr_reminder/reminder_active', {'reminder_name':value}).then(function(current){
            self.reminder = current
            for (var i=0; i<1; i++){
                const Action = {
                            type: 'ir.actions.act_window',
                            res_model: self.reminder[i],
                            view_mode: 'list',
                            views: [[false, 'list']],
                            target: 'new',
                            context: { create: false}
                        };
                if (self.reminder[i+2] === 'today') {
                    const domain = [
                                [self.reminder[i+1], '>=', `${self.reminder[i+7]} 00:00:00`],
                                [self.reminder[i+1], '<=', `${self.reminder[i+7]} 23:59:59`]
                            ];
                    return self.action.doAction({ ...Action, domain });
                }
                else if (self.reminder[i+2] == 'set_date'){
                    const domain = [
                            [self.reminder[i+1], '>=', `${self.reminder[i+10]} 00:00:00`],
                            [self.reminder[i+1], '<=', `${self.reminder[i+3]} 23:59:59`]
                        ];
                    return self.action.doAction({ ...Action, domain });
                }
                else if (self.reminder[i+2] == 'set_period'){
                    const domain = [
                            [self.reminder[i+1], '>=', `${self.reminder[i+4]} 00:00:00`],
                            [self.reminder[i+1], '<=', `${self.reminder[i+5]} 23:59:59`]
                        ];
                    return self.action.doAction({ ...Action, domain });
                }
            }
        })
    }
}
ReminderMenu.template = 'owl.reminder_menu'
const Systray = {
    Component: ReminderMenu,
}
registry.category("systray").add("reminder_menu", Systray)
