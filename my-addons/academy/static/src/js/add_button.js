odoo.define('academy.bicon_list_view_button', function (require) {
    "use strict";
    //这些是调⽤需要的模块
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');
    var ListController = require('web.ListController');
    //这块代码是继承ListController在原来的基础上进⾏扩展
    var BiConListController = ListController.extend({
        renderButtons: function () {
            this._super.apply(this, arguments);
            if (this.$buttons) {
                //这⾥找到刚才定义的class名为create_by_xf的按钮
                var btn = this.$buttons.find('.create_by_xf');
                //给按钮绑定click事件和⽅法create_data_by_dept
                btn.on('click', this.proxy('create_data_by_dept'));
            }
        },


        create_data_by_dept: function () {
            var self = this;
            console.log(self);
            //这⾥是获取tree视图中选中的数据的记录集
            
            var records = _.map(self.selectedRecords, function (id) {
                return self.model.localData[id];
            });
            if (self.selectedRecords.length == 0) {
                var allRecordKeys = self.model.localData[self.model.modelName + '1']?.data;
                records = _.map(allRecordKeys, function (id) {
                    return self.model.localData[id];
                });

            }
            //获取到数据集中每条数据的对应数据库id集合
            var ids = _.pluck(records, 'res_id');
            //通过rpc调⽤路由为/cheshi/hello的controller中的⽅法
            // this._rpc({
            // route: '/cheshi/hello',
            // params: {}
            // });
            this._rpc({
                model: 'ir.model.data',
                method: 'get_object_reference',
                args: ['academy', 'academy_teachers_list']
            }).then(function (view_ids) {
                self.do_action({
                    res_model: 'academy.teachers',
                    name: "Academy teachers",
                    views: [[view_ids[1], 'list']],
                    view_model: 'list',
                    view_type:'list',
                    target: 'current',
                    type: 'ir.actions.act_window',
                    context: {
                        "view_id": view_ids[1],
                        "mxids":ids
                    },
                    domain: '[("id","=",(' + ids + '))]',
                });
            });

            //通过rpc调⽤bs.warehouse模块中的my_function⽅法
            //this._rpc({
            //    model: 'academy.library.book.report',
            //    method: 'do_advanced_query',
            //    args: [ids],
            //}).then(function () {
            //    //location.reload();

            //});
        },

    });
    //这块代码是继承ListView在原来的基础上进⾏扩展
    //这块⼀般只需要在config中添加上⾃⼰的Model,Renderer,Controller
    //这⾥我就对原来的Controller进⾏了扩展编写，所以就配置了⼀下BiConListController
    var BiConListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: BiConListController,
        }),
    });
    //这⾥⽤来注册编写的视图BiConListView，第⼀个字符串是注册名到时候需要根据注册名调⽤视图
    viewRegistry.add('bicon_list_view_button', BiConListView);
    return BiConListView;
});
