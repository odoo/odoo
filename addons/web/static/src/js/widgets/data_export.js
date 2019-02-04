odoo.define('web.DataExport', function (require) {
"use strict";

var core = require('web.core');
var crash_manager = require('web.crash_manager');
var data = require('web.data');
var Dialog = require('web.Dialog');
var framework = require('web.framework');
var pyUtils = require('web.py_utils');

var QWeb = core.qweb;
var _t = core._t;

var DataExport = Dialog.extend({
    template: 'ExportDialog',
    events: {
        'click .o_expand': function(e) {
            this.on_expand_action(this.records[$(e.target).closest('.o_export_tree_item').data('id')]);
        },
        'click .o_export_tree_item': function(e) {
            e.stopPropagation();
            var $elem = $(e.currentTarget);

            var row_index = $elem.prevAll('.o_export_tree_item').length;
            var row_index_level = $elem.parents('.o_export_tree_item').length;

            if(e.shiftKey && row_index_level === this.row_index_level) {
                var minIndex = Math.min(row_index, this.row_index);
                var maxIndex = Math.max(row_index, this.row_index);

                this.$records.filter(function() { return ($elem.parent()[0] === $(this).parent()[0]); })
                             .slice(minIndex, maxIndex+1)
                             .addClass('o_selected')
                             .filter(':not(:last)')
                             .each(process_children);
            }

            this.row_index = row_index;
            this.row_index_level = row_index_level;

            if(e.ctrlKey) {
                $elem.toggleClass('o_selected').focus();
            } else if(e.shiftKey) {
                $elem.addClass('o_selected').focus();
            } else {
                this.$(".o_selected").removeClass("o_selected")
                $elem.addClass("o_selected").focus();
            }

            function process_children() {
                var $this = $(this);
                if($this.hasClass('show')) {
                    $this.children('.o_export_tree_item')
                         .addClass('o_selected')
                         .each(process_children);
                }
            }
        },
        'dblclick .o_export_tree_item:not(.haschild)': function(e) {
            var self = this;
            function addElement(el) {
                self.add_field(el.getAttribute('data-id'), el.querySelector('.o_tree_column').textContent);
            }
            var target = e.currentTarget;
            target.classList.remove('o_selected');
            // Add parent fields to export
            [].reverse.call($(target).parents('.o_export_tree_item')).each(function () {
                addElement(this);
            });
            // add field itself
            addElement(target);
        },
        'keydown .o_export_tree_item': function(e) {
            e.stopPropagation();
            var $elem = $(e.currentTarget);
            var record = this.records[$elem.data('id')];

            switch(e.keyCode || e.which) {
                case $.ui.keyCode.LEFT:
                    if ($elem.hasClass('show')) {
                        this.on_expand_action(record);
                    }
                    break;
                case $.ui.keyCode.RIGHT:
                    if (!$elem.hasClass('show')) {
                        this.on_expand_action(record);
                    }
                    break;
                case $.ui.keyCode.UP:
                    var $prev = $elem.prev('.o_export_tree_item');
                    if($prev.length === 1) {
                        while($prev.hasClass('show')) {
                            $prev = $prev.children('.o_export_tree_item').last();
                        }
                    } else {
                        $prev = $elem.parent('.o_export_tree_item');
                        if($prev.length === 0) {
                            break;
                        }
                    }

                    $elem.removeClass("o_selected").blur();
                    $prev.addClass("o_selected").focus();
                    break;
                case $.ui.keyCode.DOWN:
                    var $next;
                    if($elem.hasClass('show')) {
                        $next = $elem.children('.o_export_tree_item').first();
                    } else {
                        $next = $elem.next('.o_export_tree_item');
                        if($next.length === 0) {
                            $next = $elem.parent('.o_export_tree_item').next('.o_export_tree_item');
                            if($next.length === 0) {
                                break;
                            }
                        }
                    }

                    $elem.removeClass("o_selected").blur();
                    $next.addClass("o_selected").focus();
                    break;
            }
        },

        'click .o_add_field': function() {
            var self = this;
            this.$('.o_field_tree_structure .o_selected')
                .removeClass('o_selected')
                .each(function() {
                    var $this = $(this);
                    self.add_field($this.data('id'), $this.children('.o_tree_column').text());
                });
        },
        'click .o_remove_field': function() {
            this.$fields_list.find('option:selected').remove();
        },
        'click .o_remove_all_field': function() {
            this.$fields_list.empty();
        },
        'click .o_move_up': function() {
            var $selected_rows = this.$fields_list.find('option:selected');

            var $prev_row = $selected_rows.first().prev();
            if($prev_row.length){
                $prev_row.before($selected_rows.detach());
            }
        },
        'click .o_move_down': function () {
            var $selected_rows = this.$fields_list.find('option:selected');

            var $next_row = $selected_rows.last().next();
            if($next_row.length){
                $next_row.after($selected_rows.detach());
            }
        },

        'click .o_toggle_save_list': function(e) {
            e.preventDefault();

            var $saveList = this.$(".o_save_list");
            if($saveList.is(':empty')) {
                $saveList.append(QWeb.render('Export.SaveList'));
            } else {
                if($saveList.is(':hidden')) {
                    $saveList.show();
                    $saveList.find(".o_export_list_input").val("");
                } else {
                    $saveList.hide();
                }
            }
        },
        'click .o_save_list > button': function(e) {
            var $saveList = this.$(".o_save_list");

            var value = $saveList.find("input").val();
            if(!value) {
                Dialog.alert(this, _t("Please enter save field list name"));
                return;
            }

            var fields = this.get_fields();
            if (fields.length === 0) {
                return;
            }

            $saveList.hide();

            var self = this;
            this.exports.create({
                name: value,
                resource: this.record.model,
                export_fields: _.map(fields, function (field) {
                    return [0, 0, {name: field}];
                }),
            }).then(function(export_list_id) {
                if(!export_list_id) {
                    return;
                }
                var $select = self.$(".o_exported_lists_select");
                if($select.length === 0 || $select.is(":hidden")) {
                    self.show_exports_list();
                }
                $select.append(new Option(value, export_list_id));
            });
        },
    },
    init: function(parent, record, defaultExportFields) {
        var options = {
            title: _t("Export Data"),
            buttons: [
                {text: _t("Export To File"), click: this.export_data, classes: "btn-primary"},
                {text: _t("Close"), close: true},
            ],
        };
        this._super(parent, options);
        this.records = {};
        this.record = record;
        this.defaultExportFields = defaultExportFields;
        this.exports = new data.DataSetSearch(this, 'ir.exports', this.record.getContext());

        this.row_index = 0;
        this.row_index_level = 0;
    },
    start: function() {
        var self = this;
        var waitFor = [this._super.apply(this, arguments)];

        // The default for the ".modal_content" element is "max-height: 100%;"
        // but we want it to always expand to "height: 100%;" for this modal.
        // This can be achieved thanks to CSS modification without touching
        // the ".modal-content" rules... but not with Internet explorer (11).
        this.$modal.find(".modal-content").css("height", "100%");

        this.$fields_list = this.$('.o_fields_list');
        this.$import_compat_radios = this.$('.o_import_compat input');

        waitFor.push(this._rpc({route: '/web/export/formats'}).then(do_setup_export_formats));

        var got_fields = new $.Deferred();
        this.$import_compat_radios.change(function(e) {
            self.isCompatibleMode = !!$(e.target).val();
            self.$('.o_field_tree_structure').remove();

            self._rpc({
                    route: '/web/export/get_fields',
                    params: {
                        model: self.record.model,
                        import_compat: self.isCompatibleMode,
                    },
                })
                .done(function (records) {
                    var compatible_fields = _.map(records, function (record) {return record.id; });
                    self.$fields_list
                        .find('option')
                        .filter(function () {
                            var option_field = $(this).attr('value');
                            if (compatible_fields.indexOf(option_field) === -1) {
                                return true;
                            }
                        })
                        .remove();
                    got_fields.resolve();
                    self.on_show_data(records);
                    // In compatible mode add ID field as first field to export
                    if (self.isCompatibleMode) {
                        self.$('.o_fields_list').prepend(new Option(_('External ID'), 'id'));
                    }
                    _.each(records, function (record) {
                        if (_.contains(self.defaultExportFields, record.id)) {
                            self.add_field(record.id, record.string);
                        }
                    });
                });
        }).eq(0).change();
        waitFor.push(got_fields);

        waitFor.push(this.getParent().getActiveDomain().then(function (domain) {
            if (domain === undefined) {
                self.ids_to_export = self.getParent().getSelectedIds();
                self.domain = self.record.domain;
            } else {
                self.ids_to_export = false;
                self.domain = domain;
            }
        }));

        waitFor.push(this.show_exports_list().then(function () {
            _.each(self.records, function (record, key) {
                if (_.contains(self.defaultExportFields, key)) {
                    self.add_field(key, record.string);
                }
            });
        }));

        return $.when.apply($, waitFor);

        function do_setup_export_formats(formats) {
            var $fmts = self.$('.o_export_format');

            _.each(formats, function(format, i) {
                var $radio = $('<input/>', {type: 'radio', value: format.tag, name: 'o_export_format_name'});
                var $label = $('<span/>', {html: format.label});

                if (format.error) {
                    $radio.prop('disabled', true);
                    $label.html(_.str.sprintf("%s — %s", format.label, format.error));
                }

                var $radioButton = $('<label/>').append($radio, $label);
                $fmts.append($("<div class='radio'></div>").append($radioButton));
            });

            self.$export_format_inputs = $fmts.find('input');
            self.$export_format_inputs.filter(':enabled').first().prop('checked', true);
        }
    },
    show_exports_list: function() {
        if (this.$('.o_exported_lists_select').is(':hidden')) {
            this.$('.o_exported_lists').show();
            return $.when();
        }

        var self = this;
        return this._rpc({
            model: 'ir.exports',
            method: 'search_read',
            fields: ['name'],
            domain: [['resource', '=', this.record.model]]
        }).then(function (export_list) {
            if (!export_list.length) {
                return;
            }
            self.$('.o_exported_lists').append(QWeb.render('Export.SavedList', {'existing_exports': export_list}));
            self.$('.o_exported_lists_select').on('change', function() {
                self.$fields_list.empty();
                var export_id = self.$('.o_exported_lists_select option:selected').val();
                if(export_id) {
                    self._rpc({
                            route: '/web/export/namelist',
                            params: {
                                model: self.record.model,
                                export_id: parseInt(export_id, 10),
                            },
                        })
                        .then(do_load_export_field);
                }
            });
            self.$('.o_delete_exported_list').click(function() {
                var select_exp = self.$('.o_exported_lists_select option:selected');
                var options = {
                    confirm_callback: function () {
                        if (select_exp.val()) {
                            self.exports.unlink([parseInt(select_exp.val(), 10)]);
                            select_exp.remove();
                            self.$fields_list.empty();
                            if (self.$('.o_exported_lists_select option').length <= 1) {
                                self.$('.o_exported_lists').hide();
                            }
                        }
                    }
                };
                Dialog.confirm(this, _t("Do you really want to delete this export template?"), options);
            });
       });

        function do_load_export_field(field_list) {
            _.each(field_list, function (field) {
                self.$fields_list.append(new Option(field.label, field.name));
            });
        }
    },
    on_expand_action: function(record) {
        if(!record['children']) {
            return;
        }

        var model = record['params']['model'];
        var prefix = record['params']['prefix'];
        var name = record['params']['name'];
        var exclude_fields = [];
        if(record['relation_field']) {
            exclude_fields.push(record['relation_field']);
        }

        if(!record.loaded) {
            var self = this;
            this._rpc({
                    route: '/web/export/get_fields',
                    params: {
                        model: model,
                        prefix: prefix,
                        parent_name: name,
                        import_compat: !!this.$import_compat_radios.filter(':checked').val(),
                        parent_field_type : record['field_type'],
                        parent_field: record['params']['parent_field'],
                        exclude: exclude_fields,
                    },
                })
                .done(function(results) {
                    record.loaded = true;
                    self.on_show_data(results, record.id);
                });
        } else {
            this.show_content(record.id);
        }
    },
    on_show_data: function(records, expansion) {
        var self = this;
        if(expansion) {
            this.$('.o_export_tree_item[data-id="' + expansion + '"]')
                .addClass('show')
                .find('.o_expand_parent')
                .toggleClass('fa-chevron-right fa-chevron-down')
                .next()
                .after(QWeb.render('Export.TreeItems', {'fields': records, 'debug': this.getSession().debug}));
        } else {
            this.$('.o_left_field_panel').empty().append(
                $("<div/>").addClass('o_field_tree_structure')
                           .append(QWeb.render('Export.TreeItems', {'fields': records, 'debug': this.getSession().debug}))
            );
        }

        _.extend(this.records, _.object(_.pluck(records, 'id'), records));
        this.$records = this.$(".o_export_tree_item");
        this.$records.each(function(i, el) {
            var $elem = $(el);
            $elem.find('.o_tree_column').first().toggleClass('o_required', !!self.records[$elem.data('id')].required);
        });
    },
    show_content: function(id) {
        var $this = this.$('.o_export_tree_item[data-id="' + id + '"]');
        $this.toggleClass('show');
        var is_open = $this.hasClass('show');

        $this.children('.o_expand_parent').toggleClass('fa-chevron-down', !!is_open).toggleClass('fa-chevron-right', !is_open);

        var $child_field = $this.find('.o_export_tree_item');
        var child_len = (id.split("/")).length + 1;
        for (var i = 0 ; i < $child_field.length ; i++) {
            var $child = $child_field.eq(i);
            if(!is_open) {
                $child.hide();
            } else if(child_len === $child_field.eq(i).data('id').split("/").length) {
                if ($child.hasClass('show')) {
                    $child.removeClass('show');
                    $child.children('.o_expand_parent').removeClass('fa-chevron-down').addClass('fa-chevron-right');
                }
                $child.show();
            }
        }
    },
    add_field: function(field_id, string) {
        var $field_list = this.$('.o_fields_list');
        field_id = this.records[field_id].value || field_id;
        if($field_list.find("option[value='" + field_id + "']").length === 0) {
            $field_list.append(new Option(string, field_id));
        }
    },
    get_fields: function() {
        var $export_fields = this.$(".o_fields_list option").map(function() {
            return $(this).val();
        }).get();
        if($export_fields.length === 0) {
            Dialog.alert(this, _t("Please select fields to save export list..."));
        }
        return $export_fields;
    },
    export_data: function() {
        var self = this;
        var exported_fields = this.$('.o_fields_list option').map(function () {
            return {
                name: (self.records[this.value] || this).value,
                label: this.textContent || this.innerText // DOM property is textContent, but IE8 only knows innerText
            };
        }).get();

        if (_.isEmpty(exported_fields)) {
            Dialog.alert(this, _t("Please select fields to export..."));
            return;
        }
        if (!this.isCompatibleMode) {
            exported_fields.unshift({name: 'id', label: _t('External ID')});
        }

        var export_format = this.$export_format_inputs.filter(':checked').val();

        framework.blockUI();
        this.getSession().get_file({
            url: '/web/export/' + export_format,
            data: {data: JSON.stringify({
                model: this.record.model,
                fields: exported_fields,
                ids: this.ids_to_export,
                domain: this.domain,
                context: pyUtils.eval('contexts', [this.record.getContext()]),
                import_compat: !!this.$import_compat_radios.filter(':checked').val(),
            })},
            complete: framework.unblockUI,
            error: crash_manager.rpc_error.bind(crash_manager),
        });
    },
});

return DataExport;

});
