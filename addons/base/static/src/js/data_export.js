openerp.base.data_export = function(openerp) {
openerp.base.DataExport = openerp.base.Dialog.extend({
    template: 'ExportTreeView',
    dialog_title: 'Export Data',
    init: function(parent, dataset) {
        this._super(parent);
        this.dataset = dataset;
        this.exports = new openerp.base.DataSetSearch(
            this, 'ir.exports', this.dataset.get_context());
    },
    start: function() {
        var self = this;
        this._super.apply(this, arguments);
        this.open({
            modal: true,
            width: '55%',
            height: 'auto',
            position: 'top',
            buttons : {
                "Close" : function() {
                    self.close();
                  },
                "Export To File" : function() {
                    self.on_click_export_data();
                  }
               },
            close: function(event, ui){ self.close();}
        });
        self.on_show_exists_export_list();
        self.$element.removeClass('ui-dialog-content ui-widget-content');
        self.$element.find('#add_field').click(function() {
            if ($('#field-tree-structure tr.ui-selected')) {
                var fld = self.$element.find('#field-tree-structure tr.ui-selected').find('a');
                for (var i = 0; i < fld.length; i++) {
                    var id = $(fld[i]).attr('id').split('-')[1];
                    var string = $(fld[i]).attr('string');
                    self.add_field(id, string);
                }
                self.$element.find('#field-tree-structure tr').removeClass('ui-selected');
            }
        });
        self.$element.find('#remove_field').click(function() {
            self.$element.find('#fields_list option:selected').remove();
        });
        self.$element.find('#remove_all_field').click(function() {
            self.$element.find('#fields_list').empty();
        });
        self.$element.find('#export_new_list').click(function() {
            self.on_show_save_list();
        });
        var import_comp = self.$element.find('#import_compat option:selected').val(),
            params = {
                import_compat: parseInt(import_comp, 10)
            };
        self.rpc('/base/export/get_fields', { model: self.dataset.model, params: params }, self.on_show_data);

        self.$element.find('#import_compat').change(function() {
            self.$element.find('#fields_list option').remove();
            self.$element.find('#field-tree-structure').remove();
            var import_comp = self.$element.find("#import_compat option:selected").val();
            if (import_comp) {
                var params = {
                    import_compat: parseInt(import_comp, 10)
                };
                self.rpc("/base/export/get_fields", { model: self.dataset.model, params: params}, self.on_show_data);
            }
        });
    },
    on_show_exists_export_list: function() {
        var self = this;
        if (self.$element.find('#saved_export_list').is(':hidden')) {
            self.$element.find('#ExistsExportList').show();
            return;
        }
        this.exports.read_slice(['name'], {
            domain: [['resource', '=', this.dataset.model]]
        }, function (export_list) {
            if (!export_list.length) {
                return;
            }
            self.$element.find('#ExistsExportList').append(QWeb.render('Exists.ExportList', {'existing_exports': export_list}));
            self.$element.find('#saved_export_list').change(function() {
                self.$element.find('#fields_list option').remove();
                var export_id = self.$element.find('#saved_export_list option:selected').val();
                if (export_id) {
                    self.rpc('/base/export/namelist', {'model': self.dataset.model, export_id: parseInt(export_id)}, self.do_load_export_field);
                }
            });
            self.$element.find('#delete_export_list').click(function() {
                var select_exp = self.$element.find('#saved_export_list option:selected');
                if (select_exp.val()) {
                    self.exports.unlink([parseInt(select_exp.val(), 10)]);
                    select_exp.remove();
                    if (self.$element.find('#saved_export_list option').length <= 1) {
                        self.$element.find('#ExistsExportList').hide();
                    }
                }
            });
        });
    },
    do_load_export_field: function(field_list) {
        var export_node = this.$element.find("#fields_list");
        for (var key in field_list) {
            export_node.append(new Option(field_list[key], key));
        }
    },
    on_show_save_list: function() {
        var self = this;
        var current_node = self.$element.find("#savenewlist");
        if (!(current_node.find("label")).length) {
            current_node.append(QWeb.render('ExportNewList'));
            current_node.find("#add_export_list").click(function() {
                var value = current_node.find("#savelist_name").val();
                if (value) {
                    self.do_save_export_list(value);
                } else {
                    alert("Pleae Enter Save Field List Name");
                }
            });
        } else {
            if (current_node.is(':hidden')) {
                current_node.show();
                current_node.find("#savelist_name").val("");
            } else {
               current_node.hide();
            }
        }
    },
    do_save_export_list: function(value) {
        var self = this;
        var fields = self.get_fields();
        if (!fields.length) {
            return;
        }
        this.exports.create({
            name: value,
            resource: this.dataset.model,
            export_fields: _(fields).map(function (field) {
                return [0, 0, {name: field}];
            })
        }, function (export_list_id) {
            if (!export_list_id) {
                return;
            }
            if (self.$element.find("#saved_export_list").length > 0) {
                self.$element.find("#saved_export_list").append(
                        new Option(value, export_list_id));
            } else {
                self.on_show_exists_export_list();
            }
            if (self.$element.find("#saved_export_list").is(":hidden")) {
                self.on_show_exists_export_list();
            }
        });
        this.on_show_save_list();
        this.$element.find("#fields_list option").remove();
    },
    on_click: function(id, result) {
        var self = this;
        self.field_id = id.split("-")[1];
        var is_loaded = 0;
        _.each(result, function(record) {
            if (record['id'] == self.field_id && (record['children']).length >= 1) {
                var model = record['params']['model'],
                    prefix = record['params']['prefix'],
                    name = record['params']['name'];
                $(record['children']).each(function(e, childid) {
                    if (self.$element.find("tr[id='treerow-" + childid + "']").length > 0) {
                        if (self.$element.find("tr[id='treerow-" + childid + "']").is(':hidden')) {
                            is_loaded = -1;
                        } else {
                            is_loaded++;
                        }
                    }
                });
                if (is_loaded == 0) {
                    if (self.$element.find("tr[id='treerow-" + self.field_id +"']").find('img').attr('src') === '/base/static/src/img/expand.gif') {
                        if (model) {
                            var import_comp = self.$element.find("#import_compat option:selected").val();
                            var params = {
                                import_compat: parseInt(import_comp),
                                parent_field_type : record['field_type']
                            };
                            self.rpc("/base/export/get_fields", {
                                model: model,
                                prefix: prefix,
                                name: name,
                                field_parent : self.field_id,
                                params: params
                            }, function(results) {
                                self.on_show_data(results);
                            });
                        }
                    }
                } else if (is_loaded > 0) {
                    self.showcontent(self.field_id, true);
                } else {
                    self.showcontent(self.field_id, false);
                }
            }
        });
    },
    on_show_data: function(result) {
        var self = this;
        var imp_cmpt = parseInt(self.$element.find("#import_compat option:selected").val());
        var current_tr = self.$element.find("tr[id='treerow-" + self.field_id + "']");
        if (current_tr.length >= 1) {
            current_tr.find('img').attr('src','/base/static/src/img/collapse.gif');
            current_tr.after(QWeb.render('ExportTreeView-Secondary.children', {'fields': result}));
        } else {
            self.$element.find('#left_field_panel').append(QWeb.render('ExportTreeView-Secondary', {'fields': result}));
        }
        _.each(result, function(record) {
            if ((record.field_type == "one2many") && imp_cmpt) {
                var o2m_fld = self.$element.find("tr[id='treerow-" + record.id + "']").find('#tree-column');
                o2m_fld.addClass("oe_export_readonlyfield");
            }
            if (record.required) {
                var required_fld = self.$element.find("tr[id='treerow-" + record.id + "']").find('#tree-column');
                required_fld.addClass("oe_export_requiredfield");
            }
            self.$element.find("img[id='parentimg-" + record.id +"']").click(function() {
                self.on_click(this.id, result);
            });

            self.$element.find("tr[id='treerow-" + record.id + "']").click(function(e) {
                if (e.shiftKey) {
                    var frst_click, scnd_click = '';
                    if (self.row_index == 0) {
                        self.row_index = this.rowIndex;
                        frst_click = self.$element.find("tr[id^='treerow-']")[self.row_index-1];
                        $(frst_click).addClass("ui-selected");
                    } else {
                        if (this.rowIndex >=self.row_index) {
                            for (var i = (self.row_index-1); i < this.rowIndex; i++) {
                                scnd_click = self.$element.find("tr[id^='treerow-']")[i];
                                if (!$(scnd_click).find('#tree-column').hasClass("oe_export_readonlyfield")) {
                                    $(scnd_click).addClass("ui-selected");
                                }
                            }
                        } else {
                            for (var i = (self.row_index-1); i >= (this.rowIndex-1); i--) {
                                scnd_click = self.$element.find("tr[id^='treerow-']")[i];
                                if (!$(scnd_click).find('#tree-column').hasClass("oe_export_readonlyfield")) {
                                    $(scnd_click).addClass("ui-selected");
                                }
                            }
                        }
                    }
                }
                self.row_index = this.rowIndex;

                self.$element.find("tr[id='treerow-" + record.id + "']").keyup(function() {
                    self.row_index = 0;
                });
                var o2m_selection = self.$element.find("tr[id='treerow-" + record.id + "']").find('#tree-column');
                if ($(o2m_selection).hasClass("oe_export_readonlyfield")) {
                    return false;
                }
                if (e.ctrlKey) {
                    if ($(this).hasClass('ui-selected')) {
                        $(this).removeClass('ui-selected').find('a').blur();
                    } else {
                        $(this).addClass('ui-selected').find('a').focus();
                    }
                } else if (!e.shiftKey) {
                    self.$element.find("tr.ui-selected")
                            .removeClass("ui-selected").find('a').blur();
                    $(this).addClass("ui-selected").find('a').focus();
                }
                return false;
            });

            self.$element.find("tr[id='treerow-" + record.id + "']").keydown(function(e) {
                var keyCode = e.keyCode || e.which;
                var arrow = {left: 37, up: 38, right: 39, down: 40 };
                switch (keyCode) {
                    case arrow.left:
                        if ($(this).find('img').attr('src') === '/base/static/src/img/collapse.gif') {
                            self.on_click(this.id, result);
                        }
                        break;
                    case arrow.up:
                        var elem = this;
                        $(elem).removeClass("ui-selected");
                        while (!$(elem).prev().is(":visible")) {
                            elem = $(elem).prev();
                        }
                        if (!$(elem).prev().find('#tree-column').hasClass("oe_export_readonlyfield")) {
                            $(elem).prev().addClass("ui-selected");
                        }
                        $(elem).prev().find('a').focus();
                        break;
                    case arrow.right:
                        if ($(this).find('img').attr('src') == '/base/static/src/img/expand.gif') {
                            self.on_click(this.id, result);
                        }
                        break;
                    case arrow.down:
                        var elem = this;
                        $(elem).removeClass("ui-selected");
                        while(!$(elem).next().is(":visible")) {
                            elem = $(elem).next();
                        }
                        if (!$(elem).next().find('#tree-column').hasClass("oe_export_readonlyfield")) {
                            $(elem).next().addClass("ui-selected");
                        }
                        $(elem).next().find('a').focus();
                        break;
                }
            });
            self.$element.find("tr[id='treerow-" + record.id + "']").dblclick(function() {
                var $o2m_selection = self.$element.find("tr[id^='treerow-" + record.id + "']").find('#tree-column');
                if (!$o2m_selection.hasClass("oe_export_readonlyfield")) {
                    var field_id = $(this).find("a").attr("id");
                    if (field_id) {
                       self.add_field(field_id.split('-')[1], $(this).find("a").attr("string"));
                   }
                }
            });
        });
        self.$element.find('#fields_list').mouseover(function(event) {
            if (event.relatedTarget) {
                if (event.relatedTarget.attributes['id'] && event.relatedTarget.attributes['string']) {
                    var field_id = event.relatedTarget.attributes["id"]["value"];
                    if (field_id && field_id.split("-")[0] === 'export') {
                        if (!self.$element.find("tr[id='treerow-" + field_id.split("-")[1] + "']").find('#tree-column').hasClass("oe_export_readonlyfield")) {
                            self.add_field(field_id.split("-")[1], event.relatedTarget.attributes["string"]["value"]);
                        }
                    }
                }
            }
        });
    },
    showcontent: function(id, flag) {
        // show & hide the contents
        var first_child = this.$element.find("tr[id='treerow-" + id + "']").find('img');
        if (flag) {
            first_child.attr('src', '/base/static/src/img/expand.gif');
        }
        else {
            first_child.attr('src', '/base/static/src/img/collapse.gif');
        }
        var child_field = this.$element.find("tr[id^='treerow-" + id +"/']");
        var child_len = (id.split("/")).length + 1;
        for (var i = 0; i < child_field.length; i++) {
            if (flag) {
                $(child_field[i]).hide();
            } else {
                if (child_len == (child_field[i].id.split("/")).length) {
                    if ($(child_field[i]).find('img').attr('src') == '/base/static/src/img/collapse.gif') {
                        $(child_field[i]).find('img').attr('src', '/base/static/src/img/expand.gif');
                    }
                    $(child_field[i]).show();
                }
            }
        }
    },
    add_field: function(field_id, string) {
        var field_list = this.$element.find('#fields_list');
        if (this.$element.find("#fields_list option[value='" + field_id + "']") && !this.$element.find("#fields_list option[value='" + field_id + "']").length) {
            field_list.append(new Option(string, field_id));
        }
    },
    get_fields: function() {
        var export_field = [];
        this.$element.find("#fields_list option").each(function() {
            export_field.push($(this).val());
        });
        if (!export_field.length) {
            alert('Please select fields to save export list...');
        }
        return export_field;
    },
    on_click_export_data: function() {
        $.blockUI(this.$element);
        var exported_fields = {};
        this.$element.find("#fields_list option").each(function() {
            exported_fields[$(this).val()] = $(this).text();
        });
        if (_.isEmpty(exported_fields)) {
            alert('Please select fields to export...');
            return;
        }

        this.session.get_file({
            url: '/base/export/export_data',
            data: {data: JSON.stringify({
                model: this.dataset.model,
                fields: exported_fields,
                ids: this.dataset.ids,
                domain: this.dataset.domain,
                import_compat: parseInt(
                        this.$element.find("#import_compat").val(), 10),
                export_format: this.$element.find("#export_format").val()
            })},
            complete: $.unblockUI
        });
    },
    close: function() {
        $(this.$dialog).remove();
        this._super();
    }
});

};
