openerp.web.view_editor = function(openerp) {
var _PROPERTIES = {
    'field' : ['name', 'string', 'required', 'readonly', 'domain', 'context', 'nolabel', 'completion',
               'colspan', 'widget', 'eval', 'ref', 'on_change', 'attrs'],
    'form' : ['string', 'col', 'link'],
    'notebook' : ['colspan', 'position', 'groups'],
    'page' : ['string', 'states', 'attrs', 'groups'],
    'group' : ['string', 'col', 'colspan', 'states', 'attrs', 'groups'],
    'image' : ['filename', 'width', 'height', 'groups'],
    'separator' : ['string', 'colspan', 'groups'],
    'label': ['string', 'align', 'colspan', 'groups'],
    'button': ['name', 'string', 'icon', 'type', 'states', 'readonly', 'special', 'target', 'confirm', 'context', 'attrs', 'groups'],
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
        var action_manager = new openerp.web.ActionManager(this);
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
                self.xml_id = 0 ;
                self.get_data();
            },
            "Close": function(){
                $(this).dialog('destroy');
            }
        },
        });
        this.view_edit_dialog.start();
        this.view_edit_dialog.open();
        action_manager.appendTo(this.view_edit_dialog);
        action_manager.do_action(action);
    },
    check_attr: function(xml, tag, level) {
        var obj = new Object();
        obj.child_id = [];
        obj.id = this.xml_id++;
        obj.level = level+1;
        var render_name = "<" + tag;
        obj.att_list = [];
        obj.att_list.push(tag);
        $(xml).each(function() {
            _.each(this.attributes, function(attrs){
                if (tag != 'button') {
                    if (attrs.nodeName == "string" || attrs.nodeName == "name" || attrs.nodeName == "index") {
                        render_name += ' ' + attrs.nodeName + '=' + '"' + attrs.nodeValue + '"' ;
                    }
                } else if (attrs.nodeName == "name") {
                    render_name += ' ' + attrs.nodeName + '=' + '"' + attrs.nodeValue + '"';
                }
                if (attrs.nodeName != "position") {
                    obj.att_list.push( [attrs.nodeName,attrs.nodeValue] );
                }
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
                if (val.id==check_id) {
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
        var view_id =((this.view_edit_dialog.$element.find("input[name='radiogroup']:checked").parent()).parent()).attr('data-id');
        var ve_dataset = new openerp.web.DataSet(this, 'ir.ui.view');
        ve_dataset.read_ids([parseInt(view_id)], ['arch'], function (arch) {
            one_object = self.parse_xml(arch[0].arch,view_id);
            one_object.arch = arch[0].arch;
            dataset = new openerp.web.DataSetSearch(self, 'ir.ui.view', null, null);
            dataset.read_slice([], {domain : [['inherit_id','=', parseInt(view_id)]]}, function (result) {
                _.each(result, function(res) {
                    self.inherit_view(one_object, res);
                });
                return self.edit_view({"main_object": one_object,
                         "parent_child_id": self.parent_child_list(one_object, [])});
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
                    check_list = [_.flatten(xpath_object[0].child_id[0].att_list)];
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
                    if(list_1 != 0){
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
            $("tr[id^='viewedit-']").removeClass('ui-selected');
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
            var level = side.attr('level');
            var list_shift =[];
            var last_tr;
            var cur_tr = side;
            list_shift.push(side);
            var next_tr;
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
                    self.on_edit_node(properties,fld_name,id_tr);
                    break;
                case "side-up":
                    while (1) {
                        var prev_tr = cur_tr.prev();
                        if(level >= prev_tr.attr('level') || prev_tr.length == 0) {
                           last_tr = prev_tr;
                           break;
                        }
                        cur_tr = prev_tr;
                    }
                    if (img) {
                        while (1) {
                            next_tr = side.next();
                            if (next_tr.attr('level') <= level || next_tr.length == 0) {
                                break;
                            } else {
                                list_shift.push(next_tr);
                                side = next_tr;
                            }
                        }
                    }
                    if (last_tr.length != 0 && last_tr.attr('level') == level) {
                        _.each(list_shift, function(rec) {
                             $(last_tr).before(rec);
                        });
                    }
                break;
            case "side-down":
                if (img) {
                    while (1) {
                        next_tr = cur_tr.next();
                        if (next_tr.attr('level') <= level || next_tr.length == 0) {
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
                if (last_tr.length != 0 && last_tr.attr('level') == level) {
                    var last_tr_id = (last_tr.attr('id')).split('-')[1];
                    img = last_tr.find("img[id='parentimg-" + last_tr_id + "']").attr('src');
                    if (img) {
                        this.edit_xml_dialog.$element.find("img[id='parentimg-" + last_tr_id + "']").attr('src', '/web/static/src/img/expand.gif');
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
                }
                break;
            }
        });
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
    on_edit_node:function(properties,fld_name,id_tr){
        var self = this;
        var result;
        this.edit_node_dialog = new openerp.web.Dialog(this,{
            modal: true,
            title: 'Properties',
            width: 650,
            height: 200,
            buttons: {
                    "Update": function(){
                    },
                    "Cancel": function(){
                        $(this).dialog('destroy');
                    }
                }
        });
        this.edit_node_dialog.start().open();
        var widget = ['readonly','required','nolabel','completion','widget','groups','position','icon','align','special','type','target'];
        var arch_val = self.get_view_object(id_tr,one_object,[]);
        self.edit_node_dialog.$element.append('<table id="rec_table"></table>');
        dataset = new openerp.web.DataSetSearch(this,'ir.model', null, null);
        dataset.read_slice([],{domain : [['model','=',self.model]]},function (result) {
            db = new openerp.web.DataSetSearch(self,'ir.model.fields', null, null);
            db.read_slice([],{domain : [['model_id','=',result[0].id],['name','=',fld_name]]},function (res) {
                _.each(properties,function(record){
                    var id = record;
                    var rs = res.length ? res[0][record] : null;
                    if (_.include(widget,record)){
                        var type_widget =  new (self.property.get_any(['undefined' , record, arch_val[0]['att_list'][0]])) (self.edit_node_dialog, arch_val);
                        self.edit_node_dialog.$element.find('table[id=rec_table]').append('<tr id="'+record+'"><td align="right">'+record+':</td><td>'+type_widget.render()+'</td></tr>');
                        type_widget.set_value(id,rs);
                    }else{
                        var type_widget = new openerp.web.ViewEditor.FieldChar (self.edit_node_dialog,arch_val);
                        self.edit_node_dialog.$element.find('table[id=rec_table]').append('<tr id="'+record+'"><td align="right">'+record+':</td><td>'+type_widget.render()+'</td></tr>');
                        type_widget.set_value(id,rs);
                    }
                });
            });
        });
    }
});
openerp.web.ViewEditor.Field = openerp.web.Class.extend({
    init: function(view, node) {
        this.$element = view.$element;
        this.node = node;
    },
    render: function () {
        return QWeb.render(this.template, {widget: this});
    },
    start: function() {
        this._super();
        var self = this;
    }
});

openerp.web.ViewEditor.FieldBoolean = openerp.web.ViewEditor.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "view_boolean";
    },
    start: function() {
        var self = this;
        this._super.apply(this, arguments);
    },
    set_value: function(id,value) {
        var view_val = _.detect(this.node[0]['att_list'],function(res) {
            return _.include(res,id);
        });
        view_val ? this.$element.find("tr[id="+id+"] input").attr('checked', view_val[1]): this.$element.find("tr[id="+id+"] input").attr('checked', value);
    }
});
openerp.web.ViewEditor.FieldChar = openerp.web.ViewEditor.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.template = "view_char";
    },
    start: function() {
        var self = this;
        this._super.apply(this, arguments);
    },
    set_value: function(id,value) {
        var view_val = _.detect(this.node[0]['att_list'],function(res) {
            return _.include(res,id);
        });
        view_val ? this.$element.find("tr[id="+id+"] input").val(view_val[1]): this.$element.find("tr[id="+id+"] input").val(value);
    }
});
openerp.web.ViewEditor.FieldSelect = openerp.web.ViewEditor.Field.extend({
    init: function(view, node) {
        this._super(view, node);
        this.node = node;
        this.template = "view_selection";
    },
    start: function() {
        var self = this;
        this._super.apply(this, arguments);
    },
    set_value: function(id,value) {
        //ToDo
    }
});
openerp.web.ViewEditor.property_widget = new openerp.web.Registry({
    'required' : 'openerp.web.ViewEditor.FieldBoolean',
    'readonly' : 'openerp.web.ViewEditor.FieldBoolean',
    'nolabel' : 'openerp.web.ViewEditor.FieldBoolean',
    'completion' : 'openerp.web.ViewEditor.FieldBoolean',
    'widget' : 'openerp.web.ViewEditor.FieldSelect',
    'groups' : 'openerp.web.ViewEditor.FieldSelect',
    'position': 'openerp.web.ViewEditor.FieldSelect',
    'icon': 'openerp.web.ViewEditor.FieldSelect',
    'align': 'openerp.web.ViewEditor.FieldSelect',
    'special': 'openerp.web.ViewEditor.FieldSelect',
    'type': 'openerp.web.ViewEditor.FieldSelect',
    'target': 'openerp.web.ViewEditor.FieldSelect'
});
};