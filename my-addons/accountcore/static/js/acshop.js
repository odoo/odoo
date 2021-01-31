odoo.define("accountcore.acshop", ['web.core', 'web.AbstractAction'], function (require) {
    'use strict';
    var core = require("web.core");
    var AbstractAction = require("web.AbstractAction");

    var acshop = AbstractAction.extend({
        template: 'acshop_site_page',
    })
    core.action_registry.add("acshop",acshop)
    return acshop;
});