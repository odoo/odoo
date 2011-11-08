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
            domain: [["model", "=", this.dataset.model]],
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
                radio: true
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
                    self.xml_element_id = 0;
                    self.get_arch();
                },
                "Close": function(){
                    self.view_edit_dialog.close();
                }
            },
        }).start().open();
        var action_manager = new openerp.web.ActionManager(this);
        action_manager.appendTo(this.view_edit_dialog);
        $.when(action_manager.do_action(action)).then(function() {
            var viewmanager = action_manager.inner_viewmanager,
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
    convert_tag_to_obj: function(xml, level) {
        var obj = {
            'child_id': [],
            'id': this.xml_element_id++,
            'level': level + 1,
            'att_list': [],
            'name': ''
        };
        var tag = xml.tagName.toLowerCase();
        obj.att_list.push(tag);
        obj.name = "<" + tag;
        $(xml).each(function() {
            _.each(this.attributes, function(attrs) {
                if (tag != 'button' && tag != 'field') {
                    if (attrs.nodeName == "string" ) {
                        obj.name += ' ' + attrs.nodeName + '=' + '"' + attrs.nodeValue + '"';
                    }
                } else {
                    if (attrs.nodeName == "name") {
                        obj.name += ' ' + attrs.nodeName + '=' + '"' + attrs.nodeValue + '"';
                    }
                }
                obj.att_list.push([attrs.nodeName, attrs.nodeValue]);
            });
            obj.name += ">";
        });
        return obj;
    },
    append_child_object: function(val, parent_list, child_obj_list) {
        var self = this;
        if (val.child_id.length != 0) {
            _.each(val.child_id, function(val) {
                (val.id == parent_list[0])?
                    self.append_child_object( val, parent_list.slice(1), child_obj_list) : false;
            });
        } else { val.child_id = child_obj_list; }
    },
    convert_arch_to_obj: function(xml, parent_list, parent_id, main_object){
        var self = this;
        var child_obj_list = [];
        var children_list = $(xml).children();
        var parents = $(children_list[0]).parents().get();
        _.each(children_list, function(child_node) {
            child_obj_list.push(self.convert_tag_to_obj(child_node, parents.length));
        });
        if (children_list.length != 0) {
            if(parents.length <= parent_list.length) { parent_list.splice(parents.length - 1);}
            parent_list.push(parent_id);
            self.append_child_object(main_object[0], parent_list.slice(1), child_obj_list);
        }
        for (var i = 0; i < children_list.length; i++) {
            self.convert_arch_to_obj(children_list[i], parent_list, child_obj_list[i].id, main_object);
        }
        return main_object;
    },
    parse_xml: function(arch, view_id) {
        var root = $(arch).filter(":first")[0];
        var tag = root.tagName.toLowerCase();
        var view_obj = {
            'child_id': [],
            'id': this.xml_element_id++,
            'level': 0,
            'att_list': [],
            'name': _.sprintf("<view view_id='%d'>", view_id),
        };
        var root_object = this.convert_tag_to_obj(root, 0);
        view_obj.child_id = this.convert_arch_to_obj(arch, [], this.xml_element_id, [root_object], []);
        return [view_obj];
    },
    get_arch: function() {
        var self = this;
        var view_arch_list = [];
        var view_dataset = new openerp.web.DataSet(this, 'ir.ui.view');
        view_dataset.read_ids([parseInt(self.main_view_id)], ['arch', 'type'], function(arch) {
            var arch_object = self.parse_xml(arch[0].arch, self.main_view_id);
            self.main_view_type = arch[0].type
            view_arch_list.push({"view_id": self.main_view_id, "arch": arch[0].arch});
            dataset = new openerp.web.DataSetSearch(self, 'ir.ui.view', null, null);
            dataset.read_slice([], {domain: [['inherit_id','=', parseInt(self.main_view_id)]]}, function(result) {
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
        var root = $(result.arch).filter('*');
        var xml_list = [];
        root[0].tagName.toLowerCase() == "data"? xml_list = $(root[0]).children() : xml_list.push(root[0]);
        _.each(xml_list, function(xml) {
            var expr_to_list = [];
            var xpath_arch_object = self.parse_xml(xml,result.id);
            if (xml.tagName.toLowerCase() == "xpath" ) {
                var part_expr = _.without($(xml).attr('expr').split("/"), "");
                _.each(part_expr, function(part) {
                    expr_to_list.push(_.without($.trim(part.replace(/[^a-zA-Z 0-9 _]+/g,'!')).split("!"), ""));
                });
            } else {
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
            }
            else {
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
        this.edit_xml_dialog.$element.html(QWeb.render('view_editor', {'data': one_object['main_object']}));
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
            while (1) {
                view_find = view_find.prev();
                if((self.edit_xml_dialog.$element.find(view_find).find('a').text()).search("view_id") != -1
                        && parseInt(view_find.attr('level')) < clicked_tr_level) {
                    view_id = parseInt(($(view_find).find('a').text()).replace(/[^0-9]+/g, ''));
                    view_xml_id = (view_find.attr('id')).split('-')[1];
                    break;
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
                }
                else {
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
        if (($(arch.arch).filter("data")).length != 0 && view_xml_id != 0) {
            var check_list = _.flatten(obj[0].child_id[0].att_list);
            arch.arch = _.detect($(arch.arch).children(), function(xml_child){
                var temp_obj = self.convert_tag_to_obj(xml_child);
                var main_list = _.flatten(temp_obj.att_list);
                var insert = _.intersection(main_list,_.uniq(check_list));
                if (insert.length == check_list.length ) {return xml_child;}
            });
        }
        return self.save_arch(arch.arch, obj[0].child_id[0], parseInt(clicked_tr_id), [], parseInt(clicked_tr_level),
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
    save_arch: function(arch1, obj, id, child_list, level, view_id, arch, move_direct, update_values){
        var self = this;
        var children_list =  $(arch1).children();
        var list_obj_xml = _.zip(children_list,obj.child_id);
        if (id) {
            if (obj.id == id) {
                var id;
                var parent = $(arch1).parents();
                var index = _.indexOf(child_list, obj);
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
                        $(arch1).attr(val[0],val[1]);
                    });
                    var new_obj = self.convert_tag_to_obj(arch1, obj.level - 1);
                    new_obj.id = obj.id;
                    new_obj.child_id = obj.child_id;
                    self.edit_xml_dialog.$element.find("tr[id='viewedit-"+id+"']").find('a').text(new_obj.name);
                    child_list.splice(index, 1, new_obj);
                }
                parent = parent[parent.length - 1];
                var convert_to_utf = self.xml2Str(parent);
                if (convert_to_utf) {
                    convert_to_utf = convert_to_utf.replace('xmlns="http://www.w3.org/1999/xhtml"', "");
                    convert_to_utf = '<?xml version="1.0"?>' + convert_to_utf;
                    arch.arch = convert_to_utf;
                    dataset = new openerp.web.DataSet(this, 'ir.ui.view');
                        dataset.write(parseInt(view_id),{"arch": convert_to_utf}, function(result) {
                    });
                }
            }
            if (obj.level <= level) {
                _.each(list_obj_xml, function(child_node) {
                    self.save_arch(child_node[0], child_node[1], id, obj.child_id, level, view_id, arch, move_direct, update_values);
                });
            }
        }
    },
    xml2Str: function(xmlNode) {
       try {
          return (new XMLSerializer()).serializeToString(xmlNode);
      }
      catch (exception) {
         try {
            return xmlNode.xml;
         }
         catch (exception) {
            return false;
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
            width: 650,
            height: 200,
            buttons: {
                    "Update": function(){
                        var update_values = [];
                        _.each(self.edit_widget,function(widget){
                            var value = widget.get_value();
                            if (value) {
                                update_values.push(value);
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
        var widget = ['readonly','required','nolabel','completion','widget','groups','position','icon','align','special','type','target'];
        var arch_val = self.get_object_by_id(clicked_tr_id,obj['main_object'],[]);
        this.edit_node_dialog.$element.append('<table id="rec_table" class="oe_forms"></table>');
        this.edit_widget = [];
        _.each(properties,function(record){
            var id = record,
            type_widget;
            self.ready  = $.when(self.on_groups(id)).then(function () {
                if (_.include(widget,id)){
                    type_widget =  new (self.property.get_any(['undefined' , id, arch_val[0]['att_list'][0]])) (self.edit_node_dialog, arch_val, id);
                    self.edit_widget.push(type_widget);
                }else{
                    type_widget = new openerp.web.ViewEditor.FieldChar (self.edit_node_dialog,arch_val, id);
                    self.edit_widget.push(type_widget);
                }
                self.edit_node_dialog.$element.find('table[id=rec_table]').append('<tr id="'+id+'"><td align="right">'+id+':</td><td>'+type_widget.render()+'</td></tr>');
                (id=='groups')?type_widget.set_value(self.groups):type_widget.set_value();
                type_widget.start();
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
        this.$element = view.$element;
        this.node = node;
        this.dirty = false;
        this.name = id;
    },
    on_ui_change: function() {
        this.dirty = true;
    },
    render: function () {
        return QWeb.render(this.template, {widget: this});
    },
});
openerp.web.ViewEditor.FieldBoolean = openerp.web.ViewEditor.Field.extend({
    init: function(view, node, id) {
        this._super(view, node, id);
        this.template = "view_boolean";
    },
    start: function () {
        var self = this;
        this.$element.find("tr[id="+ self.name+"] input").change(function() {
            self.on_ui_change();
        });
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
        if (!this.dirty) {
            return false;
        }
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
    start: function () {
        var self = this;
        this.$element.find("tr[id="+ this.name+"] input").change(function() {
            self.on_ui_change();
        });
    },
    set_value: function() {
        var self = this;
        var view_val = _.detect(this.node[0]['att_list'],function(res) {
            return _.include(res, self.name);
        });
        view_val ? this.$element.find("tr[id="+self.name +"] input").val(view_val[1]): this.$element.find("tr[id="+self.name+"] input").val();
    },
    get_value: function(){
        if (!this.dirty) {
            return false;
        }
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
    start: function () {
        var self = this;
        this.$element.find("tr[id="+ this.name+"] select").change(function() {
            self.on_ui_change();
        });
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
        if (!this.dirty) {
            return false;
        }
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