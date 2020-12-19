odoo.define('activitytest', function (require) {
    "use strict";
    var core = require('web.core');
    var Widget = require('web.Widget');

    // �����ģ��
    var Echarts = Widget.extend({
        // ģ������ ��Ӧ����xml��t-name
        template: 'echarts_china_template',

        init: function(parent, data){
            return this._super.apply(this, arguments);
        },

        start: function(){
            return true;
        },


    });
    // �����涨��Ĵ�ģ��ע��ɿͻ��˶��� ��������Ӧclient_action�е�tag
    core.action_registry.add('activitytest.load_echarts_china', Echarts);
})