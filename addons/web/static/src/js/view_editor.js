openerp.web.view_editor = function(openerp) {
var QWeb = openerp.web.qweb;
openerp.web.ViewEditor =   openerp.web.Widget.extend({
    init: function(parent, element_id, dataset, view, options) {
        this._super(parent);
        this.element_id = element_id
        this.parent = parent
        this.dataset = dataset;
        this.model = dataset.model;
        this.xml_id = 0;
    },
    start: function() {
        this.View_editor();
    },
    View_editor : function() {
        var self = this;
        var action = {
            name:'ViewEditor',
            context:this.session.user_context,
            domain: [["model", "=", this.dataset.model]],
            res_model : 'ir.ui.view',
            views : [[false, 'list']],
            type: 'ir.actions.act_window',
            target: "current",
            limit : 80,
            auto_search : true,
            flags: {
                sidebar: false,
                views_switcher: false,
                action_buttons:false,
                search_view:false,
                pager:false,
                radio:true
            },
        };
        this.view_edit_dialog = new openerp.web.Dialog(this,{
            modal: true,
            title: 'ViewEditor',
            width: 750,
            height: 500,
            buttons: {
            "Create": function(){
                //to do
            },
            "Edit": function(){
                self.xml_id=0;
                self.get_data();
            },
            "Close": function(){
                $(this).dialog('destroy');
            }
        },
        });
        this.view_edit_dialog.start().open();
        var action_manager = new openerp.web.ActionManager(this);
        action_manager.appendTo(this.view_edit_dialog);
        action_manager.do_action(action);
    },
    check_attr: function(xml, tag, level) {
        var obj = {'child_id':[],'id':this.xml_id++,'level':level+1,'att_list':[],'name':""};
        var render_name = "<" + tag;
        obj.att_list.push(tag);
        $(xml).each(function() {
            _.each(this.attributes, function(attrs){
            if (tag != 'button') {
                if (attrs.nodeName == "string" || attrs.nodeName == "name" || attrs.nodeName == "index") {
                render_name += ' ' + attrs.nodeName + '=' + '"' + attrs.nodeValue + '"' ;}
            } else {
                if (attrs.nodeName == "name") {
                render_name += ' ' + attrs.nodeName + '=' + '"' + attrs.nodeValue + '"';}
            }
            obj.att_list.push( [attrs.nodeName,attrs.nodeValue] );
            });
        render_name+= ">";
        });
        obj.name = render_name;
        return obj;
    },
    save_object: function(val, parent_list, child_obj_list) {
        var self = this;
        var check_id = parent_list[0];
        var p_list = parent_list.slice(1);
        if (val.child_id.length != 0) {
            _.each(val.child_id, function(val, key) {
                if (val.id == check_id) {
                    if (p_list.length!=0) {
                        self.save_object(val, p_list, child_obj_list);
                    } else {
                        val.child_id = child_obj_list;
                        return false;
                    }
                }
            });
        } else {
            val.child_id = child_obj_list;
        }
    },
    xml_node_create: function(xml, root, parent_list, parent_id, main_object){
        var self = this;
        var child_obj_list = [];
        var children_list = $(xml).filter(root).children();
        var parents = $(children_list[0]).parents().get();
        _.each(children_list, function (child_node) {
            child_obj_list.push(self.check_attr(child_node,child_node.tagName.toLowerCase(),parents.length));
        });
        if (children_list.length != 0) {
            if (parents.length <= parent_list.length) {
                parent_list.splice(parents.length - 1);
            }
            parent_list.push(parent_id);
            self.save_object(main_object[0], parent_list.slice(1), child_obj_list);
        }
        for (var i=0; i<children_list.length; i++) {
            self.xml_node_create
            (children_list[i], children_list[i].tagName.toLowerCase(),
                parent_list, child_obj_list[i].id, main_object);
        }
        return main_object;
    },
    parse_xml: function(arch, view_id) {
        var root = $(arch).filter(":first")[0];
        var tag = root.tagName.toLowerCase();
        var obj ={'child_id':[],'id':this.xml_id++,'level':0,'att_list':[],'name':"<view view_id='"+view_id+"'>"};
        var root_object = this.check_attr(root,tag,0);
        obj.child_id = this.xml_node_create(arch, tag, [], this.xml_id-1, [root_object], [])
        return [obj];
    },
    get_data: function() {
        var self = this;

        var view_arch_list = [];
        var view_id =((this.view_edit_dialog.$element.find("input[name='radiogroup']:checked").parent()).parent()).attr('data-id');
        var ve_dataset = new openerp.web.DataSet(this, 'ir.ui.view');
        ve_dataset.read_ids([parseInt(view_id)], ['arch'], function (arch) {
            one_object = self.parse_xml(arch[0].arch,view_id);
            view_arch_list.push({"view_id" : view_id, "arch" : arch[0].arch});
            dataset = new openerp.web.DataSetSearch(self, 'ir.ui.view', null, null);
            dataset.read_slice([], {domain : [['inherit_id','=', parseInt(view_id)]]}, function (result) {
                _.each(result, function(res) {
                    view_arch_list.push({"view_id":res.id,"arch":res.arch});
                    self.inherit_view(one_object, res);
                });
                return self.edit_view({"main_object": one_object,
                         "parent_child_id": self.parent_child_list(one_object, []),
                         "arch": view_arch_list});
            });
        });
    },
    parent_child_list : function(one_object, p_list) {
        var self = this;
        _.each(one_object , function(element){
            if(element.child_id.length != 0){
                p_list.push({"key":element.id,"value":_.pluck(element.child_id, 'id')});
                self.parent_child_list(element.child_id, p_list);
            }
        });
        return p_list;
    },
    inherit_view : function(one_object, result) {
        var self = this;
        var root = $(result.arch).filter('*');
        var xml_list = [];
        if (root[0].tagName.toLowerCase() == "data") {
            xml_list = $(root[0]).children();
        } else {
            xml_list.push(root[0]);
        }
        _.each(xml_list , function(xml){
            var parent_id;
            var check_list = [];
            var xpath_object = self.parse_xml(xml,result.id);
            if (xml.tagName.toLowerCase() == "xpath" ) {
                var part_expr = _.without($(xml).attr('expr').split("/"),"");
                _.each(part_expr,function(part){
                    check_list.push(_.without($.trim(part.replace(/[^a-zA-Z 0-9 _]+/g,'!')).split("!"),""));
                });
            } else {
                    var temp = [];
                    _.each(xpath_object[0].child_id[0].att_list, function(list){
                        if(!_.include(list, "position")){
                           temp.push(list);
                        }
                    });
                    check_list = [_.flatten(temp)];
            }
            self.full_path_search(check_list ,one_object ,xpath_object);
        });
    },
    full_path_search: function(check_list ,val ,xpath_object) {
        var self = this;
        if(xpath_object.length!=0){
            var check = check_list[0];
            var obj;
            switch (check.length) {
                case 2:
                    if(parseInt(check[1])){
                        var list_1 = _.select(val,function(element){
                            var main_list = _.flatten(element.att_list);
                            return _.include(main_list, check[0]);
                        });
                        obj = val[_.indexOf(val,list_1[parseInt(check[1])-1])];
                    } else {
                        obj = _.detect(val, function(element){
                            var main_list = _.flatten(element.att_list);
                            return _.include(main_list, check[0]);
                        });
                    }
                    break;
                case 3:
                    obj = _.detect(val,function(element){
                        var main_list = _.flatten(element.att_list);
                        check = _.uniq(check);
                        var insert = _.intersection(main_list,check);
                        if(insert.length == check.length ){return element;}
                    });
                    break;
                case 1:
                    var list_1 = _.select(val,function(element){
                        var main_list = _.flatten(element.att_list);
                        return _.include(main_list, check[0]);
                    });
                    if(list_1.length != 0){
                        (check_list.length == 1)? obj = list_1[0] : check_list.shift();
                    }
                    break;
            }
            if(obj) {
                check_list.shift();
                if (check_list.length !=0){
                    self.full_path_search(check_list ,obj.child_id ,xpath_object);
                } else {
                    var level = obj.level+1;
                    self.increase_level(xpath_object[0], level)
                    obj.child_id.push(xpath_object[0]);
                    xpath_object.pop();
                    return;
                }
            }
            else {
                _.each(val,function(element){
                    self.full_path_search(check_list ,element.child_id ,xpath_object);
                });
            }
        }
    },
    increase_level: function(val, level) {
        var self = this;
        val.level = level;
        _.each(val.child_id, function(val, key) {
            self.increase_level(val, level + 1);
        });
    },
    edit_view: function(one_object) {
        var self = this;
        this.edit_xml_dialog = new openerp.web.Dialog(this,{
            modal: true,
            title: 'Edit Xml',
            width: 750,
            height: 500,
            buttons: {
                "Inherited View": function(){
                    //todo
                },
                "Preview": function(){
                    //todo
                },
                "Close": function(){
                    $(this).dialog('destroy');
                }
            }
        });
        this.edit_xml_dialog.start().open();
        this.edit_xml_dialog.$element.html(QWeb.render('view_editor', {
            'data': one_object['main_object'],
        }));
        this.edit_xml_dialog.$element.find("tr[id^='viewedit-']").click(function() {
            self.edit_xml_dialog.$element.find("tr[id^='viewedit-']").removeClass('ui-selected');
            $(this).addClass('ui-selected');
        });
        this.edit_xml_dialog.$element.find("img[id^='parentimg-']").click(function() {
            if ($(this).attr('src') == '/web/static/src/img/collapse.gif') {
                $(this).attr('src', '/web/static/src/img/expand.gif');
                self.on_expand(this);
            } else {
                $(this).attr('src', '/web/static/src/img/collapse.gif');
                var id = this.id.split('-')[1];
                self.on_collapse(this,one_object['parent_child_id'], one_object['main_object']);
            }
        });
        this.edit_xml_dialog.$element.find("img[id^='side-']").click(function() {
            var side = $(this).closest("tr[id^='viewedit-']")
            var id_tr = (side.attr('id')).split('-')[1];
            var img = side.find("img[id='parentimg-"+id_tr+"']").attr('src'); ;
            var level = parseInt(side.attr('level'));
            var list_shift =[];
            var last_tr;
            var cur_tr = side;
            list_shift.push(side);
            var next_tr;
            var ls = side;
            var view_id;
            var view_xml_id;
            while(1){
                ls = ls.prev();
               if((self.edit_xml_dialog.$element.find(ls).find('a').text()).search("view_id") != -1
                     && parseInt(ls.attr('level')) < level){
                    view_id = parseInt(($(ls).find('a').text()).replace(/[^0-9]+/g,''));
                    view_xml_id = (ls.attr('id')).split('-')[1];
                    break;
                }
            }
            switch (this.id) {
                case "side-add":
                    break;
                case "side-remove":
                    break;
                case "side-edit":
                    break;
                case "side-up":
                    while (1) {
                        var prev_tr = cur_tr.prev();
                        if(level >= parseInt(prev_tr.attr('level')) || prev_tr.length == 0) {
                           last_tr = prev_tr;
                           break;
                        }
                        cur_tr = prev_tr;
                    }
                    if (img) {
                        while (1) {
                            next_tr = side.next();
                            if ( parseInt(next_tr.attr('level')) <= level || next_tr.length == 0) {
                                break;
                            } else {
                                list_shift.push(next_tr);
                                side = next_tr;
                            }
                        }
                    }
                    if (last_tr.length != 0 
                            && parseInt(last_tr.attr('level')) == level
                                && 
                    (self.edit_xml_dialog.$element.find(last_tr).find('a').text()).search("view_id") == -1) {
                        _.each(list_shift, function(rec) {
                             $(last_tr).before(rec);
                        });
                        self.save_move_arch(one_object, view_id, view_xml_id, id_tr, level, "up");
                    }
                break;
            case "side-down":
                if (img) {
                    while (1) {
                        next_tr = cur_tr.next();
                        if ( parseInt(next_tr.attr('level')) <= level || next_tr.length == 0) {
                            last_tr = next_tr;
                            break;
                        } else {
                            list_shift.push(next_tr);
                            cur_tr = next_tr;
                        }
                   }
                }
                else {
                    last_tr = cur_tr.next();
                }
                if((self.edit_xml_dialog.$element.find(last_tr).find('a').text()).search("view_id") != -1){
                    return;
                }
                if (last_tr.length != 0 &&  parseInt(last_tr.attr('level')) == level) {
                    var last_tr_id = (last_tr.attr('id')).split('-')[1];
                    img = last_tr.find("img[id='parentimg-" + last_tr_id + "']").attr('src');
                    if (img) {
                        self.edit_xml_dialog.$element.find("img[id='parentimg-" + last_tr_id + "']").
                                                        attr('src', '/web/static/src/img/expand.gif');
                        while (1) {
                            var next_tr = last_tr.next();
                            if (next_tr.attr('level') <= level || next_tr.length == 0) break;
                            next_tr.hide();
                            last_tr = next_tr;
                        }
                    }
                    
                    list_shift.reverse();
                    _.each(list_shift, function(rec) {
                       $(last_tr).after(rec);
                    });
                    self.save_move_arch(one_object, view_id, view_xml_id, id_tr, level, "down");

                }
                break;
            }
        });
    },
    save_move_arch: function(one_object, view_id, view_xml_id, id_tr, level, move_direct){
        var self = this;
        var arch = _.detect(one_object['arch'],function(element){
            return element.view_id == view_id;
        });
        var obj = self.get_view_object(view_xml_id, one_object['main_object'], []);
        if(($(arch.arch).filter("data")).length != 0 && view_xml_id != 0){
            var check_list = _.flatten(obj[0].child_id[0].att_list);
            arch.arch = _.detect($(arch.arch).children(), function(xml_child){
                var temp_obj = self.check_attr(xml_child, xml_child.tagName.toLowerCase());
                var main_list = _.flatten(temp_obj.att_list);
                check_list = _.uniq(check_list);
                var insert = _.intersection(main_list,check_list);
                if(insert.length == check_list.length ){return xml_child;}
            });
        }
        return self.get_node(arch.arch, obj[0].child_id[0], parseInt(id_tr), [], parseInt(level),
                        parseInt(view_id), arch, move_direct);
    },

    get_view_object: function(view_xml_id, one_object,result){
        var self = this;
        if(result.length==0){
            var check = _.detect(one_object , function(obj){
                return view_xml_id==obj.id;
            });
            if(check){result.push(check);};
            _.each(one_object, function(obj){
               self.get_view_object(view_xml_id, obj.child_id, result);
            });
        }
        return result;
    },

    get_node: function(arch1, obj, id, child_list, level, view_id, arch, move_direct){
        var self = this;
        var children_list =  $(arch1).children();
        var list_obj_xml = _.zip(children_list,obj.child_id);
        if(id){
            if(obj.id == id){
                var id;
                var parent = $(arch1).parents();
                var index = _.indexOf(child_list,obj)
                var re_insert_obj = child_list.splice(index,1);
                if(move_direct == "down"){
                    var next = $(arch1).next();
                    $(next).after(arch1);
                    child_list.splice(index+1, 0, re_insert_obj[0]);
                }else{
                    var prev = $(arch1).prev();
                    $(prev).before(arch1);
                    child_list.splice(index-1, 0, re_insert_obj[0]);
                }
                parent = parent[parent.length-1];
                var convert_to_utf = self.xml2Str(parent);
                if(convert_to_utf){
                    convert_to_utf = convert_to_utf.replace('xmlns="http://www.w3.org/1999/xhtml"', "");
                    convert_to_utf = '<?xml version="1.0" encoding="utf-8"?>' + convert_to_utf;
                    arch.arch = convert_to_utf;
                    dataset = new openerp.web.DataSet(this, 'ir.ui.view');
                        dataset.write(parseInt(view_id),{"arch":convert_to_utf},function(r){
                    });
                }
            }
            if(obj.level <= level){
                _.each(list_obj_xml, function(child_node){
                    self.get_node(child_node[0], child_node[1], id, obj.child_id, level, view_id, arch, move_direct);
                });
            }
        }
    },
    xml2Str: function(xmlNode) {
       try {
          return (new XMLSerializer()).serializeToString(xmlNode);
      }
      catch (e) {
         try {
            return xmlNode.xml;
         }
         catch (e) {
            return false;
         }
       }
      
    },

    on_expand: function(expand_img){
        var level = parseInt($(expand_img).closest("tr[id^='viewedit-']").attr('level'));
        var cur_tr = $(expand_img).closest("tr[id^='viewedit-']");
        while (1) {
            var nxt_tr = cur_tr.next();
            if (parseInt(nxt_tr.attr('level')) > level){
                cur_tr = nxt_tr;
                nxt_tr.hide();
            } else return nxt_tr;
        }
    },
    on_collapse: function(collapse_img, parent_child_id, id, main_object) {
        var self = this;
        var id = collapse_img.id.split('-')[1];
        var datas = _.detect(parent_child_id,function(res) {
            return res.key == id;
        });
        _.each(datas.value, function(rec) {
            var tr = self.edit_xml_dialog.$element.find("tr[id='viewedit-"+rec+"']");
            tr.find("img[id='parentimg-"+rec+"']").attr('src','/web/static/src/img/expand.gif');
            tr.show();
        });
    }

});
};
