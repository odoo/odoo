odoo.define('activitytest', function (require) {
    "use strict";
    var core = require('web.core');
    var Widget = require('web.Widget');

    // 定义打开模板
    var Echarts = Widget.extend({
        // 模板名称 对应上面xml中t-name
        template: 'echarts_china_template',

        init: function(parent, data){
            return this._super.apply(this, arguments);
        },

        start: function(){
            return true;
        },


    });
    // 将上面定义的打开模板注册成客户端动作 动作名对应client_action中的tag
    core.action_registry.add('activitytest.load_echarts_china', Echarts);
})