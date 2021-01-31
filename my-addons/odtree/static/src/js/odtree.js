// ##############################################################################
// #    odtree
// #    author:15251908@qq.com (openliu)
// #    license:'LGPL-3
// #
// ##############################################################################
odoo.define('odtree', function (require) {
    "use strict";

    var core = require('web.core');
    var ajax = require('web.ajax');
    var ListController = require('web.ListController');
    var ListRenderer = require('web.ListRenderer');
    var KanbanController = require('web.KanbanController');
    var KanbanRenderer = require('web.KanbanRenderer');
    var qweb = core.qweb;

    var node_id_selected = 0;
    var treejson = [];
    var treeObj;
    var last_view_type;
    var controller;
    var renderer;


    var buildTree = function () {
        var categ_model=renderer.arch.attrs.categ_model;
        var categ_property=renderer.arch.attrs.categ_property;
        var categ_parent_key=renderer.arch.attrs.categ_parent_key;
        var setting = {
            data: {
                simpleData: {
                    enable: true
                }
            },
            callback: {
                onClick: function (event, treeId, treeNode, clickFlag) {
                    node_id_selected = treeNode.id;
                    var search_view = controller.searchView;
                    var search_data = search_view.build_search_data();
                    var domains = search_data.domains;
                    if (categ_property && categ_model) {
                        if (node_id_selected != null && node_id_selected > 0) {
                            var include_children = renderer.getParent().$('#include_children').get(0).checked;
                            var operation = include_children ? 'child_of' : '=';
                            domains[domains.length] = [[categ_property, operation, node_id_selected]];
                        }
                    }
                    search_view.trigger_up('search', search_data);
                }
            }
        };
        if (controller.searchView==undefined){
            $('.o_list_view_categ').hide();
            return true

        }


        var fields = ['id', 'name'];
        if (categ_parent_key != null) {
            fields.push(categ_parent_key);
        }
        var ctx =renderer.state.getContext();
        ajax.jsonRpc('/web/dataset/call_kw', 'call', {
            model: categ_model,
            method: 'search_read',
            args: [],
            kwargs: {
                domain: [],
                fields: fields,
                order: 'id asc',
                context: ctx
            }
        }).then(function (respdata) {
            if (respdata.length > 0) {
                var treejson_cur = [];
                for (var index = 0; index < respdata.length; index++) {
                    var obj = respdata[index];
                    var parent_id = 0;
                    if (obj.hasOwnProperty(categ_parent_key)) {
                        parent_id = obj[categ_parent_key];
                        if (parent_id) {
                            parent_id = parent_id[0];
                        }
                    }
                    treejson_cur.push({id: obj['id'], pId: parent_id, name: obj['name'], open: true});
                }
                if (renderer.getParent().$('.o_list_view_categ').length === 0
                     || last_view_type !== renderer.viewType
                     || (JSON.stringify(treejson) !== JSON.stringify(treejson_cur))) {
                    last_view_type =renderer.viewType;
                    renderer.getParent().$('.o_list_view_categ').remove();
                    renderer.getParent().$('.o_kanban_view').addClass(' col-xs-12 col-md-10');
                    treejson=treejson_cur;
                    var fragment = document.createDocumentFragment();
                    var content = qweb.render('Odtree');
                    $(content).appendTo(fragment);
                    renderer.getParent().$el.prepend(fragment);
                    treeObj = $.fn.zTree.init(renderer.getParent().$('.ztree'), setting, treejson);
                    renderer.getParent().$(".handle_menu_arrow").on('click', function (e) {
                       if ( renderer.getParent().$('.handle_menu_arrow').hasClass("handle_menu_arrow_left")){
                            renderer.getParent().$('.odtree_control_panel').css("display","none");
                            renderer.getParent().$('.o_list_view_categ').css("border-right", "0px");
                            renderer.getParent().$('.handle_menu_arrow').removeClass("handle_menu_arrow_left");
                            renderer.getParent().$('.handle_menu_arrow').addClass("handle_menu_arrow_right");
                            renderer.getParent().$('.ztree').css("display","none");
                            renderer.getParent().$('.o_list_view_categ').removeClass('col-xs-12 col-md-2');
                            renderer.getParent().$('.o_list_view_categ').addClass('o_list_view_categ_hidden');
                            renderer.getParent().$('.o_kanban_view').removeClass(' col-xs-12 col-md-10');
                       }else{
                            renderer.getParent().$('.odtree_control_panel').css("display","block");
                            renderer.getParent().$('.o_list_view_categ').css({"border-right": "1px solid #b9b9b9"});
                            renderer.getParent().$('.handle_menu_arrow').removeClass("handle_menu_arrow_right");
                            renderer.getParent().$('.handle_menu_arrow').addClass("handle_menu_arrow_left");
                            renderer.getParent().$('.ztree').css("display","block");
                            renderer.getParent().$('.o_list_view_categ').removeClass('o_list_view_categ_hidden');
                            renderer.getParent().$('.o_list_view_categ').addClass('col-xs-12 col-md-2');
                            renderer.getParent().$('.o_kanban_view').addClass(' col-xs-12 col-md-10');
                       }
                    });
                }
                if (node_id_selected != null && node_id_selected > 0) {
                    var node = treeObj.getNodeByParam('id', node_id_selected, null);
                    treeObj.selectNode(node);
                }
            }
        });

    };

    ListController.include({
        renderPager: function () {
            controller=this;
            return this._super.apply(this, arguments);
        }
    });

    KanbanController.include({
        renderPager: function () {
            controller=this;
            return this._super.apply(this, arguments);
        }
    });

 //
    ListRenderer.include({
        // init: function () {
        //     this.$(window).scroll(function(){
        //     var leftWidth=$(window).scrollLeft();
        //     this.$('.o_list_view_categ').scrollLeft(leftWidth);
        //     });
        // },

        _renderView: function () {
            renderer=this;
            var result = this._super.apply(this, arguments);
            if (this.arch.attrs.categ_property && this.arch.attrs.categ_model) {
                this.getParent().$('.table-responsive').addClass("o_list_view_width_withcateg");
                this.getParent().$('.table-responsive').css("width",'auto');
                this.getParent().$('.table-responsive').css("overflow-x", "auto");
                buildTree();
            } else {
                this.getParent().$('.o_list_view_categ').remove();
            }
            return result;
        }
    });

    KanbanRenderer.include({

        _renderView: function () {
            renderer=this;
            var result = this._super.apply(this, arguments);
            if (this.arch.attrs.categ_property && this.arch.attrs.categ_model) {
                buildTree();
            } else {
                this.getParent().$('.o_list_view_categ').remove();
            }
            return result;
        }
    });

});
