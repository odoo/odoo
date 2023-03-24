odoo.define('hr.OpenChatLegacy', function (require) {
"use strict";

const widgetRegistry = require('web.widget_registry');
const Widget = require('web.Widget');

const HrEmployeeChatLegacy = Widget.extend({
    template: 'hr.OpenChatLegacy',
});

// TODO KBA remove when Studio converted to Owl
widgetRegistry.add('hr_employee_chat', HrEmployeeChatLegacy);
});
