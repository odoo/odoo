openerp.web.data_export = function(openerp) {
var QWeb = openerp.web.qweb,
      _t = openerp.web._t;
openerp.web.DataExport = openerp.web.Dialog.extend({
    template: 'ExportTreeView',
    dialog_title: {toString: function () { return _t("Export Data"); }},
    init: function(parent, dataset) {
        this._super(parent);
        this.records = {};
        this.dataset = dataset;
        this.exports = new openerp.web.DataSetSearch(
            this, 'ir.exports', this.dataset.get_context());
    },
    start: function() {
        var self = this;
        this._super.apply(this, arguments);
        this.open({
            buttons : [
                {text: _t("Close"), click: function() { self.close(); }},
                {text: _t("Export To File"), click: function() { self.on_click_export_data(); }}
            ],
            close: function(event, ui){ self.close();}
        });
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
        this.$element.find('#export_new_list').click(this.on_show_save_list);

        var got_fields = new $.Deferred();
        this.$element.find('#import_compat').change(function() {
            self.$element.find('#fields_list').empty();
            self.$element.find('#field-tree-structure').remove();
            var import_comp = self.$element.find("#import_compat").val();
            self.rpc("/web/export/get_fields", {
                model: self.dataset.model,
                import_compat: Boolean(import_comp)
            }, function (records) {
                got_fields.resolve();
                self.on_show_data(records);
            });
        }).change();

        return $.when(
            got_fields,
            this.rpc('/web/export/formats', {}, this.do_setup_export_formats),
            this.show_exports_list());
    },
    do_setup_export_formats: function (formats) {
        var $fmts = this.$element.find('#export_format');
        _(formats).each(function (format) {
            var opt = new Option(format.label, format.tag);
            if (format.error) {
                opt.disabled = true;
                opt.replaceChild(
                    document.createTextNode(
                        _.str.sprintf("%s — %s", format.label, format.error)),
                    opt.childNodes[0])
            }
            var options = $fmts.prop('options');
            options[options.length] = opt;
        });
    },
    show_exports_list: function() {
        var self = this;
        if (self.$element.find('#saved_export_list').is(':hidden')) {
            self.$element.find('#ExistsExportList').show();
            return;
        }
        return this.exports.read_slice(['name'], {
            domain: [['resource', '=', this.dataset.model]]
        }).then(function (export_list) {
            if (!export_list.length) {
                return;
            }
            self.$element.find('#ExistsExportList').append(QWeb.render('Exists.ExportList', {'existing_exports': export_list}));
            self.$element.find('#saved_export_list').change(function() {
                self.$element.find('#fields_list option').remove();
                var export_id = self.$element.find('#saved_export_list option:selected').val();
                if (export_id) {
                    self.rpc('/web/export/namelist', {'model': self.dataset.model, export_id: parseInt(export_id)}, self.do_load_export_field);
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
        _(field_list).each(function (field) {
            export_node.append(new Option(field.label, field.name));
        });
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
                    alert(_t("Please enter save field list name"));
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
            if (!export_list_id.result) {
                return;
            }
            self.$element.find("#saved_export_list").append(
                    new Option(value, export_list_id.result));
            if (self.$element.find("#saved_export_list").is(":hidden")) {
                self.show_exports_list();
            }
        });
        this.on_show_save_list();
        this.$element.find("#fields_list option").remove();
    },
    on_click: function(id, record) {
        var self = this;
        if (!record['children']) {
            return;
        }
        var model = record['params']['model'],
            prefix = record['params']['prefix'],
            name = record['params']['name'],
            exclude_fields = [];
        if (record['relation_field']) {
            exclude_fields.push(record['relation_field']);
        }

        if (!record.loaded) {
            var import_comp = self.$element.find("#import_compat").val();
            self.rpc("/web/export/get_fields", {
                model: model,
                prefix: prefix,
                parent_name: name,
                import_compat: Boolean(import_comp),
                parent_field_type : record['field_type'],
                exclude: exclude_fields
            }, function(results) {
                record.loaded = true;
                self.on_show_data(results, record.id);
            });
        } else {
            self.showcontent(record.id);
        }
    },
    on_show_data: function(result, after) {
        var self = this;
        var imp_cmpt = Boolean(self.$element.find("#import_compat").val());

        if (after) {
            var current_tr = self.$element.find("tr[id='treerow-" + after + "']");
            current_tr.addClass('open');
            current_tr.find('img').attr('src','/web/static/src/img/collapse.gif');
            current_tr.after(QWeb.render('ExportTreeView-Secondary.children', {'fields': result}));
        } else {
            self.$element.find('#left_field_panel').append(QWeb.render('ExportTreeView-Secondary', {'fields': result}));
        }
        _.each(result, function(record) {
            self.records[record.id] = record.value;
            if (record.required) {
                var required_fld = self.$element.find("tr[id='treerow-" + record.id + "']").find('#tree-column');
                required_fld.addClass("oe_export_requiredfield");
            }
            self.$element.find("img[id='parentimg-" + record.id +"']").click(function() {
                self.on_click(this.id, record);
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
                        if ($(this).hasClass('open')) {
                            self.on_click(this.id, record);
                        }
                        break;
                    case arrow.right:
                        if (!$(this).hasClass('open')) {
                            self.on_click(this.id, record);
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
                   self.add_field(record.id, $(this).find("a").attr("string"));
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
    showcontent: function(id) {
        // show & hide the contents
        var $this = this.$element.find("tr[id='treerow-" + id + "']");
        var is_open = $this.hasClass('open');
        $this.toggleClass('open');

        var first_child = $this.find('img');
        if (is_open) {
            first_child.attr('src', '/web/static/src/img/expand.gif');
        } else {
            first_child.attr('src', '/web/static/src/img/collapse.gif');
        }
        var child_field = this.$element.find("tr[id^='treerow-" + id +"/']");
        var child_len = (id.split("/")).length + 1;
        for (var i = 0; i < child_field.length; i++) {
            var $child = $(child_field[i]);
            if (is_open) {
                $child.hide();
            } else if (child_len == (child_field[i].id.split("/")).length) {
                if ($child.hasClass('open')) {
                    $child.removeClass('open');
                    $child.find('img').attr('src', '/web/static/src/img/expand.gif');
                }
                $child.show();
            }
        }
    },
    add_field: function(field_id, string) {
        var field_list = this.$element.find('#fields_list');
        if (this.$element.find("#fields_list option[value='" + field_id + "']")
                && !this.$element.find("#fields_list option[value='" + field_id + "']").length) {
            var options = field_list.prop('options');
            options[options.length] = new Option(string, field_id);
        }
    },
    get_fields: function() {
        var export_field = [];
        this.$element.find("#fields_list option").each(function() {
            export_field.push($(this).val());
        });
        if (!export_field.length) {
            alert(_t("Please select fields to save export list..."));
        }
        return export_field;
    },
    on_click_export_data: function() {
        var self = this;
        var exported_fields = this.$element.find('#fields_list option').map(function () {
            // DOM property is textContent, but IE8 only knows innerText
            return {name: self.records[this.value] || this.value,
                    label: this.textContent || this.innerText};
        }).get();

        if (_.isEmpty(exported_fields)) {
            alert(_t("Please select fields to export..."));
            return;
        }

        exported_fields.unshift({name: 'id', label: 'External ID'});
        var export_format = this.$element.find("#export_format").val();
        $.blockUI();
        this.session.get_file({
            url: '/web/export/' + export_format,
            data: {data: JSON.stringify({
                model: this.dataset.model,
                fields: exported_fields,
                ids: this.dataset.ids,
                domain: this.dataset.domain,
                import_compat: Boolean(
                    this.$element.find("#import_compat").val())
            })},
            complete: $.unblockUI
        });
    },
    close: function() {
        this.$element.remove();
        this._super();
    }
});

};
