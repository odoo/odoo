openerp.web.view_editor = function(openerp) {
var _PROPERTIES = {
    'field' : ['name', 'string', 'required', 'readonly', 'domain', 'context', 'nolabel', 'completion',
               'colspan', 'widget', 'eval', 'ref', 'on_change', 'groups', 'attrs'],
    'form' : ['string', 'col', 'link'],
    'notebook' : ['colspan', 'position', 'groups'],
    'page' : ['string', 'states', 'attrs', 'groups'],
    'group' : ['string', 'col', 'colspan', 'states', 'attrs', 'groups'],
    'image' : ['filename', 'width', 'height', 'groups'],
    'separator' : ['string', 'colspan', 'groups'],
    'label': ['string', 'align', 'colspan', 'groups'],
    'button': ['name', 'string', 'icon', 'type', 'states', 'readonly', 'special', 'target', 'confirm', 'context', 'attrs', 'groups','colspan'],
    'newline' : [],
    'hpaned': ['position', 'groups'],
    'vpaned': ['position', 'groups'],
    'child1' : ['groups'],
    'child2' : ['groups'],
    'action' : ['name', 'string', 'colspan', 'groups'],
    'tree' : ['string', 'colors', 'editable', 'link', 'limit', 'min_rows'],
    'graph' : ['string', 'type'],
    'calendar' : ['string', 'date_start', 'date_stop', 'date_delay', 'day_length', 'color', 'mode'],
    'view' : [],
};
var icons = ['','STOCK_ABOUT', 'STOCK_ADD', 'STOCK_APPLY', 'STOCK_BOLD',
'STOCK_CANCEL', 'STOCK_CDROM', 'STOCK_CLEAR', 'STOCK_CLOSE', 'STOCK_COLOR_PICKER',
'STOCK_CONNECT', 'STOCK_CONVERT', 'STOCK_COPY', 'STOCK_CUT', 'STOCK_DELETE',
'STOCK_DIALOG_AUTHENTICATION', 'STOCK_DIALOG_ERROR', 'STOCK_DIALOG_INFO',
'STOCK_DIALOG_QUESTION', 'STOCK_DIALOG_WARNING', 'STOCK_DIRECTORY', 'STOCK_DISCONNECT',
'STOCK_DND', 'STOCK_DND_MULTIPLE', 'STOCK_EDIT', 'STOCK_EXECUTE', 'STOCK_FILE',
'STOCK_FIND', 'STOCK_FIND_AND_REPLACE', 'STOCK_FLOPPY', 'STOCK_GOTO_BOTTOM',
'STOCK_GOTO_FIRST', 'STOCK_GOTO_LAST', 'STOCK_GOTO_TOP', 'STOCK_GO_BACK',
'STOCK_GO_DOWN', 'STOCK_GO_FORWARD', 'STOCK_GO_UP', 'STOCK_HARDDISK',
'STOCK_HELP', 'STOCK_HOME', 'STOCK_INDENT', 'STOCK_INDEX', 'STOCK_ITALIC',
'STOCK_JUMP_TO', 'STOCK_JUSTIFY_CENTER', 'STOCK_JUSTIFY_FILL',
'STOCK_JUSTIFY_LEFT', 'STOCK_JUSTIFY_RIGHT', 'STOCK_MEDIA_FORWARD',
'STOCK_MEDIA_NEXT', 'STOCK_MEDIA_PAUSE', 'STOCK_MEDIA_PLAY',
'STOCK_MEDIA_PREVIOUS', 'STOCK_MEDIA_RECORD', 'STOCK_MEDIA_REWIND',
'STOCK_MEDIA_STOP', 'STOCK_MISSING_IMAGE', 'STOCK_NETWORK', 'STOCK_NEW',
'STOCK_NO', 'STOCK_OK', 'STOCK_OPEN', 'STOCK_PASTE', 'STOCK_PREFERENCES',
'STOCK_PRINT', 'STOCK_PRINT_PREVIEW', 'STOCK_PROPERTIES', 'STOCK_QUIT',
'STOCK_REDO', 'STOCK_REFRESH', 'STOCK_REMOVE', 'STOCK_REVERT_TO_SAVED',
'STOCK_SAVE', 'STOCK_SAVE_AS', 'STOCK_SELECT_COLOR', 'STOCK_SELECT_FONT',
'STOCK_SORT_ASCENDING', 'STOCK_SORT_DESCENDING', 'STOCK_SPELL_CHECK',
'STOCK_STOP', 'STOCK_STRIKETHROUGH', 'STOCK_UNDELETE', 'STOCK_UNDERLINE',
'STOCK_UNDO', 'STOCK_UNINDENT', 'STOCK_YES', 'STOCK_ZOOM_100',
'STOCK_ZOOM_FIT', 'STOCK_ZOOM_IN', 'STOCK_ZOOM_OUT',
'terp-account', 'terp-crm', 'terp-mrp', 'terp-product', 'terp-purchase',
'terp-sale', 'terp-tools', 'terp-administration', 'terp-hr', 'terp-partner',
'terp-project', 'terp-report', 'terp-stock', 'terp-calendar', 'terp-graph',
];
var QWeb = openerp.web.qweb;
openerp.web.ViewEditor =   openerp.web.Widget.extend({
    init: function(parent, element_id, dataset, view, options) {
        this._super(parent);
        this.element_id = element_id
        this.parent = parent
        this.dataset = dataset;
        this.model = this.dataset.model;
        this.xml_id = 0;
        this.property = openerp.web.ViewEditor.property_widget;
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
        this.view_edit_dialog = new openerp.web.Dialog(this, {
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
                    self.view_edit_dialog.close();
                }
            },
        });
        this.view_edit_dialog.start().open();
        var action_manager = new openerp.web.ActionManager(this);
        action_manager.appendTo(this.view_edit_dialog);
        action_manager.do_action(action);
    },
    check_attr: function(xml, tag, level) {
        var obj = {'child_id': [], 'id': this.xml_id++, 'level': level+1, 'att_list': [], 'name': ""};
        var render_name = "<" + tag;
        obj.att_list.push(tag);
        $(xml).each(function() {
            _.each(this.attributes, function(attrs){
                if ((tag != 'button') && (tag != 'field')){
                    if (attrs.nodeName == "string" || attrs.nodeName == "name" || attrs.nodeName == "index") {
                        render_name += ' ' + attrs.nodeName + '=' + '"' + attrs.nodeValue + '"' ;
                    }
                } else {
                    if (attrs.nodeName == "name") {
                        render_name += ' ' + attrs.nodeName + '=' + '"' + attrs.nodeValue + '"';
                    }
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
        for (var i = 0; i < children_list.length; i++) {
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
        obj.child_id = this.xml_node_create(arch, tag, [], this.xml_id-1, [root_object], []);
        return [obj];
    },
    get_data: function() {
        var self = this;
        var view_arch_list = [];
        self.main_view_id =((this.view_edit_dialog.$element.find("input[name='radiogroup']:checked").parent()).parent()).attr('data-id');
        var ve_dataset = new openerp.web.DataSet(this, 'ir.ui.view');
        ve_dataset.read_ids([parseInt(self.main_view_id)], ['arch', 'type'], function (arch) {
            one_object = self.parse_xml(arch[0].arch,self.main_view_id);
            self.main_view_type = arch[0].type
            view_arch_list.push({"view_id" : self.main_view_id, "arch" : arch[0].arch});
            dataset = new openerp.web.DataSetSearch(self, 'ir.ui.view', null, null);
            dataset.read_slice([], {domain : [['inherit_id','=', parseInt(self.main_view_id)]]}, function (result) {
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
            title: 'View Editor',
            width: 750,
            height: 500,
            buttons: {
                "Inherited View": function(){
                    //todo
                },
                "Preview": function(){
                    var action = {
                        context:self.session.user_context,
                        res_model : self.model,
                        views : [[self.main_view_id, self.main_view_type]],
                        type: 'ir.actions.act_window',
                        target: "new",
                        flags: {
                            sidebar: false,
                            views_switcher: false,
                            action_buttons:false,
                            search_view:false,
                            pager:false,
                        },
                    };
                    var action_manager = new openerp.web.ActionManager(self);
                    action_manager.do_action(action);
                },
                "Close": function(){
                    self.edit_xml_dialog.close();
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
                    var tag, fld_name;
                    var tr = $(this).closest("tr[id^='viewedit-']").find('a').text();
                    var tag_fld = tr.split(" ");
                    if (tag_fld.length > 3){
                        tag = tag_fld[1].replace(/[^a-zA-Z 0-9]+/g,'');
                        fld_name = tag_fld[2].split("=")[1].replace(/[^a-zA-Z _ 0-9]+/g,'');
                    }else{
                        tag = tag_fld[1].replace(/[^a-zA-Z 0-9]+/g,'');
                        fld_name= tag;
                    }
                    var properties = _PROPERTIES[tag];
                    self.on_edit_node(properties,fld_name,id_tr,one_object,view_id, view_xml_id, level);
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
                    if (last_tr.length != 0  && parseInt(last_tr.attr('level')) == level &&
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
    save_move_arch: function(one_object, view_id, view_xml_id, id_tr, level, move_direct, update_values){
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
            parseInt(view_id), arch, move_direct, update_values);
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
    get_node: function(arch1, obj, id, child_list, level, view_id, arch, move_direct, update_values){
        var self = this;
        var children_list =  $(arch1).children();
        var list_obj_xml = _.zip(children_list,obj.child_id);
        if (id) {
            if (obj.id == id) {
                var index = _.indexOf(child_list, obj)
                if (move_direct == "down") {
                    var next = $(arch1).next();
                    $(next).after(arch1);
                    var re_insert_obj = child_list.splice(index, 1);
                    child_list.splice(index+1, 0, re_insert_obj[0]);
                }else if(move_direct == "up"){
                    var prev = $(arch1).prev();
                    $(prev).before(arch1);
                    var re_insert_obj = child_list.splice(index, 1);
                    child_list.splice(index-1, 0, re_insert_obj[0]);
                }else if(move_direct == "update_node"){
                    _.each(update_values, function(val){
                        if(val[1]){
                        $(arch1).attr(val[0],val[1]);
                        }
                    });
                    var new_obj = self.check_attr(arch1,arch1.tagName.toLowerCase(),obj.level);
                    new_obj.id = obj.id;
                    self.edit_xml_dialog.$element.find("tr[id='viewedit-"+id+"']").find('a').text(new_obj.name);
                    child_list.splice(index, 1, new_obj);
                }
                var parent = $(arch1).parents();
                parent = parent[parent.length-1];
                var convert_to_utf = self.xml2Str(parent);
                if (convert_to_utf) {
                    convert_to_utf = convert_to_utf.replace('xmlns="http://www.w3.org/1999/xhtml"', "");
                    convert_to_utf = '<?xml version="1.0"?>' + convert_to_utf;
                    arch.arch = convert_to_utf;
                    dataset = new openerp.web.DataSet(this, 'ir.ui.view');
                        dataset.write(parseInt(view_id),{"arch":convert_to_utf}, function(r) {
                    });
                }
            }
            if (obj.level <= level) {
                _.each(list_obj_xml, function(child_node) {
                    self.get_node(child_node[0], child_node[1], id, obj.child_id, level, view_id, arch, move_direct, update_values);
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
    },
    on_edit_node:function(properties,fld_name,id_tr,obj,view_id, view_xml_id, level){
        var self = this;
        this.edit_node_dialog = new openerp.web.Dialog(this,{
            modal: true,
            title: 'Properties',
            width: 650,
            height: 200,
            buttons: {
                    "Update": function(){
                        var update_values = [];
                        _.each(self.edit_widget,function(widget){
                            update_values.push(widget.get_value());
                        });
                        self.save_move_arch(obj, view_id, view_xml_id, id_tr, level, "update_node", update_values);
                    },
                    "Cancel": function(){
                        $(this).dialog('destroy');
                    }
                }
        });
        this.edit_node_dialog.start().open();
        var widget = ['readonly','required','nolabel','completion','widget','groups','position','icon','align','special','type','target'];
        var arch_val = self.get_view_object(id_tr,one_object,[]);
        self.edit_node_dialog.$element.append('<table id="rec_table" class="oe_forms"></table>');
        self.edit_widget = [];
        _.each(properties,function(record){
            var id = record;
            self.ready  = $.when(self.on_groups(id)).then(function () {
                    if (_.include(widget,id)){
                        var type_widget =  new (self.property.get_any(['undefined' , id, arch_val[0]['att_list'][0]])) (self.edit_node_dialog, arch_val, id);
                        self.edit_widget.push(type_widget);
                        self.edit_node_dialog.$element.find('table[id=rec_table]').append('<tr id="'+id+'"><td align="right">'+id+':</td><td>'+type_widget.render()+'</td></tr>');
                        (id=='groups')?type_widget.set_value(self.groups):type_widget.set_value();
                    }else{
                        var type_widget = new openerp.web.ViewEditor.FieldChar (self.edit_node_dialog,arch_val, id);
                        self.edit_widget.push(type_widget);
                        self.edit_node_dialog.$element.find('table[id=rec_table]').append('<tr id="'+id+'"><td align="right">'+id+':</td><td>'+type_widget.render()+'</td></tr>');
                        type_widget.set_value();
                    }
                });
            });
    },
     //for getting groups
    on_groups: function(id){
        var self = this,
        def = $.Deferred();
        if (id !='groups') {
            self.groups = false;
            return false;
        }
        var group_ids = [],
        group_names = {},
        groups = [];
        var res_groups = new openerp.web.DataSetSearch(this,'res.groups', null, null),
            model_data = new openerp.web.DataSetSearch(self,'ir.model.data', null, null);
            res_groups
            .read_slice([],{})
            .done(function(res_grp) {
                _.each(res_grp,function(res){
                    var key = res.id;
                    group_names[key]=res.name;
                    group_ids.push(res.id);
                });
            model_data
                .read_slice([],{domain:[['res_id', 'in', group_ids],['model','=','res.groups']]})
                .done(function(model_grp) {
                    _.each(model_grp,function(res_group){
                        groups.push([res_group.name,group_names[res_group.res_id]]);
                    });
                    self.groups = groups;
                    def.resolve();
                });
            })
        return def.promise();
    }
});
openerp.web.ViewEditor.Field = openerp.web.Class.extend({
    init: function(view, node, id) {
        var self = this;
        this.$element = view.$element;
        this.node = node;
        this.dirty = false;
        this.name = id;
    },
    render: function () {
        return QWeb.render(this.template, {widget: this});
    }
});
openerp.web.ViewEditor.FieldBoolean = openerp.web.ViewEditor.Field.extend({
    init: function(view, node, id) {
        this._super(view, node, id);
        this.template = "view_boolean";
    },
    set_value: function() {
        var self = this;
        var view_val = _.detect(this.node[0]['att_list'],function(res) {
            return _.include(res,self.name);
        });
        if(view_val){
            this.$element.find("tr[id="+ self.name+"] input").attr('checked', view_val[1]);
        }
    },
    get_value: function(){
        var val = this.$element.find("tr[id="+this.name+"] input").is(':checked');
        if (val){
            return [this.name,val];
        }else{
            return [this.name,null];
        }
    }
});
openerp.web.ViewEditor.FieldChar = openerp.web.ViewEditor.Field.extend({
    init: function(view, node, id) {
        this._super(view, node, id);
        this.template = "view_char";
    },
    set_value: function() {
        var self = this;
        var view_val = _.detect(this.node[0]['att_list'],function(res) {
            return _.include(res, self.name);
        });
        view_val ? this.$element.find("tr[id="+self.name +"] input").val(view_val[1]): this.$element.find("tr[id="+self.name+"] input").val();
    },
    get_value: function(){
        var self = this;
        var val= this.$element.find("tr[id="+this.name+"] input").val();
        if (val){
            return [this.name,val];
        }else{
            return [this.name,""];
        }
    }
});
openerp.web.ViewEditor.FieldSelect = openerp.web.ViewEditor.Field.extend({
    init: function(view, node, id) {
        this._super(view, node, id);
        this.template = "view_selection";
    },
    set_value: function(value) {
        var self = this;
        var view_val = _.detect(this.node[0]['att_list'],function(res) {
            return _.include(res,self.name);
        });
        _.each(value, function(item) {
            var select_val = view_val?(view_val[1]==((typeof(item)=='string')?item:item[0])?true:false):false;
            self.$element.find("tr[id="+self.name+"] select").append($("<option/>", {
                    value:(typeof(item)=='string')?item:item[0],
                    text:(typeof(item)=='string')?item:item[1],
                    selected:select_val
            }));
        });
    },
    get_value: function(){
        var self = this;
        var val = this.$element.find("tr[id="+this.name+"] select").find("option:selected").val();
        if (val){
            return [this.name,val];
        }else{
            return [this.name,""];
        }
    }
});
openerp.web.ViewEditor.WidgetProperty = openerp.web.ViewEditor.FieldSelect.extend({
    init: function(view, node, id) {
        this._super(view, node, id);
        this.registry = openerp.web.form.widgets;
    },
    set_value: function() {
        var self= this;
        var value = _.keys(this.registry.map);
        value.push('');
        value.sort();
        this._super.apply(this,[value]);
    }
});
openerp.web.ViewEditor.IconProperty = openerp.web.ViewEditor.FieldSelect.extend({
    init: function(view, node, id) {
        this._super(view, node, id);
    },
    set_value: function() {
        var self = this;
        var value = icons;
        this._super.apply(this,[value]);
    }
});
openerp.web.ViewEditor.ButtonTargetProperty = openerp.web.ViewEditor.FieldSelect.extend({
    init: function(view, node, id) {
        this._super(view, node, id);
    },
    set_value: function() {
        var self = this;
        var value = [['',''],['new','New Window']];
        this._super.apply(this,[value]);
    }
});
openerp.web.ViewEditor.ButtonTypeProperty = openerp.web.ViewEditor.FieldSelect.extend({
    init: function(view, node, id) {
        this._super(view, node, id);
    },
    set_value: function() {
        var self = this;
        var value = [['',''],['action', 'Action'], ['object', 'Object'], ['workflow', 'Workflow'], ['server_action', 'Server Action']];
        this._super.apply(this,[value]);
    }
});
openerp.web.ViewEditor.AlignProperty = openerp.web.ViewEditor.FieldSelect.extend({
    init: function(view, node, id) {
        this._super(view, node, id);
    },
    set_value: function() {
        var self = this;
        var value = [['',''],['0.0','Left'], ['0.5','Center'], ['1.0','Right']];
        this._super.apply(this,[value]);
    }
});
openerp.web.ViewEditor.ButtonSpecialProperty = openerp.web.ViewEditor.FieldSelect.extend({
    init: function(view, node, id) {
        this._super(view, node, id);
    },
    set_value: function() {
        var self = this;
        var value = [['',''],['save','Save Button'], ['cancel','Cancel Button'], ['open','Open Button']];
        this._super.apply(this,[value]);
    }
});
openerp.web.ViewEditor.PositionProperty = openerp.web.ViewEditor.FieldSelect.extend({
    init: function(view, node, id) {
        this._super(view, node, id);
    },
    set_value: function() {
        var self = this;
        var value = [['',''],['after', 'After'],['before', 'Before'],['inside', 'Inside'],['replace', 'Replace']];
        this._super.apply(this,[value]);
    }
});
openerp.web.ViewEditor.GroupsProperty = openerp.web.ViewEditor.FieldSelect.extend({
    init: function(view, node, id) {
        this._super(view, node, id);
    },
    set_value: function(value) {
        var self = this;
        this.$element.find("tr[id="+ this.name +"] select").attr('multiple', true);
        this.$element.find("tr[id="+ this.name +"] select").css('height','100px');
        this._super.apply(this,[value]);
    }
});
openerp.web.ViewEditor.property_widget = new openerp.web.Registry({
    'required' : 'openerp.web.ViewEditor.FieldBoolean',
    'readonly' : 'openerp.web.ViewEditor.FieldBoolean',
    'nolabel' : 'openerp.web.ViewEditor.FieldBoolean',
    'completion' : 'openerp.web.ViewEditor.FieldBoolean',
    'widget' : 'openerp.web.ViewEditor.WidgetProperty',
    'groups' : 'openerp.web.ViewEditor.GroupsProperty',
    'position': 'openerp.web.ViewEditor.PositionProperty',
    'icon': 'openerp.web.ViewEditor.IconProperty',
    'align': 'openerp.web.ViewEditor.AlignProperty',
    'special': 'openerp.web.ViewEditor.ButtonSpecialProperty',
    'type': 'openerp.web.ViewEditor.ButtonTypeProperty',
    'target': 'openerp.web.ViewEditor.ButtonTargetProperty'
});
};
