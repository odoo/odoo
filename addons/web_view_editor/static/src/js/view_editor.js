openerp.web_view_editor = function(instance) {
var _t = instance.web._t;
var QWeb = instance.web.qweb;
instance.web.ViewManagerAction.include({
    on_debug_changed:function(evt){
        var val = $(evt.currentTarget).find('option:selected').val(),
            current_view = this.views[this.active_view].controller;
        if(val === "manage_views"){
            if (current_view.fields_view && current_view.fields_view.arch) {
                    var view_editor = new instance.web_view_editor.ViewEditor(current_view, current_view.$el, this.dataset, current_view.fields_view.arch);
                    view_editor.start();
                } else {
                    this.do_warn(_t("Manage Views"),
                            _t("Could not find current view declaration"));
                }
                evt.currentTarget.selectedIndex = 0;
        }else{
            return this._super.apply(this,arguments);
        }
    }
});
instance.web_view_editor.ViewEditor =   instance.web.Widget.extend({
    init: function(parent, element_id, dataset, view, options) {
        this._super(parent);
        this.parent = parent;
        this.dataset = new instance.web.DataSetSearch(this, 'ir.ui.view', null, null),
        this.model = dataset.model;
        this.xml_element_id = 0;
        this.property = instance.web_view_editor.ViewEditor.property_widget;
        this.one_object = false;
    },
    start: function() {
        this.init_view_editor();
    },
    init_view_editor: function() {
        var self = this,
            action_title = _.str.sprintf(_t("Manage Views (%s)"), this.model);
        var action = {
            name: action_title,
            context: this.session.user_context,
            domain: [["model", "=", this.model]],
            res_model: 'ir.ui.view',
            views: [[false, 'list']],
            type: 'ir.actions.act_window',
            target: "current",
            limit: this.dataset.limit || 80,
            auto_search : true,
            flags: {
                sidebar: false,
                deletable: false,
                views_switcher: false,
                action_buttons: false,
                search_view: false,
                pager: false,
                radio: true,
                select_view_id: self.parent.fields_view.view_id
            }
        };
        this.view_edit_dialog = new instance.web.Dialog(this, {
            title: action_title,
            buttons: [
                {text: _t("Create"), click: function() { self.on_create_view(); }},
                {text: _t("Edit"), click: function() { self.xml_element_id = 0; self.get_arch(); }},
                {text: _t("Remove"), click: function() { self.do_delete_view(); }},
                {text: _t("Close"), click: function() { self.view_edit_dialog.close(); window.location.reload(); }}
            ]
        }).open();
        this.view_edit_dialog.on("closing", this, function(){window.location.reload();});
        this.main_view_id = this.parent.fields_view.view_id;
        this.action_manager = new instance.web.ActionManager(this);
        this.action_manager.appendTo(this.view_edit_dialog.$el);
        $.when(this.action_manager.do_action(action)).done(function() {
            var viewmanager = self.action_manager.inner_widget;
            var controller = viewmanager.views[viewmanager.active_view].controller;
            $(controller.groups).bind({
                'selected': function (e, ids, records, deselected) {
                        self.main_view_id = ids[0];
                }
            });
        });
    },
    on_create_view: function() {
        var self = this;
        this.create_view_dialog = new instance.web.Dialog(this, {
            title: _.str.sprintf(_t("Create a view (%s)"), self.model),
            buttons: [
                {text: _t("Save"), click: function () {
                    var view_values = {};
                    var warn = false;
                    _.each(self.create_view_widget, function(widget) {
                        if (widget.is_invalid) {
                            warn = true;
                            return false;
                        }
                        if (widget.dirty && !widget.is_invalid) {
                            view_values[widget.name] = widget.get_value();
                        }
                    });
                    if (warn) {
                        self.on_valid_create_view(self.create_view_widget);
                    } else {
                        $.when(self.do_save_view(view_values)).done(function() {
                            self.create_view_dialog.close();
                            var controller = self.action_manager.inner_widget.views[self.action_manager.inner_widget.active_view].controller;
                            controller.reload_content();
                        });
                    }
                }},
                {text: _t("Cancel"), click: function () { self.create_view_dialog.close(); }}
            ]
        }).open();
        var view_widget = [{'name': 'view_name', 'string':'View Name', 'type': 'char', 'required': true, 'value' : this.model + '.custom_' + Math.round(Math.random() * 1000)},
                           {'name': 'view_type', 'string': 'View Type', 'type': 'selection', 'required': true, 'value': 'Form', 'selection': [['',''],['tree', 'Tree'],['form', 'Form'],['graph', 'Graph'],['calendar', 'Calender']]},
                           {'name': 'proirity', 'string': 'Priority', 'type': 'float', 'required': true, 'value':'16'}];
        this.create_view_dialog.$el.append('<table id="create_view"  style="width:400px" class="oe_form"></table>');
        this.create_view_widget = [];
        _.each(view_widget, function(widget) {
            var type_widget =  new (self.property.get_any([widget.type])) (self.create_view_dialog, widget);
            self.create_view_dialog.$el.find('table[id=create_view]').append('<tr><td width="100px" align="right">' + widget.string + ':</td>' + type_widget.render()+'</tr>');
            var value = null;
            if (widget.value) {
                value = widget.value;
                type_widget.dirty = true;
            }
            type_widget.start();
            type_widget.set_value(value);
            self.create_view_widget.push(type_widget);
        });
    },
    do_save_view: function(values) {
        def = $.Deferred();
        var field_dataset = new instance.web.DataSetSearch(this, this.model, null, null);
        var model_dataset = new instance.web.DataSetSearch(this, 'ir.model', null, null);
        var view_string = "", field_name = false, self = this;
        field_dataset.call( 'fields_get', []).done(function(fields) {
            _.each(['name', 'x_name'], function(value) {
                if (_.include(_.keys(fields), value)) {
                    field_name = value;
                    return false;
                }
            });
            if (field_name) {
                model_dataset.read_slice(['name','field_id'], {"domain": [['model','=',self.model]]}).done(function(records) {
                    if (records) {view_string = records[0].name;}
                    var arch = _.str.sprintf("<?xml version='1.0'?>\n<%s string='%s'>\n\t<field name='%s'/>\n</%s>", values.view_type, view_string, field_name, values.view_type);
                    var vals = {'model': self.model, 'name': values.view_name, 'priority': values.priority, 'type': values.view_type, 'arch': arch};
                    def = self.dataset.create(vals);
                });
            }
        });
        return def.promise();
    },
    on_valid_create_view: function(widgets) {
        var msg = "<ul>";
        _.each(widgets, function(widget) {
            if (widget.is_invalid) {
                msg += "<li>" + widget.name + "</li>";
            }
        });
        msg += "</ul>";
        this.do_warn(_t("The following fields are invalid :"), msg);
    },
    add_node_name : function(node) {
        if(node.tagName.toLowerCase() == "button" || node.tagName.toLowerCase() == "field"){
            return (node.getAttribute('name'))?
                _.str.sprintf( "<%s name='%s'>",node.tagName.toLowerCase(), node.getAttribute('name')):
                _.str.sprintf( "<%s>",node.tagName.toLowerCase());
        }else if(node.tagName.toLowerCase() == "group"){
            return (node.getAttribute('string'))?
                _.str.sprintf( "<%s>",node.getAttribute('string')):
                _.str.sprintf( "<%s>",node.tagName.toLowerCase());
        }else{
            return (node.getAttribute('string'))?
                _.str.sprintf( "<%s string='%s'>",node.tagName.toLowerCase(), node.getAttribute('string')):
                _.str.sprintf( "<%s>",node.tagName.toLowerCase());
        }
    },
    do_delete_view: function() {
        var self = this;
        if (confirm(_t("Do you really want to remove this view?"))) {
            var controller = this.action_manager.inner_widget.views[this.action_manager.inner_widget.active_view].controller;
            this.dataset.unlink([this.main_view_id]).done(function() {
                controller.reload_content();
                self.main_view_id = self.parent.fields_view.view_id;
            });
        }
    },
    create_View_Node: function(node){
        ViewNode = {
            'level': ($(node).parents()).length + 1,
            'id': this.xml_element_id += 1,
            'att_list': [],
            'name': this.add_node_name(node),
            'child_id': []
        };
        ViewNode.att_list.push(node.tagName.toLowerCase());
        _.each(node.attributes, function(att) {
            ViewNode.att_list.push([att.nodeName, att.nodeValue]);
       });
        return ViewNode;
    },
    append_child_object: function(main_object, parent_id, child_obj_list) {
        var self = this;
        if (main_object.id == parent_id) {
            main_object.child_id = child_obj_list;
            return main_object;
        } else {
            _.each(main_object.child_id, function(child_object) {
                self.append_child_object(child_object, parent_id, child_obj_list);
            });
        }
    },
    convert_arch_to_obj: function(xml_Node, main_object, parent_id) {
        var self = this;
        var child_obj_list = [];
        _.each(xml_Node, function(element) {
           child_obj_list.push(self.create_View_Node(element));
        });
        this.append_child_object(main_object, parent_id, child_obj_list);
        var obj_xml_list = _.zip(xml_Node, child_obj_list);
        _.each(obj_xml_list, function(node) {
            var children = _.filter(node[0].childNodes, function(child) {
                return child.nodeType == 1;
            });
            if (children) {
                self.convert_arch_to_obj(children, main_object, node[1].id);
            }
        });
        return main_object;
    },
    parse_xml: function(arch, view_id) {
        //First element of att_list must be element tagname.
        main_object = {
            'level': 0,
            'id': this.xml_element_id +=1,
            'att_list': ["view"],
            'name': _.str.sprintf("<view view_id = %s>", view_id),
            'child_id': []
        };
        var xml_arch = QWeb.load_xml(arch);
        return [this.convert_arch_to_obj(xml_arch.childNodes, main_object, this.xml_element_id)];
    },
    get_arch: function() {
        var self = this;
        var view_arch_list = [];
        this.dataset.read_ids([parseInt(self.main_view_id)], ['arch', 'type','priority']).done(function(arch) {
            if (arch.length) {
                var arch_object = self.parse_xml(arch[0].arch, self.main_view_id);
                self.main_view_type = arch[0].type == 'tree'? 'list': arch[0].type;
                view_arch_list.push({"view_id": self.main_view_id, "arch": arch[0].arch,"priority":arch[0].priority});
                self.dataset.read_slice([], {domain: [['inherit_id','=', parseInt(self.main_view_id)]]}).done(function(result) {
                    _.each(result, function(res) {
                        view_arch_list.push({"view_id": res.id, "arch": res.arch,"priority":res.priority});
                        self.inherit_view(arch_object, res);
                    });
                    return self.edit_view({"main_object": arch_object,
                        "parent_child_id": self.parent_child_list(arch_object, []),
                        "arch": view_arch_list});
                });
            } else {
                self.do_warn(_t("Please select view in list :"));
            }
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
        var self = this, xml_list = [], xml_arch = QWeb.load_xml(result.arch);
        if (xml_arch.childNodes[0].tagName == "data") {
            xml_list = _.filter(xml_arch.childNodes[0].childNodes, function(child) {
                return child.nodeType == 1;
            });
        } else {
            xml_list.push( xml_arch.childNodes[0]);
        }
        _.each(xml_list, function(xml) {
            var expr_to_list = [], xpath_arch_object = self.parse_xml(QWeb.tools.xml_node_to_string(xml), result.id);
            if (xml.tagName == "xpath") {
                var part_expr = _.without(xml.getAttribute('expr').split("/"), "");
                _.each(part_expr, function(part) {
                    expr_to_list.push(_.without($.trim(part.replace(/[^a-zA-Z 0-9 _]+/g,'!')).split("!"), ""));
                });
            } else {
                var temp = _.reject(xpath_arch_object[0].child_id[0].att_list, function(list) {
                    return list instanceof Array? _.include(list, "position"): false;
                });
                expr_to_list = [_.flatten(temp)];
            }
            self.inherit_apply(expr_to_list, arch_object ,xpath_arch_object);
        });
    },
    inherit_apply: function(expr_list ,arch_object ,xpath_arch_object) {
        var self = this;
        if (xpath_arch_object.length) {
            var check = expr_list[0], obj = false;
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
                        if ((_.intersection(_.flatten(element.att_list), _.uniq(check))).length == _.uniq(check).length) {
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
    do_select_row: function(row_id) {
        this.edit_xml_dialog.$el.find("tr[id^='viewedit-']").removeClass('ui-selected');
        this.edit_xml_dialog.$el.find("tr[id=viewedit-" + row_id + "]").addClass('ui-selected');
    },
    do_parent_img_hide_show: function(img) {
        if (_.str.include($(img).attr('src'), '/web/static/src/img/collapse.gif')) {
            $(img).attr('src', '/web/static/src/img/expand.gif');
            this.on_expand(img);
        } else {
            $(img).attr('src', '/web/static/src/img/collapse.gif');
            this.on_collapse(img);
        }
    },
    edit_view: function(one_object) {
        var self = this;
        this.one_object = one_object;
        this.edit_xml_dialog = new instance.web.Dialog(this, {
            title: _.str.sprintf(_t("View Editor %d - %s"), self.main_view_id, self.model),
            buttons: [
                {text: _t("Inherited View"), click: function(){
                    var selected_row = self.edit_xml_dialog.$el.find('.ui-selected');
                    if (selected_row.length) {
                        if(selected_row.find('a').text().search("field") != -1){
                            if (confirm(_t("Do you really wants to create an inherited view here?"))) {
                                self.inherited_view(selected_row);
                            }
                        }else{
                            alert(_t("Can't Update View"));
                        }
                    }else{
                        alert(_t("Select an element"));
                    }
                }},
                {text: _t("Preview"), click: function() {
                    var action = {
                        context: self.session.user_context,
                        res_model: self.model,
                        views: [[self.main_view_id, self.main_view_type]],
                        type: 'ir.actions.act_window',
                        target: "new",
                        auto_search: true,
                        flags: {
                            sidebar: false,
                            views_switcher: false,
                            action_buttons: false
                        }
                    };
                    var action_manager = new instance.web.ActionManager(self);
                    action_manager.do_action(action);
                }},
                {text: _t("Close"), click: function(){
                    self.action_manager.inner_widget.views[self.action_manager.inner_widget.active_view].controller.reload_content();
                    self.edit_xml_dialog.close();
                }}
            ]
        }).open();
        var no_property_att = [];
        _.each(_PROPERTIES, function(val, key) {
            if (! val.length) no_property_att.push(key);
        });
        this.edit_xml_dialog.$el.html(QWeb.render('view_editor', {'data': one_object['main_object'], 'no_properties': no_property_att}));
        this.edit_xml_dialog.$el.find("tr[id^='viewedit-']").click(function() {
            self.do_select_row(this.id.split('-')[1]);
        });
        this.edit_xml_dialog.$el.find("img[id^='parentimg-']").click(function() {
            self.do_parent_img_hide_show(this);
        });
        this.edit_xml_dialog.$el.find("img[id^='side-']").click(function() {
            self.on_select_img(this);
        });
    },
    inherited_view: function(selected_row){
        var self = this;
        var row_id = parseInt((selected_row.attr('id')).split('-')[1]);
        var obj = self.get_object_by_id(row_id,self.one_object['main_object'], [])[0];
        var view_name = this.model + '.inherit_' + Math.round(Math.random() * 1000);
        var view_find = selected_row;
        var view_id;
        var min_level = parseInt(selected_row.attr('level'));
        while (1) {
            view_find = view_find.prev();
            if (view_find.length == 0 ||
                    self.edit_xml_dialog.$el.find(view_find).find('a').text().search("view_id") != -1 &&
                    parseInt(view_find.attr('level')) < min_level ) {
                view_id = parseInt($(view_find).find('a').text().replace(/[^0-9]+/g, ''));
                break;
            }
            if (view_find.attr('level') < min_level) {
                min_level = parseInt(view_find.attr('level'));
            }
        }
        var val = _.detect(obj.att_list, function(val) {return val[0] == "name";});
        var priority = _.detect(self.one_object['arch'], function(val) {return val.view_id == view_id;});
        var arch = _.str.sprintf("<?xml version='1.0'?>\n\t <field name='%s' position='after'> </field>", val[1]);
        var vals = {'model': self.model, 'name': view_name, 'priority': priority.priority + 1, 'type': "form", 'arch': arch,'inherit_id':self.main_view_id};
        this.dataset.create(vals).done(function(id) {
            var arch_to_obj = self.parse_xml(arch,id);
            obj.child_id.push(arch_to_obj[0]);
            self.one_object['parent_child_id'] = self.parent_child_list(self.one_object['main_object'],[]);
            self.one_object['arch'].push({'view_id':id,"arch":arch,'priority': priority.priority + 1});
            self.increase_level(arch_to_obj[0],obj.level+1);
            self.render_inherited_view(selected_row,arch_to_obj[0]);
        });
    },
    render_inherited_view: function(selected_row,obj){
        var self = this,row_id = parseInt((selected_row.attr('id')).split('-')[1]);
        var clone = this.create_clone(selected_row.clone(),obj);
        if (selected_row.find("img[id^='parentimg-']").length == 0) {
            ($(selected_row.find('a').parent()).siblings('td'))
            .append($('<img width="16" height="16"></img>').attr('src', '/web/static/src/img/collapse.gif').
             attr('id','parentimg-'+ row_id).click(function(){
                self.do_parent_img_hide_show(this);
            }));
        }
        self.edit_xml_dialog.$el.
            find("tr[id='viewedit-"+row_id+"']").after(clone.removeClass('ui-selected'));
        _.each(obj.child_id,function(obj){self.render_inherited_view(clone,obj);});
    },
    on_select_img: function(element_img) {
        var self = this;
        var side = $(element_img).closest("tr[id^='viewedit-']");
        this.one_object.clicked_tr_id = parseInt((side.attr('id')).split('-')[1]);
        this.one_object.clicked_tr_level = parseInt(side.attr('level'));
        var img = side.find("img[id='parentimg-" + this.one_object.clicked_tr_id + "']").attr('src');
        var view_id = 0, view_xml_id = 0, view_find = side;
        //for view id finding
        var min_level = this.one_object.clicked_tr_id;
        if (($(side).find('a').text()).search("view_id") != -1) {
            view_id = parseInt(($(view_find).find('a').text()).replace(/[^0-9]+/g, ''));
            view_xml_id = (view_find.attr('id')).split('-')[1];
            this.one_object.clicked_tr_id  += 1;
            this.one_object.clicked_tr_level += 1;
        }else{
            while (1) {
                view_find = view_find.prev();
                if (view_find.length == 0 ||
                    (self.edit_xml_dialog.$el.find(view_find).find('a').text()).search("view_id") != -1
                        && parseInt(view_find.attr('level')) < min_level ) {
                    view_id = parseInt(($(view_find).find('a').text()).replace(/[^0-9]+/g, ''));
                    view_xml_id = parseInt((view_find.attr('id')).split('-')[1]);
                    break;
                }
                if (view_find.attr('level') < min_level) {
                    min_level = parseInt(view_find.attr('level'));
                }
            }
        }
        this.one_object.clicked_tr_view = [view_id, view_xml_id];
        switch (element_img.id) {
            case "side-add":
                self.do_node_add(side);
                break;
            case "side-remove":
                if (confirm(_t("Do you really want to remove this node?"))) {
                    self.do_save_update_arch("remove_node");
                }
                break;
            case "side-edit":
                self.do_node_edit(side);
                break;
            case "side-up":
                self.do_node_up(side, img);
                break;
            case "side-down":
                self.do_node_down(side, img);
                break;
        }
    },
    do_node_add: function(side){
        var self = this,property_to_check = [];
        var tr = self.get_object_by_id(this.one_object.clicked_tr_id, this.one_object['main_object'], [])[0].att_list[0];
        var parent_tr = ($(side).prevAll("tr[level=" + String(this.one_object.clicked_tr_level - 1) + "]"))[0];
        var field_dataset = new instance.web.DataSetSearch(this, this.model, null, null);
        if(_.isUndefined(parent_tr))
            return;
        parent_tr = self.get_object_by_id(parseInt($(parent_tr).attr('id').replace(/[^0-9]+/g, '')), this.one_object['main_object'], [])[0].att_list[0];
        _.each([tr, parent_tr],function(element) {
            var value = _.has(_CHILDREN, element) ? element : _.str.include(html_tag, element)?"html_tag":false;
            property_to_check.push(value);
        });
        field_dataset.call( 'fields_get', []).done(function(result) {
            var fields = _.keys(result);
            fields.push(" "),fields.sort();
            self.on_add_node(property_to_check, fields, self.inject_position(parent_tr,tr));
        });
    },
    inject_position : function(parent_tag,current_tag){
        if(parent_tag == "view")
            return ['Inside'];
        if(current_tag == "field")
            return ['After','Before'];
        return ['After','Before','Inside'];
    },
    do_node_edit: function(side) {
        var self = this;
        var result = self.get_object_by_id(this.one_object.clicked_tr_id, this.one_object['main_object'], []);
        if (result.length && result[0] && result[0].att_list) {
            var properties = _PROPERTIES[result[0].att_list[0]];
            self.on_edit_node(properties);
        }
    },
    do_node_down: function(cur_tr, img) {
        var self = this, next_tr, last_tr, tr_to_move = [];
        tr_to_move.push(cur_tr);
        if (img) {
            while (1) {
                next_tr = cur_tr.next();
                if ( parseInt(next_tr.attr('level')) <= this.one_object.clicked_tr_level || next_tr.length == 0) {
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
        if ((self.edit_xml_dialog.$el.find(last_tr).find('a').text()).search("view_id") != -1) {
            return false;
        }
        if (last_tr.length != 0 &&  parseInt(last_tr.attr('level')) == this.one_object.clicked_tr_level) {
            var last_tr_id = (last_tr.attr('id')).split('-')[1];
            img = last_tr.find("img[id='parentimg-" + last_tr_id + "']").attr('src');
            if (img) {
                self.edit_xml_dialog.$el.find("img[id='parentimg-" + last_tr_id + "']").
                                                attr('src', '/web/static/src/img/expand.gif');
                while (1) {
                    var next_tr = last_tr.next();
                    if (next_tr.attr('level') <= this.one_object.clicked_tr_level || next_tr.length == 0) break;
                    next_tr.hide();
                    last_tr = next_tr;
                }
            }
            tr_to_move.reverse();
            _.each(tr_to_move, function(rec) {
               $(last_tr).after(rec);
            });
            self.do_save_update_arch("down");
        }
    },
    do_node_up: function(cur_tr, img) {
        var self = this, side = cur_tr, tr_to_move = [];
        tr_to_move.push(side);
        while (1) {
            var prev_tr = cur_tr.prev();
            if (this.one_object.clicked_tr_level >= parseInt(prev_tr.attr('level')) || prev_tr.length == 0) {
               last_tr = prev_tr;
               break;
            }
            cur_tr = prev_tr;
        }
        if (img) {
        self.edit_xml_dialog.$el.find("img[id='parentimg-" + this.one_object.clicked_tr_id + "']").
                attr('src', '/web/static/src/img/expand.gif');
            while (1) {
                next_tr = side.next();
                if (parseInt(next_tr.attr('level')) <= this.one_object.clicked_tr_level || next_tr.length == 0) {
                    break;
                } else {
                    next_tr.hide();
                    tr_to_move.push(next_tr);
                    side = next_tr;
                }
            }
        }
        if (last_tr.length != 0 && parseInt(last_tr.attr('level')) == this.one_object.clicked_tr_level &&
                (self.edit_xml_dialog.$el.find(last_tr).find('a').text()).search("view_id") == -1) {
            _.each(tr_to_move, function(rec) {
                 $(last_tr).before(rec);
            });
            self.do_save_update_arch("up");
        }
    },
    do_save_update_arch: function(move_direct, update_values) {
        var self = this;
        var arch = _.detect(self.one_object['arch'], function(element)
            {return element.view_id == self.one_object.clicked_tr_view[0]});
        var obj = self.get_object_by_id(this.one_object.clicked_tr_view[1],this.one_object['main_object'], []);
        //for finding xpath tag from inherit view
        var xml_arch = QWeb.load_xml(arch.arch);
        if (xml_arch.childNodes[0].tagName == "data") {
            var check_list = _.flatten(obj[0].child_id[0].att_list);
            var children = _.filter(xml_arch.childNodes[0].childNodes, function (child) {
                return child.nodeType == 1;
            });
            var inherited_view = _.detect(children, function(xml_child) {
                var temp_obj = self.create_View_Node(xml_child),
                    insert = _.intersection(_.flatten(temp_obj.att_list),_.uniq(check_list));
                if (insert.length == _.uniq(check_list).length ) {return xml_child;}
            });
            xml_arch = QWeb.load_xml(instance.web.xml_to_str(inherited_view));
        }
        return self.do_save_xml(xml_arch.documentElement, obj[0].child_id[0],obj[0].child_id, move_direct, update_values,arch);
    },
    get_object_by_id: function(id, one_object, result) {
        var self = this;
        if (result.length == 0 ) {
            var check = _.detect(one_object , function(obj) {
                return id == obj.id;
            });
            if (check) {result.push(check);}
            _.each(one_object, function(obj) {
               self.get_object_by_id(id,obj.child_id, result);
            });
        }
        return result;
    },
    create_clone: function(clone, new_node_obj){
        var self = this;
        clone.find('a').text(new_node_obj.name);
        ($(clone.find('a').parent()).siblings('td')).css( "padding-left", 20 * new_node_obj.level);
        clone.attr("id", "viewedit-" + new_node_obj.id);
        clone.attr("level", new_node_obj.level);
        clone.find("img[id^='parentimg-']").remove();
        clone.bind("click",function(){
            self.do_select_row(this.id.split('-')[1]);
        });
        clone.find("img[id^='side-']").click(function() {
            self.on_select_img(this);
        });
        return clone;
    },
    do_save_xml: function(arch1, obj, child_list, move_direct, update_values, arch){
        var self = this, children_list =  $(arch1).children(),list_obj_xml;
        try{list_obj_xml = _.zip(children_list, obj.child_id);}catch(err){return;}
        if (this.one_object.clicked_tr_id) {
            if (obj.id == this.one_object.clicked_tr_id) {
                var parent = false, index = _.indexOf(child_list, obj);
                if (move_direct == "down") {
                    var next = $(arch1).next();
                    $(next).after(arch1);
                    var re_insert_obj = child_list.splice(index, 1);
                    child_list.splice(index+1, 0, re_insert_obj[0]);
                    parent = $(arch1).parents();
                } else if (move_direct == "up") {
                    var prev = $(arch1).prev();
                    $(prev).before(arch1);
                    var re_insert_obj = child_list.splice(index, 1);
                    child_list.splice(index-1, 0, re_insert_obj[0]);
                    parent = $(arch1).parents();
                } else if (move_direct == "update_node") {
                    _.each(update_values, function(val){
                        if (val[1]) $(arch1)[0].setAttribute(val[0], val[1]);
                        else $(arch1)[0].removeAttribute(val[0]);
                    });
                    var new_obj = self.create_View_Node(arch1);
                    new_obj.id = obj.id,new_obj.child_id = obj.child_id;
                    self.edit_xml_dialog.$el.
                        find("tr[id='viewedit-"+this.one_object.clicked_tr_id+"']").
                            find('a').text(new_obj.name);
                    child_list.splice(index, 1, new_obj);
                    parent = $(arch1).parents();
                } else if(move_direct == "add_node") {
                    var tr_click = self.edit_xml_dialog.$el.find("tr[id='viewedit-"+self.one_object.clicked_tr_id+"']"),
                        temp_xml = QWeb.load_xml(update_values[0]),
                        object_xml = self.create_View_Node(temp_xml.childNodes[0]);
                    (update_values[1] == "Inside")? object_xml.level = obj.level + 1:object_xml.level = obj.level;
                    var clone = self.create_clone(tr_click.clone(),object_xml),
                        after_append = _.detect(self.one_object['parent_child_id'],function(ele){
                            return self.one_object.clicked_tr_id == ele.key;
                    });
                    after_append = (after_append)?_.last(after_append.value):self.one_object.clicked_tr_id;
                     switch (update_values[1]) {
                         case "After":
                            self.edit_xml_dialog.$el.
                                find("tr[id='viewedit-"+after_append+"']").after(clone);
                            $(arch1).after($(update_values[0]));
                            child_list.splice(index + 1, 0, object_xml);
                            break;
                        case "Before":
                            tr_click.before(clone);
                            $(arch1).before($(update_values[0]));
                            child_list.splice(index - 1, 0, object_xml);
                            break;
                        case "Inside":
                            if (tr_click.find("img[id^='parentimg-']").length == 0) {
                                ($(tr_click.find('a').parent()).siblings('td'))
                                    .append($('<img width="16" height="16"></img>').attr('src', '/web/static/src/img/collapse.gif').
                                    attr('id','parentimg-'+ self.one_object.clicked_tr_id).click(function(){
                                        self.do_parent_img_hide_show(this);
                                }));
                            }
                            $(arch1).append($(update_values[0]));
                            self.edit_xml_dialog.$el.
                                find("tr[id='viewedit-"+after_append+"']").after(clone);
                            obj.child_id.push(object_xml);
                            break;
                   }
                    self.edit_xml_dialog.$el.
                        find("tr[id='viewedit-" + object_xml.id + "']").removeClass('ui-selected');
                    parent = $(arch1).parents();
                } else if (move_direct == "remove_node") {
                    parent = $(arch1).parents();
                    if (parent.length == 0 || (parent[0].tagName.toLowerCase() == "data")) {
                        self.one_object.clicked_tr_id = self.one_object.clicked_tr_id -1;
                        self.one_object.clicked_tr_level = self.one_object.clicked_tr_level - 1;
                        (parent.length == 0)?parent.push("remove_view"):false;
                    }
                    $(arch1).remove();
                    child_list.splice(index,1);
                    var cur_tr = self.edit_xml_dialog.$el.
                            find("tr[id='viewedit-" + self.one_object.clicked_tr_id + "']");
                    _.each(self.get_list_tr(cur_tr,self.one_object.clicked_tr_level), function(tr_element){
                        tr_element.remove();
                    });
                    cur_tr.remove();
                    var parent_img = _.detect(self.one_object['parent_child_id'],function(element){
                        return _.include(element.value, self.one_object.clicked_tr_id);
                    });
                    if(parent_img.value.length == 1){
                        self.edit_xml_dialog.$el.
                            find("tr[id='viewedit-"+parent_img.key+"']").
                            find("img[id^='parentimg-']").remove();
                    }
                    self.one_object['parent_child_id'] = self.parent_child_list(self.one_object['main_object'],[]);
                }
                var convert_to_utf = (parent.length != 0)? parent[parent.length-1]: arch1;
                if (convert_to_utf != "remove_view") {
                    convert_to_utf = QWeb.tools.xml_node_to_string(convert_to_utf);
                    convert_to_utf = convert_to_utf.replace('xmlns="http://www.w3.org/1999/xhtml"', "");
                    convert_to_utf = '<?xml version="1.0"?>' + convert_to_utf;
                    arch.arch = convert_to_utf;
                    this.dataset.write(this.one_object.clicked_tr_view[0] ,{"arch":convert_to_utf});
                } else {
                    this.dataset.unlink([this.one_object.clicked_tr_view[0]]);
                }
                if(move_direct == "add_node"){
                    self.add_node_dialog.close();
                    self.on_select_img(clone.find("img[id='side-edit']")[0]);
                    self.one_object['parent_child_id'] = self.parent_child_list(self.one_object['main_object'],[]);
                }
            }
            if (obj.level <= this.one_object.clicked_tr_level) {
                _.each(list_obj_xml, function(child_node) {
                    self.do_save_xml(child_node[0], child_node[1], obj.child_id, move_direct, update_values, arch);
                });
            }
        }
    },
    on_expand: function(expand_img){
        var level = parseInt($(expand_img).closest("tr[id^='viewedit-']").attr('level'));
        var cur_tr = $(expand_img).closest("tr[id^='viewedit-']");
        _.each(this.get_list_tr(cur_tr,level), function(tr_element){
            tr_element.hide();
        });
    },
    get_list_tr: function(cur_tr,level){
        tr_list = [];
        while (1) {
            var nxt_tr = cur_tr.next();
            if (parseInt(nxt_tr.attr('level')) > level) {
                cur_tr = nxt_tr;
                tr_list.push(nxt_tr);
            } else return tr_list;
        }
    },
    on_collapse: function(collapse_img) {
        var self = this, id = collapse_img.id.split('-')[1];
        var datas = _.detect(self.one_object['parent_child_id'] , function(res) {
            return res.key == id;
        });
        _.each(datas.value, function (rec) {
            var tr = self.edit_xml_dialog.$el.find("tr[id='viewedit-" + rec + "']");
            tr.find("img[id='parentimg-" + rec + "']").attr('src', '/web/static/src/img/expand.gif');
            tr.show();
        });
    },
    on_edit_node: function(properties){
        var self = this;
        this.edit_node_dialog = new instance.web.Dialog(this,{
            title: _t("Properties"),
            size: 'medium',
            buttons: [
                {text: _t("Update"), click: function () {
                    var warn = false, update_values = [];
                    _.each(self.edit_widget, function(widget) {
                        if (widget.is_invalid) {
                            warn = true;
                            return false;
                        }
                        if (widget.dirty && !widget.is_invalid) {
                            update_values.push([widget.name, widget.get_value()]);
                        }
                    });
                    if (warn) {
                        self.on_valid_create_view(self.edit_widget);
                    } else {
                        self.do_save_update_arch("update_node", update_values);
                        self.edit_node_dialog.close();
                    }
                }},
                {text: _t("Cancel"), click: function () { self.edit_node_dialog.close(); }}
            ]
        }).open();
        var _PROPERTIES_ATTRIBUTES = {
            'name' : {'name':'name', 'string': 'Name', 'type': 'char'},
            'string' : {'name':'string', 'string': 'String', 'type': 'char'},
            'required' : {'name':'required', 'string': 'Required', 'type': 'boolean'},
            'readonly' : {'name':'readonly', 'string': 'Readonly', 'type': 'boolean'},
            'invisible' : {'name':'invisible', 'string': 'Invisible', 'type': 'boolean'},
            'domain' : {'name':'domain', 'string': 'Domain', 'type': 'char'},
            'context' : {'name':'context', 'string': 'Context', 'type': 'char'},
            'limit' : {'name':'limit', 'string': 'Limit', 'type': 'float'},
            'min_rows' : {'name':'min_rows', 'string': 'Minimum rows', 'type': 'float'},
            'date_start' : {'name':'date_start', 'string': 'Start date', 'type': 'char'},
            'date_delay' : {'name':'date_delay', 'string': 'Delay date', 'type': 'char'},
            'day_length' : {'name':'day_length', 'string': 'Day length', 'type': 'char'},
            'mode' : {'name':'mode', 'string': 'Mode', 'type': 'char'},
            'align' : {'name':'align', 'string': 'Alignment ', 'type': 'selection', 'selection': [['', ''], ['0.0', 'Left'], ['0.5', 'Center'], ['1.0', 'Right']]},
            'icon' : {'name':'icon', 'string': 'Icon', 'type': 'selection', 'selection': _ICONS},
            'type' : {'name':'type', 'string': 'Type', 'type': 'selection', 'selection': [['', ''], ['action', 'Action'], ['object', 'Object'], ['workflow', 'Workflow'], ['server_action', 'Server Action']]},
            'special' : {'name':'special', 'string': 'Special', 'type': 'selection', 'selection': [['',''],['save', 'Save Button'], ['cancel', 'Cancel Button'], ['open', 'Open Button']]},
            'target' : {'name':'target', 'string': 'Target', 'type': 'selection', 'selection': [['', ''], ['new', 'New Window']]},
            'confirm' : {'name':'confirm', 'string': 'Confirm', 'type': 'char'},
            'style' : {'name':'style', 'string': 'Style', 'type': 'selection', 'selection':[["",""],["1", "1"],["1-1", "1-1"],["1-2", "1-2"],["2-1", "2-1"],["1-1-1", "1-1-1"]]},
            'filename' : {'name':'filename', 'string': 'File Name', 'type': 'char'},
            'width' : {'name':'width', 'string': 'Width', 'type': 'float'},
            'height' : {'name':'height', 'string': 'Height', 'type': 'float'},
            'attrs' : {'name':'attrs', 'string': 'Attrs', 'type': 'char'},
            'col' : {'name':'col', 'string': 'col', 'type': 'float'},
            'link' : {'name':'link', 'string': 'Link', 'type': 'char'},
            'position' : {'name':'position', 'string': 'Position', 'type': 'selection', 'selection': [['',''],['after', 'After'],['before', 'Before'],['inside', 'Inside'],['replace', 'Replace']]},
            'states' : {'name':'states', 'string': 'states', 'type': 'char'},
            'eval' : {'name':'eval', 'string': 'Eval', 'type': 'char'},
            'ref' : {'name':'ref', 'string': 'Ref', 'type': 'char'},
            'on_change' : {'name':'on_change', 'string': 'On change', 'type': 'char'},
            'nolabel' : {'name':'nolabel', 'string': 'No label', 'type': 'boolean'},
            'completion' : {'name':'completion', 'string': 'Completion', 'type': 'boolean'},
            'colspan' : {'name':'colspan', 'string': 'Colspan', 'type': 'float'},
            'widget' : {'name':'widget', 'string': 'widget', 'type': 'selection'},
            'colors' : {'name':'colors', 'string': 'Colors', 'type': 'char'},
            'editable' : {'name':'editable', 'string': 'Editable', 'type': 'selection', 'selection': [["",""],["top","Top"],["bottom", "Bottom"]]},
            'groups' : {'name':'groups', 'string': 'Groups', 'type': 'selection_multi'},
            'fonts' : {'name':'fonts', 'string': 'fonts', 'type': 'char'},
        };
        var arch_val = self.get_object_by_id(this.one_object.clicked_tr_id,this.one_object['main_object'], []);
        this.edit_node_dialog.$el.append('<table id="rec_table"  style="width:400px" class="oe_form"></table>');
        this.edit_widget = [];
        self.ready  = $.when(self.on_groups(properties)).done(function () {
            _PROPERTIES_ATTRIBUTES['groups']['selection'] = self.groups;
            var values = _.keys( instance.web.form.widgets.map);
            values.push('');
            values.sort();
            _PROPERTIES_ATTRIBUTES['widget']['selection'] = values;
            var widgets = _.filter(_PROPERTIES_ATTRIBUTES, function (property) { return _.include(properties, property.name)});
            _.each(widgets, function(widget) {
                var type_widget =  new (self.property.get_any([widget.type])) (self.edit_node_dialog, widget);
                var value = _.detect(arch_val[0]['att_list'],function(res) {
                    return res instanceof Array? _.include(res, widget.name): false;
                });

                value = value instanceof Array ? value[1] : value;
                self.edit_node_dialog.$el.find('table[id=rec_table]').append('<tr><td align="right">' + widget.string + ':</td>' + type_widget.render() + '</tr>');
                type_widget.start();
                type_widget.set_value(value);
                self.edit_widget.push(type_widget);
            });
        });
    },
     //for getting groups
    on_groups: function(properties){
        var self = this,
        def = $.Deferred();
        if (!_.include(properties, 'groups')) {
            self.groups = false;
            def.resolve();
        }
        var group_ids = [], group_names = {}, groups = [];
        var res_groups = new instance.web.DataSetSearch(this,'res.groups', null, null),
            model_data = new instance.web.DataSetSearch(self,'ir.model.data', null, null);
            res_groups.read_slice([], {}).done(function (res_grp) {
                _.each(res_grp, function (res) {
                    var key = res.id;
                    group_names[key]=res.full_name;
                    group_ids.push(res.id);
                });
                model_data.read_slice([], {domain: [
                    ['res_id', 'in', group_ids],
                    ['model', '=', 'res.groups']
                ]}).done(function (model_grp) {
                    _.each(model_grp, function (res_group) {
                        groups.push([res_group.module + "." + res_group.name, group_names[res_group.res_id]]);
                    });
                    self.groups = groups;
                    def.resolve();
                });
            });
        return def.promise();
    },
    on_add_node: function(properties, fields, position){
        var self = this;
        var  render_list = [{'name': 'node_type','selection': _.keys(_CHILDREN).sort(), 'value': 'field', 'string': 'Node Type','type': 'selection'},
                            {'name': 'field_value','selection': fields, 'value': false, 'string': '','type': 'selection'},
                            {'name': 'position','selection': position, 'value': false, 'string': 'Position','type': 'selection'}];
        this.add_widget = [];
        this.add_node_dialog = new instance.web.Dialog(this,{
            title: _t("Properties"),
            size: 'medium',
            buttons: [
                {text: _t("Update"), click: function() {
                    var check_add_node = true, values = {};
                    _.each(self.add_widget, function(widget) {
                        values[widget.name] = widget.get_value() || false;
                    });
                   (values.position == "Inside")?
                    check_add_node =(_.include(_CHILDREN[properties[0]],values.node_type))?true:false:
                    check_add_node =(_.include(_CHILDREN[properties[1]],values.node_type))?true:false;
                    if(values.node_type == "field" &&  check_add_node )
                        {check_add_node = (values.field_value != " ")?true:false;
                    }
                    if(check_add_node){
                        var tag = (values.node_type == "field")?
                        _.str.sprintf("<%s name='%s'> </%s>",values.node_type,values.field_value,values.node_type):
                        _.str.sprintf("<%s> </%s>",values.node_type,values.node_type);
                        self.do_save_update_arch("add_node", [tag, values.position]);
                    } else {
                        alert("Can't Update View");
                    }
                }},
                {text: _t("Cancel"), click: function() { self.add_node_dialog.close(); }}
            ]
        }).open();
        this.add_node_dialog.$el.append('<table id="rec_table"  style="width:420px" class="oe_form"><tbody><tr></tbody></table>');
        var table_selector = self.add_node_dialog.$el.find('table[id=rec_table] tbody');
        _.each(render_list, function(node) {
            type_widget = new (self.property.get_any([node.type])) (self.add_node_dialog, node);
            if (node.name == "position") {
                table_selector.append('</tr><tr><td align="right" width="100px">' + node.string + '</td>' + type_widget.render() + '</tr>');
            } else {
                table_selector.append('<td align="right">' + node.string + '</td>' + type_widget.render() );
                if (node.name == "field_value") {
                    table_selector.append('<td id="new_field" align="right"  width="100px"> <button>' + _.str.escapeHTML(_t("New Field")) + '</button></td>');
                }
            }
            type_widget.start();
            type_widget.set_value(node.value);
            self.add_widget.push(type_widget);
        });
        table_selector.find("td[id^='']").attr("width","100px");
        self.add_node_dialog.$el.find('#new_field').click(function() {
            model_data = new instance.web.DataSetSearch(self,'ir.model', null, null);
            model_data.read_slice([], {domain: [['model','=', self.model]]}).done(function(result) {
                self.render_new_field(result[0]);
            });
        });
    },
    render_new_field :function( result ) {
        var self = this;
        var action = {
            context: {'default_model_id': result.id, 'manual': true, 'module' : result.model},
            res_model: "ir.model.fields",
            views: [[false, 'form']],
            type: 'ir.actions.act_window',
            target: "new",
            flags: {
                action_buttons: true
            }
        };
        var action_manager = new instance.web.ActionManager(self);
        $.when(action_manager.do_action(action)).done(function() {
            var controller = action_manager.dialog_widget.views['form'].controller;
            controller.on("on_button_cancel", self, function(){
                action_manager.destroy();
            });
            controller.on("save", self, function(){
                action_manager.destroy();
                var value =controller.fields.name.get('value');
                self.add_node_dialog.$el.find('select[id=field_value]').append($("<option selected></option>").attr("value",value).text(value));
                    _.detect(self.add_widget,function(widget){
                        widget.name == "field_value"? widget.selection.push(value): false;
                    });
            });
        });
    }
});
instance.web_view_editor.ViewEditor.Field = instance.web.Class.extend({
    init: function(view, widget) {
        this.$el = view.$el;
        this.dirty = false;
        this.name = widget.name;
        this.selection =  widget.selection || [];
        this.required = widget.required || false;
        this.string = widget.string || "";
        this.type = widget.type;
        this.is_invalid = false;
    },
    start: function () {
        this.update_dom();
    },
    update_dom: function() {
        this.$el.find("td[id=" + this.name + "]").toggleClass('invalid', this.is_invalid);
        this.$el.find("td[id=" + this.name + "]").toggleClass('required', this.required);
    },
    on_ui_change: function() {
        this.validate();
        this.dirty = true;
        this.update_dom();
    },
    validate: function() {
        this.is_invalid = false;
        try {
            var value = instance.web.parse_value(this.get_value(), this, '');
            this.is_invalid = this.required && value === '';
        } catch(e) {
            this.is_invalid = true;
        }
    },
    render: function() {
        return _.str.sprintf("<td id = %s>%s</td>", this.name, QWeb.render(this.template, {widget: this}))
    }
});
instance.web_view_editor.ViewEditor.FieldBoolean = instance.web_view_editor.ViewEditor.Field.extend({
    template : "vieweditor_boolean",
    start: function() {
        var self = this;
        this._super();
        this.$el.find("input[id="+ self.name+"]").change(function() {
            self.on_ui_change();
        });
    },
    set_value: function(value) {
        if (value) {
            this.$el.find("input[id=" + this.name+ "]").attr('checked', true);
        }
    },
    get_value: function() {
        return  this.$el.find("input[id=" + this.name + "]").is(':checked')? "1" : null;
    }
});
instance.web_view_editor.ViewEditor.FieldChar = instance.web_view_editor.ViewEditor.Field.extend({
    template : "vieweditor_char",
    start: function () {
        var self = this;
        this._super();
        this.$el.find("input[id="+ this.name+"]").css('width','100%').change(function() {
            self.on_ui_change();
        });
    },
    set_value: function(value) {
        this.$el.find("input[id=" + this.name + "]").val(value);
    },
    get_value: function() {
        return this.$el.find("input[id=" + this.name + "]").val();
    }
});
instance.web_view_editor.ViewEditor.FieldSelect = instance.web_view_editor.ViewEditor.Field.extend({
    template : "vieweditor_selection",
    start: function () {
        var self = this;
        this._super();
        this.$el.find("select[id=" + this.name + "]").css('width', '100%').change(function() {
            self.on_ui_change();
            if (self.name == "node_type") {
                if (self.get_value() == "field") {
                    self.$el.find('#new_field').show();
                    self.$el.find("select[id=field_value]").show();
                } else {
                    self.$el.find('#new_field').hide();
                    self.$el.find("select[id=field_value]").hide();
                }
            }
        });
    },
    set_value: function(value) {
        var index = 0;
        value = value === null? false: value;
        for (var i = 0, ii = this.selection.length; i < ii; i++) {
            if ((this.selection[i] instanceof Array && this.selection[i][0] === value) || this.selection[i] === value) index = i;
        }
        this.$el.find("select[id=" + this.name + "]")[0].selectedIndex = index;
    },
    get_value: function() {
        return this.$el.find("select[id=" + this.name + "]").val();
    }
});
instance.web_view_editor.ViewEditor.FieldSelectMulti = instance.web_view_editor.ViewEditor.FieldSelect.extend({
    start: function () {
        this._super();
        this.$el.find("select[id=" + this.name + "]").css('height', '100px').attr("multiple", true);
    },
    set_value: function(value) {
        var self = this;
        self.$el.find("#groups option").attr("selected",false);
        if (!value) return false;
        _.each(this.selection, function(item) {
            if (_.include(value.split(','), item[0])) {
                self.$el.find("select[id="+self.name+"] option[value='" + item[0] +"']").attr("selected",1)
            }
        });
    }
});
instance.web_view_editor.ViewEditor.FieldFloat = instance.web_view_editor.ViewEditor.FieldChar.extend({
});

var _PROPERTIES = {
    'field' : ['name', 'string', 'required', 'readonly','invisible', 'domain', 'context', 'nolabel', 'completion',
               'colspan', 'widget', 'eval', 'ref', 'on_change', 'attrs', 'groups'],
    'form' : ['string', 'col', 'link'],
    'notebook' : ['colspan', 'position', 'groups'],
    'page' : ['string', 'states', 'attrs', 'groups'],
    'group' : ['string', 'col', 'colspan','invisible', 'states', 'attrs', 'groups'],
    'image' : ['filename', 'width', 'height', 'groups'],
    'separator' : ['string', 'colspan', 'groups'],
    'label': ['string', 'align', 'colspan', 'groups'],
    'button': ['name', 'string', 'icon', 'type', 'states', 'readonly', 'special', 'target', 'confirm', 'context', 'attrs', 'colspan', 'groups'],
    'newline' : [],
    'board': ['style'],
    'column' : [],
    'action' : ['name', 'string', 'colspan', 'groups'],
    'tree' : ['string', 'colors', 'editable', 'link', 'limit', 'min_rows', 'fonts'],
    'graph' : ['string', 'type'],
    'calendar' : ['string', 'date_start', 'date_stop', 'date_delay', 'day_length', 'color', 'mode']
};
var _CHILDREN = {
    'form': ['notebook', 'group', 'field', 'label', 'button','board', 'newline', 'separator'],
    'tree': ['field'],
    'graph': ['field'],
    'calendar': ['field'],
    'notebook': ['page'],
    'page': ['notebook', 'group', 'field', 'label', 'button', 'newline', 'separator'],
    'group': ['field', 'label', 'button', 'separator', 'newline','group'],
    'board': ['column'],
    'action': [],
    'field': ['form', 'tree', 'graph','field'],
    'label': [],
    'button' : [],
    'newline': [],
    'separator': [],
    'sheet' :['group','field','notebook','label','separator','div','page'],
    'kanban' : ['field'],
    'html_tag':['notebook', 'group', 'field', 'label', 'button','board', 'newline', 'separator']
//e.g.:xyz 'td' : ['field']
};
// Generic html_tag list and can be added html tag in future. It's support above _CHILDREN dict's *html_tag* by default.
// For specific child node one has to define tag above and specify children tag in list. Like above xyz example.
var html_tag = ['div','h1','h2','h3','h4','h5','h6','td','tr'];

var _ICONS = ['','STOCK_ABOUT', 'STOCK_ADD', 'STOCK_APPLY', 'STOCK_BOLD',
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
instance.web_view_editor.ViewEditor.property_widget = new instance.web.Registry({
    'boolean' : 'instance.web_view_editor.ViewEditor.FieldBoolean',
    'selection_multi' : 'instance.web_view_editor.ViewEditor.FieldSelectMulti',
    'selection' : 'instance.web_view_editor.ViewEditor.FieldSelect',
    'char' : 'instance.web_view_editor.ViewEditor.FieldChar',
    'float' : 'instance.web_view_editor.ViewEditor.FieldFloat'
});
};
