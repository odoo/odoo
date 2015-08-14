
(function() {

var instance = openerp;
openerp.web.data_export = {};

var QWeb = instance.web.qweb,
      _t = instance.web._t;
instance.web.DataExport = instance.web.Dialog.extend({
    template: 'ExportTreeView',
    dialog_title: {toString: function () { return _t("Export Data"); }},
    events: {
        'click #add_field': function () {
            var self = this;
            this.$('#field-tree-structure tr.ui-selected')
                .removeClass('ui-selected')
                .find('a').each(function () {
                    var id = $(this).attr('id').split('-')[1];
                    var string = $(this).attr('string');
                    self.add_field(id, string);
                });
        },
        'click #remove_field': function () {
            this.$('#fields_list option:selected').remove();
        },
        'click #remove_all_field': function () {
            this.$('#fields_list').empty();
        },
        'click #export_new_list': 'on_show_save_list',
    },
    init: function(parent, dataset) {
        var self = this;
        var options = {
            buttons: [
                {text: _t("Close"), click: function () { self.$el.parents('.modal').modal('hide'); }},
                {text: _t("Export To File"), click: function () { self.on_click_export_data(); }}
            ],
            close: function () { self.close();}
        };
        this._super(parent, options);
        this.records = {};
        this.dataset = dataset;
        this.exports = new instance.web.DataSetSearch(
            this, 'ir.exports', this.dataset.get_context());
    },
    start: function() {
        var self = this;
        this._super.apply(this, arguments);

        var got_fields = new $.Deferred();
        this.$el.find('#import_compat').change(function() {
            self.$el.find('#fields_list').empty();
            self.$el.find('#field-tree-structure').remove();
            var import_comp = self.$el.find("#import_compat").val();
            self.rpc("/web/export/get_fields", {
                model: self.dataset.model,
                import_compat: !!import_comp,
            }).done(function (records) {
                got_fields.resolve();
                self.on_show_data(records);
            });
        }).change();

        var got_domain = this.getParent().get_active_domain().then(function (domain) {
            if (domain === undefined) {
                self.ids_to_export = self.getParent().get_selected_ids();
                self.domain = self.dataset.domain;
            }
            else {
                self.ids_to_export = false;
                self.domain = domain;
            }
            self.on_show_domain();
        });

        return $.when(
            got_fields,
            got_domain,
            this.rpc('/web/export/formats', {}).done(this.do_setup_export_formats),
            this.show_exports_list());
    },
    do_setup_export_formats: function (formats) {
        var $fmts = this.$el.find('#export_format');
        _(formats).each(function (format) {
            var opt = new Option(format.label, format.tag);
            if (format.error) {
                opt.disabled = true;
                opt.replaceChild(
                    document.createTextNode(
                        _.str.sprintf("%s — %s", format.label, format.error)),
                    opt.childNodes[0]);
            }
            $fmts.append(opt);
        });
    },
    show_exports_list: function() {
        var self = this;
        if (self.$el.find('#saved_export_list').is(':hidden')) {
            self.$el.find('#ExistsExportList').show();
            return $.when();
        }
        return this.exports.read_slice(['name'], {
            domain: [['resource', '=', this.dataset.model]]
        }).done(function (export_list) {
            if (!export_list.length) {
                return;
            }
            self.$el.find('#ExistsExportList').append(QWeb.render('Exists.ExportList', {'existing_exports': export_list}));
            self.$el.find('#saved_export_list').change(function() {
                self.$el.find('#fields_list option').remove();
                var export_id = self.$el.find('#saved_export_list option:selected').val();
                if (export_id) {
                    self.rpc('/web/export/namelist', {'model': self.dataset.model, export_id: parseInt(export_id, 10)}).done(self.do_load_export_field);
                }
            });
            self.$el.find('#delete_export_list').click(function() {
                var select_exp = self.$el.find('#saved_export_list option:selected');
                if (select_exp.val()) {
                    self.exports.unlink([parseInt(select_exp.val(), 10)]);
                    select_exp.remove();
                    self.$el.find("#fields_list option").remove();
                    if (self.$el.find('#saved_export_list option').length <= 1) {
                        self.$el.find('#ExistsExportList').hide();
                    }
                }
            });
        });
    },
    do_load_export_field: function(field_list) {
        var export_node = this.$el.find("#fields_list");
        _(field_list).each(function (field) {
            export_node.append(new Option(field.label, field.name));
        });
    },
    on_show_save_list: function() {
        var self = this;
        var current_node = self.$el.find("#savenewlist");
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
        }).then(function (export_list_id) {
            if (!export_list_id) {
                return;
            }
            if (!self.$el.find("#saved_export_list").length || self.$el.find("#saved_export_list").is(":hidden")) {
                self.show_exports_list();
            }
            self.$el.find("#saved_export_list").append( new Option(value, export_list_id) );
        });
        this.on_show_save_list();
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
            var import_comp = self.$el.find("#import_compat").val();
            self.rpc("/web/export/get_fields", {
                model: model,
                prefix: prefix,
                parent_name: name,
                import_compat: Boolean(import_comp),
                parent_field_type : record['field_type'],
                exclude: exclude_fields
            }).done(function(results) {
                record.loaded = true;
                self.on_show_data(results, record.id);
            });
        } else {
            self.showcontent(record.id);
        }
    },
    on_show_domain: function() {
        this.$el.find('tr').first().find('td').append(QWeb.render('ExportTreeView-Domain', {'record': this}));
    },
    on_show_data: function(result, after) {
        var self = this;

        if (after) {
            var current_tr = self.$el.find("tr[id='treerow-" + after + "']");
            current_tr.addClass('open');
            current_tr.find('img').attr('src','/web/static/src/img/collapse.gif');
            current_tr.after(QWeb.render('ExportTreeView-Secondary.children', {'fields': result}));
        } else {
            self.$el.find('#left_field_panel').append(QWeb.render('ExportTreeView-Secondary', {'fields': result}));
        }
        _.each(result, function(record) {
            self.records[record.id] = record.value;
            if (record.required) {
                var required_fld = self.$el.find("tr[id='treerow-" + record.id + "']").find('#tree-column');
                required_fld.addClass("oe_export_requiredfield");
            }
            self.$el.find("img[id='parentimg-" + record.id +"']").click(function() {
                self.on_click(this.id, record);
            });

            self.$el.find("tr[id='treerow-" + record.id + "']").click(function(e) {
                if (e.shiftKey) {
                    var frst_click, scnd_click = '';
                    if (self.row_index === 0) {
                        self.row_index = this.rowIndex;
                        frst_click = self.$el.find("tr[id^='treerow-']")[self.row_index-1];
                        $(frst_click).addClass("ui-selected");
                    } else {
                        var i;
                        if (this.rowIndex >=self.row_index) {
                            for (i = (self.row_index-1); i < this.rowIndex; i++) {
                                scnd_click = self.$el.find("tr[id^='treerow-']")[i];
                                if (!$(scnd_click).find('#tree-column').hasClass("oe_export_readonlyfield")) {
                                    $(scnd_click).addClass("ui-selected");
                                }
                            }
                        } else {
                            for (i = (self.row_index-1); i >= (this.rowIndex-1); i--) {
                                scnd_click = self.$el.find("tr[id^='treerow-']")[i];
                                if (!$(scnd_click).find('#tree-column').hasClass("oe_export_readonlyfield")) {
                                    $(scnd_click).addClass("ui-selected");
                                }
                            }
                        }
                    }
                }
                self.row_index = this.rowIndex;

                self.$el.find("tr[id='treerow-" + record.id + "']").keyup(function() {
                    self.row_index = 0;
                });
                var o2m_selection = self.$el.find("tr[id='treerow-" + record.id + "']").find('#tree-column');
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
                    self.$el.find("tr.ui-selected")
                            .removeClass("ui-selected").find('a').blur();
                    $(this).addClass("ui-selected").find('a').focus();
                }
                return false;
            });

            self.$el.find("tr[id='treerow-" + record.id + "']").keydown(function(e) {
                var keyCode = e.keyCode || e.which;
                var arrow = {left: 37, up: 38, right: 39, down: 40 };
                var elem;
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
                        elem = this;
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
                        elem = this;
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
            self.$el.find("tr[id='treerow-" + record.id + "']").dblclick(function() {
                var $o2m_selection = self.$el.find("tr[id^='treerow-" + record.id + "']").find('#tree-column');
                if (!$o2m_selection.hasClass("oe_export_readonlyfield")) {
                   self.add_field(record.id, $(this).find("a").attr("string"));
                }
            });
        });
        self.$el.find('#fields_list').mouseover(function(event) {
            if (event.relatedTarget) {
                if (event.relatedTarget.attributes['id'] && event.relatedTarget.attributes['string']) {
                    var field_id = event.relatedTarget.attributes["id"]["value"];
                    if (field_id && field_id.split("-")[0] === 'export') {
                        if (!self.$el.find("tr[id='treerow-" + field_id.split("-")[1] + "']").find('#tree-column').hasClass("oe_export_readonlyfield")) {
                            self.add_field(field_id.split("-")[1], event.relatedTarget.attributes["string"]["value"]);
                        }
                    }
                }
            }
        });
    },
    showcontent: function(id) {
        // show & hide the contents
        var $this = this.$el.find("tr[id='treerow-" + id + "']");
        var is_open = $this.hasClass('open');
        $this.toggleClass('open');

        var first_child = $this.find('img');
        if (is_open) {
            first_child.attr('src', '/web/static/src/img/expand.gif');
        } else {
            first_child.attr('src', '/web/static/src/img/collapse.gif');
        }
        var child_field = this.$el.find("tr[id^='treerow-" + id +"/']");
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
        var field_list = this.$el.find('#fields_list');
        if (this.$el.find("#fields_list option[value='" + field_id + "']")
                && !this.$el.find("#fields_list option[value='" + field_id + "']").length) {
            field_list.append(new Option(string, field_id));
        }
    },
    get_fields: function() {
        var export_fields = this.$("#fields_list option").map(function() {
            return $(this).val();
        }).get();
        if (!export_fields.length) {
            alert(_t("Please select fields to save export list..."));
        }
        return export_fields;
    },
    on_click_export_data: function() {
        var self = this;
        var exported_fields = this.$el.find('#fields_list option').map(function () {
            // DOM property is textContent, but IE8 only knows innerText
            return {name: self.records[this.value] || this.value,
                    label: this.textContent || this.innerText};
        }).get();

        if (_.isEmpty(exported_fields)) {
            alert(_t("Please select fields to export..."));
            return;
        }
        exported_fields.unshift({name: 'id', label: 'External ID'});

        var export_format = this.$el.find("#export_format").val();
        var c = instance.webclient.crashmanager;

        instance.web.blockUI();
        this.session.get_file({
            url: '/web/export/' + export_format,
            data: {data: JSON.stringify({
                model: this.dataset.model,
                fields: exported_fields,
                ids: this.ids_to_export,
                domain: this.domain,
                context: this.dataset.context,
                import_compat: !!this.$el.find("#import_compat").val(),
            })},
            complete: instance.web.unblockUI,
            error: c.rpc_error.bind(c),
        });
    },
    close: function() {
        this._super();
    }
});

})();
