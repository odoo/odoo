odoo.define('l10n_fr_certification.check_moves_integrity', function (require) {
'use strict';
  
var core = require('web.core');
/**
* This client action simply displays a notification. It is useful when we
* do an action (such as a server action), that does not need to do anything,
* except give some feedback to the user.
* @param {ActionManager} parent
* @param {Object} action
* 
* @param {string} action.params.title
* @param {string} [action.params.message]
* @param {Boolean} [action.params.sticky = false]
*/

function NotifyUser (parent, action) {
    var message = action.params.message || '';
    var sticky = action.params.sticky || false;

    parent.do_notify(action.params.title, message, sticky);
}

core.action_registry.add("notify_user", NotifyUser);

});