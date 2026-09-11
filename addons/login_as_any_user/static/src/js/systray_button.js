/** @odoo-module**/
import SystrayMenu from 'web.SystrayMenu';
import Widget from 'web.Widget';
var rpc = require('web.rpc');
var ajax = require('web.ajax');
/**
 * We define this module for the function of wizard button
 *
 */
var UserSwitchWidget = Widget.extend({
    template: 'UserSwitchSystray',
    events: {
        'click #switch_user': '_onClick',
    },
    /**
    * Click function for opening wizard and returning back to the user
    */
    _onClick: function() {
        var self=this
        ajax.jsonRpc('/switch/user', 'call', {}).then(function(result) {
            if (result == true) {
                self.do_action({
                    type: 'ir.actions.act_window',
                    name: 'Switch User',
                    res_model: 'user.selection',
                    view_mode: 'form',
                    views: [
                        [false, 'form']
                    ],
                    target: 'new'
                })
            }else{
                ajax.jsonRpc('/switch/admin', 'call', {}).then(function(){
                    location.reload();
                })
            }
        })
    }
})
SystrayMenu.Items.push(UserSwitchWidget)
export default UserSwitchWidget