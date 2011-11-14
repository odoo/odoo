openerp.web.view_editor = function(openerp) {
var _t = openerp.web._t;
var QWeb = openerp.web.qweb;
openerp.web.ViewEditor =   openerp.web.Widget.extend({
    init: function(parent, element_id, dataset, view, options) {
        this._super(parent);
        this.element_id = element_id
        this.parent = parent
        this.dataset = new openerp.web.DataSetSearch(this, 'ir.ui.view', null, null);
        this.model = dataset.model;
        this.xml_element_id = 0;
        this.property = openerp.web.ViewEditor.property_widget;
    },
    start: function() {
        this.init_view_editor();
    },
    init_view_editor: function() {
        var self = this;
        var action = {
            name: _.sprintf("Manage Views (%s)", this.model),
            context: this.session.user_context,
            domain: [["model", "=", this.model]],
            res_model: 'ir.ui.view',
            views: [[false, 'list']],
            type: 'ir.actions.act_window',
            target: "current",
            limit: this.dataset.limit || 80,
            auto_search: true,
            flags: {
                sidebar: false,
                deletable: false,
                views_switcher: false,
                action_buttons: false,
                search_view: false,
                pager: false,
                radio: true,
                select_view_id: self.parent.fields_view.view_id
            },
        };
        this.view_edit_dialog = new openerp.web.Dialog(this, {
            modal: true,
            title: 'ViewEditor',
            width: 750,
            height: 500,
            buttons: {
                "Create": function(){
                    self.on_create_view();
                },
                "Edit": function(){
                    self.xml_element_id = 0;
                    self.get_arch();
                },
                "Remove": function(){
                    self.do_delete_view();
                },
                "Close": function(){
                    self.view_edit_dialog.close();
                }
            },
        }).start().open();
        this.main_view_id = this.parent.fields_view.view_id;
        this.action_manager = new openerp.web.ActionManager(this);
        this.action_manager.appendTo(this.view_edit_dialog);
        $.when(this.action_manager.do_action(action)).then(function() {
            var viewmanager = self.action_manager.inner_viewmanager,
                controller = viewmanager.views[viewmanager.active_view].controller;
            controller.on_loaded.add_last(function(){
                $(controller.groups).bind({
                    'selected': function(e, ids, records) {
                        self.main_view_id = ids[0];
                    }
                })
            });
        });
    },
    on_create_view: function() {
        var self = this;
        this.create_view_dialog = new openerp.web.Dialog(this,{
            modal: true,
            title: _.sprintf("Create a view (%s)", self.model),
            width: 500,
            height: 400,
            buttons: {
                    "Save": function(){
                        var view_values = {};
                        _.each(self.create_view_widget, function(widget) {
                            if (widget.dirty && !widget.invalid) {
                                view_values[widget.name] = widget.get_value();
                            }
                        });
                        $.when(self.do_save_view(view_values)).then(function() {
                            self.create_view_dialog.close();
                            var controller = self.action_manager.inner_viewmanager.views[self.action_manager.inner_viewmanager.active_view].controller;
                            controller.reload_content();
                        });
                    },
                    "Cancel": function(){
                        self.create_view_dialog.close();
                    }
                }
        });
        this.create_view_dialog.start().open();
        var view_widget = [{'name': 'view_name', 'type': 'char', 'required': true, 'value' : this.model + '.custom_' + Math.round(Math.random() * 1000)},
                           {'name': 'view_type', 'type': 'selection', 'required': true, 'value': 'Form', 'selection': [['',''],['tree', 'Tree'],['form', 'Form'],['graph', 'Graph'],['calendar', 'Calender']]},
                           {'name': 'pririty', 'type': 'char', 'required': true, 'value':'16'}];
        this.create_view_dialog.$element.append('<table id="create_view"  style="width:400px" class="oe_forms"></table>');
        this.create_view_widget = [];
        _.each(view_widget, function(widget) {
            var type_widget =  new (self.property.get_any([widget.type])) (self.create_view_dialog, widget.name);
            if (widget.selection) {
                type_widget.selection = widget.selection;
            }
            type_widget.required = widget.required;
            self.create_view_dialog.$element.find('table[id=create_view]').append('<tr><td align="right">' + widget.name + ':</td><td  id="' +widget.name+ '">' + type_widget.render()+'</td></tr>');
            var value = null;
            if (widget.value) {
                value = [widget.name, widget.value];
                type_widget.dirty = true;
            }
            type_widget.start();
            type_widget.set_value(value)
            self.create_view_widget.push(type_widget);
        });
    },
    do_save_view: function(values) {
        def = $.Deferred();
        var field_dataset = new openerp.web.DataSetSearch(this, this.model, null, null);
        var model_dataset = new openerp.web.DataSetSearch(this, 'ir.model', null, null);
        var view_string = "", field_name = false, self = this;
        field_dataset.call( 'fields_get', [],  function(fields) {
            _.each(['name', 'x_name'], function(value) {
                if (_.include(_.keys(fields), value)) {
                    field_name = value;
                    return false;
                }
            });
            if (field_name) {
                model_dataset.read_slice(['name','field_id'], {"domain": [['model','=',self.model]]}, function(records) {
                    if (records) {view_string = records[0].name;}
                    var arch = _.sprintf("<?xml version='1.0'?>\n<%s string='%s'>\n\t<field name='%s'/>\n</%s>", values.view_type, view_string, field_name, values.view_type);
                    var vals = {'model': self.model, 'name': values.view_name, 'priority': values.priority, 'type': values.view_type, 'arch': arch};
                    self.dataset.create(vals, function(suc) {
                        def.resolve();
                    });
                });
            }
        });
        return def.promise();
    },
    add_node_name : function(node) {
        if(node.tagName.toLowerCase() == "button" || node.tagName.toLowerCase() == "field"){
            return (node.getAttribute('name'))?
                _.sprintf( "<%s name='%s'>",node.tagName.toLowerCase(), node.getAttribute('name')):
                _.sprintf( "<%s>",node.tagName.toLowerCase());
        }else if(node.tagName.toLowerCase() == "group"){
            return (node.getAttribute('string'))?
                _.sprintf( "<%s>",node.getAttribute('string')):
                _.sprintf( "<%s>",node.tagName.toLowerCase());
        }else{
            return (node.getAttribute('string'))?
                _.sprintf( "<%s string='%s'>",node.tagName.toLowerCase(), node.getAttribute('string')):
                _.sprintf( "<%s>",node.tagName.toLowerCase());
        }
    },
    do_delete_view: function() {
        if (confirm(_t("Do you really want to remove this view?"))) {
	        var controller = this.action_manager.inner_viewmanager.views[this.action_manager.inner_viewmanager.active_view].controller;
            this.dataset.unlink([this.main_view_id]).then(function() {
                controller.reload_content();
            });
        }
    },
    create_View_Node: function(node){
        var self = this;
        ViewNode = {
            'level': ($(node).parents()).length + 1,
            'id': self.xml_element_id += 1,
            'att_list': [],
            'name': self.add_node_name(node),
            'child_id': []
        }
        ViewNode.att_list.push(node.tagName.toLowerCase());
        _.each(node.attributes ,function(att){
           ViewNode.att_list.push([att.nodeName,att.nodeValue]);
       });
        return ViewNode;
    },
    append_child_object: function(main_object, parent_id, child_obj_list) {
        var self = this;
            if(main_object.id == parent_id){
                var pare
                main_object.child_id = child_obj_list;
                return main_object;
            }else{
                _.each(main_object.child_id ,function(child_object){
                    self.append_child_object(child_object, parent_id, child_obj_list);
                });
            }
    },
    convert_arch_to_obj: function(xml_Node, main_object, parent_id){
        var self = this;
        var child_obj_list = [];
        _.each(xml_Node,function(element){
           child_obj_list.push(self.create_View_Node(element)) ;
        });
        this.append_child_object(main_object, parent_id, child_obj_list);
        var obj_xml_list = _.zip(xml_Node,child_obj_list);
        _.each(obj_xml_list, function(node){
            var children = _.filter(node[0].childNodes, function (child) {
                return child.nodeType == 1;
            });
            if(children){
            self.convert_arch_to_obj(children, main_object, node[1].id);}
        });
        return main_object;
    },
    parse_xml: function(arch, view_id) {
        main_object = {
            'level': 0,
            'id': this.xml_element_id +=1,
            'att_list': [],
            'name': _.sprintf("<view view_id = %s>", view_id),
            'child_id': []
        };
        var xml_arch = QWeb.load_xml(arch);
        return [this.convert_arch_to_obj(xml_arch.childNodes, main_object, this.xml_element_id)];
    },
    get_arch: function() {
        var self = this;
        var view_arch_list = [];
        this.dataset.read_ids([parseInt(self.main_view_id)], ['arch', 'type'], function(arch) {
            var arch_object = self.parse_xml(arch[0].arch, self.main_view_id);
            self.main_view_type = arch[0].type
            view_arch_list.push({"view_id": self.main_view_id, "arch": arch[0].arch});
            self.dataset.read_slice([], {domain: [['inherit_id','=', parseInt(self.main_view_id)]]}, function(result) {
                _.each(result, function(res) {
                    view_arch_list.push({"view_id": res.id, "arch": res.arch});
                    self.inherit_view(arch_object, res);
                });
                return self.edit_view({"main_object": arch_object,
                    "parent_child_id": self.parent_child_list(arch_object, []),
                    "arch": view_arch_list});
            });
        });
    },
    parent_child_list : function(one_object, parent_list) {
        var self = this;
        _.each(one_object , function(element) {
            if (element.child_id.length != 0) {
                parent_list.push({"key": element.id, "value": _.pluck(element.child_id, 'id')});
                self.parent_child_list(element.child_id, parent_list);
            }
        });
        return parent_list;
    },
    inherit_view : function(arch_object, result) {
        var self = this;
        var xml_list = [];
        var xml_arch = QWeb.load_xml(result.arch);
        if(xml_arch.childNodes[0].tagName == "data"){
            xml_list = _.filter(xml_arch.childNodes[0].childNodes, function (child) {
                            return child.nodeType == 1;
                        });
        }else{ xml_list.push( xml_arch.childNodes[0] ); }

        _.each(xml_list, function(xml) {
            var expr_to_list = [];
            var xpath_arch_object = self.parse_xml(QWeb.tools.xml_node_to_string(xml), result.id);
            if(xml.tagName == "xpath"){
                var part_expr = _.without(xml.getAttribute('expr').split("/"), "");
                _.each(part_expr, function(part) {
                    expr_to_list.push(_.without($.trim(part.replace(/[^a-zA-Z 0-9 _]+/g,'!')).split("!"), ""));
                });
            }else{
                var temp = _.reject(xpath_arch_object[0].child_id[0].att_list, function(list) {
                    return _.include(list, "position")
                });
                expr_to_list = [_.flatten(temp)];
            }
            self.inherit_apply(expr_to_list, arch_object ,xpath_arch_object);
        });
    },
    inherit_apply: function(expr_list ,arch_object ,xpath_arch_object) {
        var self = this;
        if (xpath_arch_object.length) {
            var check = expr_list[0];
            var obj;
            switch (check.length) {
                case 2:
                    if (parseInt(check[1])) {
                        //for field[3]
                        var temp_list = _.select(arch_object, function(element) {
                            return _.include(_.flatten(element.att_list), check[0]);
                        });
                        obj = arch_object[_.indexOf(arch_object, temp_list[parseInt(check[1]) - 1])];
                    } else {
                        //for notebook[last()]
                        obj = _.detect(arch_object, function(element) {
                            return _.include(_.flatten(element.att_list), check[0]);
                        });
                    }
                    break;
                case 3:
                    //for field[@name='type']
                    obj = _.detect(arch_object, function(element){
                        if ((_.intersection(_.flatten(element.att_list), _.uniq(check))).length == check.length) {
                            return element;
                        }
                    });
                    break;
                case 1:
                    //for /form/notebook
                    var temp_list = _.select(arch_object, function(element) {
                        return _.include(_.flatten(element.att_list), check[0]);
                    });
                    if (temp_list.length != 0) {
                        expr_list.length == 1 ? obj = temp_list[0] : expr_list.shift();
                    }
                    break;
            }
            if (obj) {
                expr_list.shift();
                if (expr_list.length) {
                    self.inherit_apply(expr_list, obj.child_id, xpath_arch_object);
                } else {
                    self.increase_level(xpath_arch_object[0], obj.level + 1);
                    obj.child_id.push(xpath_arch_object[0]);
                    xpath_arch_object.pop();
                }
            } else {
                _.each(arch_object, function(element) {
                    self.inherit_apply(expr_list, element.child_id, xpath_arch_object);
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
        this.edit_xml_dialog = new openerp.web.Dialog(this, {
            modal: true,
            title: _.sprintf("View Editor %d - %s", self.main_view_id, self.model),
            width: 750,
            height: 500,
            buttons: {
                "Inherited View": function() {
                    //todo
                },
                "Preview": function() {
                    var action = {
                        context: self.session.user_context,
                        res_model: self.model,
                        views: [[self.main_view_id, self.main_view_type]],
                        type: 'ir.actions.act_window',
                        target: "new",
                        flags: {
                            sidebar: false,
                            views_switcher: false,
                            action_buttons: false,
                            search_view: false,
                            pager: false,
                        },
                    };
                    var action_manager = new openerp.web.ActionManager(self);
                    action_manager.do_action(action);
                },
                "Close": function(){
                    self.edit_xml_dialog.close();
                }
            }
        }).start().open();
        var no_property_att = [];
        _.each(_PROPERTIES, function(val, key) {
            if (! val.length) no_property_att.push(key);
        });
        this.edit_xml_dialog.$element.html(QWeb.render('view_editor', {'data': one_object['main_object'], 'no_properties': no_property_att}));
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
            var side = $(this).closest("tr[id^='viewedit-']");
            var clicked_tr_id = (side.attr('id')).split('-')[1];
            var img = side.find("img[id='parentimg-" + clicked_tr_id + "']").attr('src');
            var clicked_tr_level = parseInt(side.attr('level'));
            var cur_tr = side;
            var last_tr;
            var next_tr;
            var tr_to_move = [];
            tr_to_move.push(side);
            var view_id;
            var view_xml_id;
            var view_find = side;
            var min_level = clicked_tr_level;
            while (1) {
                view_find = view_find.prev();
                if ((self.edit_xml_dialog.$element.find(view_find).find('a').text()).search("view_id") != -1
                        && parseInt(view_find.attr('level')) < min_level ) {
                    view_id = parseInt(($(view_find).find('a').text()).replace(/[^0-9]+/g, ''));
                    view_xml_id = (view_find.attr('id')).split('-')[1];
                    break;
                }
                if(view_find.attr('level') < min_level){
                    min_level = parseInt(view_find.attr('level'));
                }
            }
            switch (this.id) {
                case "side-add":
                    break;
                case "side-remove":
                    break;
                case "side-edit":
                    var tr = $(this).closest("tr[id^='viewedit-']").find('a').text();
                    var tag = _.detect(_.keys(_PROPERTIES),function(res){
                        return _.includes(tr, res);
                    });
                    var properties = _PROPERTIES[tag];
                    self.on_edit_node(properties, clicked_tr_id, one_object, view_id, view_xml_id, clicked_tr_level);
                    break;
                case "side-up":
                    while (1) {
                        var prev_tr = cur_tr.prev();
                        if (clicked_tr_level >= parseInt(prev_tr.attr('level')) || prev_tr.length == 0) {
                           last_tr = prev_tr;
                           break;
                        }
                        cur_tr = prev_tr;
                    }
                    if (img) {
                    self.edit_xml_dialog.$element.find("img[id='parentimg-" + clicked_tr_id + "']").
                            attr('src', '/web/static/src/img/expand.gif');
                        while (1) {
                            next_tr = side.next();
                            if (parseInt(next_tr.attr('level')) <= clicked_tr_level || next_tr.length == 0) {
                                break;
                            } else {
                                next_tr.hide();
                                tr_to_move.push(next_tr);
                                side = next_tr;
                            }
                        }
                    }
                    if (last_tr.length != 0 && parseInt(last_tr.attr('level')) == clicked_tr_level &&
                            (self.edit_xml_dialog.$element.find(last_tr).find('a').text()).search("view_id") == -1) {
                        _.each(tr_to_move, function(rec) {
                             $(last_tr).before(rec);
                        });
                        self.do_save_update_arch(one_object, view_id, view_xml_id, clicked_tr_id, clicked_tr_level, "up");
                    }
                break;
            case "side-down":
                if (img) {
                    while (1) {
                        next_tr = cur_tr.next();
                        if ( parseInt(next_tr.attr('level')) <= clicked_tr_level || next_tr.length == 0) {
                            last_tr = next_tr;
                            break;
                        } else {
                            tr_to_move.push(next_tr);
                            cur_tr = next_tr;
                        }
                   }
                } else {
                    last_tr = cur_tr.next();
                }

                if ((self.edit_xml_dialog.$element.find(last_tr).find('a').text()).search("view_id") != -1) {
                    return;
                }
                if (last_tr.length != 0 &&  parseInt(last_tr.attr('level')) == clicked_tr_level) {
                    var last_tr_id = (last_tr.attr('id')).split('-')[1];
                    img = last_tr.find("img[id='parentimg-" + last_tr_id + "']").attr('src');
                    if (img) {
                        self.edit_xml_dialog.$element.find("img[id='parentimg-" + last_tr_id + "']").
                                                        attr('src', '/web/static/src/img/expand.gif');
                        while (1) {
                            var next_tr = last_tr.next();
                            if (next_tr.attr('level') <= clicked_tr_level || next_tr.length == 0) break;
                            next_tr.hide();
                            last_tr = next_tr;
                        }
                    }
                    tr_to_move.reverse();
                    _.each(tr_to_move, function(rec) {
                       $(last_tr).after(rec);
                    });
                    self.do_save_update_arch(one_object, view_id, view_xml_id, clicked_tr_id, clicked_tr_level, "down");
                }
                break;
            }
        });
    },
    do_save_update_arch: function(one_object, view_id, view_xml_id, clicked_tr_id, clicked_tr_level, move_direct, update_values) {
        var self = this;
        var arch = _.detect(one_object['arch'], function(element) {return element.view_id == view_id;});
        var obj = self.get_object_by_id(view_xml_id, one_object['main_object'], []);
         //for finding xpath tag from inherit view
        var xml_arch = QWeb.load_xml(arch.arch);
        if (xml_arch.childNodes[0].tagName == "data") {
            var check_list = _.flatten(obj[0].child_id[0].att_list);
            var children = _.filter(xml_arch.childNodes[0].childNodes, function (child) {
                return child.nodeType == 1;
            });
            arch.arch = _.detect(children, function(xml_child){
                var temp_obj = self.create_View_Node(xml_child);
                var insert = _.intersection(_.flatten(temp_obj.att_list),_.uniq(check_list));
                if (insert.length == check_list.length ) {return xml_child;}
            });
        }
        return self.do_save_xml(arch.arch, obj[0].child_id[0], parseInt(clicked_tr_id), [], parseInt(clicked_tr_level),
                        parseInt(view_id), arch, move_direct, update_values);
    },
    get_object_by_id: function(view_xml_id, one_object, result) {
        var self = this;
        if (result.length == 0 ) {
            var check = _.detect(one_object , function(obj) {
                return view_xml_id == obj.id;
            });
            if (check) {result.push(check);};
            _.each(one_object, function(obj) {
               self.get_object_by_id(view_xml_id, obj.child_id, result);
            });
        }
        return result;
    },
    do_save_xml: function(arch1, obj, id, child_list, level, view_id, arch, move_direct, update_values){
        var self = this;
        var children_list =  $(arch1).children();
        var list_obj_xml = _.zip(children_list, obj.child_id);
        if (id) {
            if (obj.id == id) {
                var id;
                var index = _.indexOf(child_list, obj);
                if (move_direct == "down") {
                    var next = $(arch1).next();
                    $(next).after(arch1);
                    var re_insert_obj = child_list.splice(index, 1);
                    child_list.splice(index+1, 0, re_insert_obj[0]);
                } else if (move_direct == "up") {
                    var prev = $(arch1).prev();
                    $(prev).before(arch1);
                    var re_insert_obj = child_list.splice(index, 1);
                    child_list.splice(index-1, 0, re_insert_obj[0]);
                } else if (move_direct == "update_node") {
                    _.each(update_values, function(val){
                        $(arch1).attr(val[0],val[1]);
                    });
                    var new_obj = self.create_View_Node(arch1);
                    new_obj.id = obj.id,new_obj.child_id = obj.child_id;
                    self.edit_xml_dialog.$element.find("tr[id='viewedit-"+id+"']").find('a').text(new_obj.name);
                    child_list.splice(index, 1, new_obj);
                }
                var parent = $(arch1).parents();
                var convert_to_utf = QWeb.tools.xml_node_to_string(parent[parent.length-1]);
                convert_to_utf = convert_to_utf.replace('xmlns="http://www.w3.org/1999/xhtml"', "");
                convert_to_utf = '<?xml version="1.0"?>' + convert_to_utf;
                arch.arch = convert_to_utf;
                this.dataset.write(parseInt(view_id),{"arch":convert_to_utf}, function(r) {
                });
            }
            if (obj.level <= level) {
                _.each(list_obj_xml, function(child_node) {
                    self.do_save_xml(child_node[0], child_node[1], id, obj.child_id, level, view_id, arch, move_direct, update_values);
                });
            }
        }
    },
    on_expand: function(expand_img){
        var level = parseInt($(expand_img).closest("tr[id^='viewedit-']").attr('level'));
        var cur_tr = $(expand_img).closest("tr[id^='viewedit-']");
        while (1) {
            var nxt_tr = cur_tr.next();
            if (parseInt(nxt_tr.attr('level')) > level) {
                cur_tr = nxt_tr;
                nxt_tr.hide();
            } else return nxt_tr;
        }
    },
    on_collapse: function(collapse_img, parent_child_id, id, main_object) {
        var self = this;
        var id = collapse_img.id.split('-')[1];
        var datas = _.detect(parent_child_id, function(res) {
            return res.key == id;
        });
        _.each(datas.value, function (rec) {
            var tr = self.edit_xml_dialog.$element.find("tr[id='viewedit-" + rec + "']");
            tr.find("img[id='parentimg-" + rec + "']").attr('src', '/web/static/src/img/expand.gif');
            tr.show();
        });
    },
    on_edit_node:function(properties, clicked_tr_id, obj, view_id, view_xml_id, clicked_tr_level){
        var self = this;
        this.edit_node_dialog = new openerp.web.Dialog(this,{
            modal: true,
            title: 'Properties',
            width: 500,
            height: 400,
            buttons: {
                    "Update": function(){
                        var update_values = [];
                        _.each(self.edit_widget, function(widget) {
                            if (widget.dirty && !widget.invalid) {
                                update_values.push([widget.name, widget.get_value()]);
                            }
                        });
                        self.do_save_update_arch(obj, view_id, view_xml_id, clicked_tr_id, clicked_tr_level, "update_node", update_values);
                        self.edit_node_dialog.close();
                    },
                    "Cancel": function(){
                        self.edit_node_dialog.close();
                    }
                }
        });
        this.edit_node_dialog.start().open();
        var widget = _.keys(self.property.map);
        var arch_val = self.get_object_by_id(clicked_tr_id,obj['main_object'], []);
        this.edit_node_dialog.$element.append('<table id="rec_table"  style="width:400px" class="oe_forms"></table>');
        this.edit_widget = [];
        _.each(properties, function(record) {
            var id = record,
            type_widget;
            self.ready  = $.when(self.on_groups(id)).then(function () {
                if (_.include(widget,id)){
                    type_widget =  new (self.property.get_any(['undefined' , id, arch_val[0]['att_list'][0]])) (self.edit_node_dialog, id);
                } else {
                    type_widget = new openerp.web.ViewEditor.FieldChar (self.edit_node_dialog, id);
                }
                var value = _.detect(arch_val[0]['att_list'],function(res) {
                    return _.include(res, id);
                });
                if (id == 'groups') type_widget.selection = self.groups;
                self.edit_node_dialog.$element.find('table[id=rec_table]').append('<tr><td align="right">'+id+':</td><td>'+type_widget.render()+'</td></tr>');
                type_widget.start();
                type_widget.set_value(value)
                self.edit_widget.push(type_widget);
            });
        });
    },
     //for getting groups
    on_groups: function(id){
        var self = this,
        def = $.Deferred();
        if (id != 'groups') {
            self.groups = false;
            return false;
        }
        var group_ids = [],
        group_names = {},
        groups = [];
        var res_groups = new openerp.web.DataSetSearch(this,'res.groups', null, null),
            model_data = new openerp.web.DataSetSearch(self,'ir.model.data', null, null);
            res_groups
            .read_slice([], {})
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
                        groups.push([res_group.module + "." + res_group.name,group_names[res_group.res_id]]);
                    });
                    self.groups = groups;
                    def.resolve();
                });
            })
        return def.promise();
    }
});
openerp.web.ViewEditor.Field = openerp.web.Class.extend({
    init: function(view, id) {
        this.$element = view.$element;
        this.dirty = false;
        this.name = id;
        this.required = false;
        this.invalid = false;
    },
    start: function () {
        this.update_dom();
    },
    update_dom: function() {
        this.$element.find("td[id="+ this.name+"]").toggleClass('invalid', this.invalid);
        this.$element.find("td[id="+ this.name+"]").toggleClass('required', this.required);
    },
    on_ui_change: function() {
        var value = this.get_value();
        value = value instanceof Array ? value[1] : value;
        if (this.required && !value) {
            this.invalid = true;
        } else {
            this.invalid = false;
        }
        this.dirty = true;
        this.update_dom();
    },
    render: function() {
        return QWeb.render(this.template, {widget: this});
    },
});
openerp.web.ViewEditor.FieldBoolean = openerp.web.ViewEditor.Field.extend({
    template : "vieweditor_boolean",
    start: function() {
        var self = this;
        this.$element.find("input[id="+ self.name+"]").change(function() {
            self.on_ui_change();
        });
        this._super();
    },
    set_value: function(value) {
        if (value) {
            this.$element.find("input[id=" + this.name+ "]").attr('checked', value[1]);
        }
    },
    get_value: function() {
        var value = this.$element.find("input[id=" + this.name + "]").is(':checked');
        return value ? value: null;
    }
});
openerp.web.ViewEditor.FieldChar = openerp.web.ViewEditor.Field.extend({
    template : "vieweditor_char",
    start: function () {
        var self = this;
        this.$element.find("input[id="+ this.name+"]").css('width','100%').change(function() {
            self.on_ui_change();
        });
        this._super();
    },
    set_value: function(value) {
        value ? this.$element.find("input[id=" + this.name + "]").val(value[1]): this.$element.find("tr[id=" + this.name + "] input").val();
    },
    get_value: function() {
        var value= this.$element.find("input[id=" + this.name + "]").val();
        return value ? value: "";
    }
});
openerp.web.ViewEditor.FieldSelect = openerp.web.ViewEditor.Field.extend({
    template : "vieweditor_selection",
    init: function(view, id) {
        this._super(view, id);
        this.selection = false;
    },
    start: function () {
        var self = this;
        this.$element.find("select[id=" + this.name + "]").css('width', '100%').change(function() {
            self.on_ui_change();
        });
        this._super();
    },
    set_value: function(value) {
        value = value === null ? false : value;
        value = value instanceof Array ? value[1] : value;
        var index = 0;
        for (var i = 0, ii = this.selection.length; i < ii; i++) {
            if ((this.selection[i] instanceof Array && this.selection[i][1] === value) || this.selection[i] === value) index = i;
        }
        this.$element.find("select[id=" + this.name + "]")[0].selectedIndex = index;
    },
    get_value: function() {
        var value = this.$element.find("select[id=" + this.name + "]").val();
        return  value ? value: "";
    }
});
openerp.web.ViewEditor.WidgetProperty = openerp.web.ViewEditor.FieldSelect.extend({
    init: function(view, id) {
        this._super(view, id);
        this.registry = openerp.web.form.widgets;
        var values = _.keys(this.registry.map);
        values.push('');
        values.sort();
        this.selection = values;
    },
});
openerp.web.ViewEditor.IconProperty = openerp.web.ViewEditor.FieldSelect.extend({
    init: function(view, id) {
        this._super(view, id);
        this.selection = icons;
    },
});
openerp.web.ViewEditor.ButtonTargetProperty = openerp.web.ViewEditor.FieldSelect.extend({
    init: function(view, id) {
        this._super(view, id);
        this.selection = [['', ''], ['new', 'New Window']];
    },
});
openerp.web.ViewEditor.ButtonTypeProperty = openerp.web.ViewEditor.FieldSelect.extend({
    init: function(view, id) {
        this._super(view, id);
        this.selection = [['', ''], ['action', 'Action'], ['object', 'Object'], ['workflow', 'Workflow'], ['server_action', 'Server Action']];
    },
});
openerp.web.ViewEditor.AlignProperty = openerp.web.ViewEditor.FieldSelect.extend({
    init: function(view, id) {
        this._super(view, id);
        this.selection = [['', ''], ['0.0', 'Left'], ['0.5', 'Center'], ['1.0', 'Right']];
    },
});
openerp.web.ViewEditor.ButtonSpecialProperty = openerp.web.ViewEditor.FieldSelect.extend({
    init: function(view, id) {
        this._super(view, id);
        this.selection = [['',''],['save', 'Save Button'], ['cancel', 'Cancel Button'], ['open', 'Open Button']];
    },
});
openerp.web.ViewEditor.PositionProperty = openerp.web.ViewEditor.FieldSelect.extend({
    init: function(view, id) {
        this._super(view, id);
        this.selection = [['',''],['after', 'After'],['before', 'Before'],['inside', 'Inside'],['replace', 'Replace']];
    },
});
openerp.web.ViewEditor.GroupsProperty = openerp.web.ViewEditor.FieldSelect.extend({
    init: function(view, id) {
        this._super(view, id);
        this.multiple = true;
    },
    start: function () {
        this._super();
        this.$element.find("select[id=" + this.name + "]").css('height', '100px').attr("multiple",true);
        this._super();
    },
    set_value: function(value) {
        var self = this;
        self.$element.find("#groups option").attr("selected",false);
        if (!value) return false;
        _.each(this.selection, function(item) {
            if (_.include(value[1].split(','), item[0])) {
                self.$element.find("select[id="+self.name+"] option[value='" + item[0] +"']").attr("selected",1)
            }
         });
    }
});
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
    'board': ['style'],
    'column' : [],
    'action' : ['name', 'string', 'colspan', 'groups'],
    'tree' : ['string', 'colors', 'editable', 'link', 'limit', 'min_rows'],
    'graph' : ['string', 'type'],
    'calendar' : ['string', 'date_start', 'date_stop', 'date_delay', 'day_length', 'color', 'mode'],
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
            'terp-project', 'terp-report', 'terp-stock', 'terp-calendar', 'terp-graph'
];
openerp.web.ViewEditor.property_widget = new openerp.web.Registry({
    'required' : 'openerp.web.ViewEditor.FieldBoolean',
    'readonly' : 'openerp.web.ViewEditor.FieldBoolean',
    'nolabel' : 'openerp.web.ViewEditor.FieldBoolean',
    'completion' : 'openerp.web.ViewEditor.FieldBoolean',
    'widget' : 'openerp.web.ViewEditor.WidgetProperty',
    'groups' : 'openerp.web.ViewEditor.GroupsProperty',
    'position' : 'openerp.web.ViewEditor.PositionProperty',
    'icon' : 'openerp.web.ViewEditor.IconProperty',
    'align' : 'openerp.web.ViewEditor.AlignProperty',
    'special' : 'openerp.web.ViewEditor.ButtonSpecialProperty',
    'type' : 'openerp.web.ViewEditor.ButtonTypeProperty',
    'target' : 'openerp.web.ViewEditor.ButtonTargetProperty',
    'selection' : 'openerp.web.ViewEditor.FieldSelect',
    'char' : 'openerp.web.ViewEditor.FieldChar',
});
};
