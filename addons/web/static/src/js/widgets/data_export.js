odoo.define('web.DataExport', function (require) {
"use strict";

var core = require('web.core');
var crash_manager = require('web.crash_manager');
var Dialog = require('web.Dialog');
var data = require('web.data');
var framework = require('web.framework');
var pyUtils = require('web.py_utils');

var QWeb = core.qweb;
var _t = core._t;

var DataExport = Dialog.extend({
    template: 'ExportDialog',
    events: {
        'change .o_exported_lists_select': '_onChangeExportList',
        'change .o_import_compat input': '_onChangeCompatibleInput',
        'click .o_add_field': '_onClickAddField',
        'click .o_delete_exported_list': '_onClickDeleteExportListBtn',
        'click .o_expand': '_onClickExpand',
        'click .o_move_down': '_onClickMovedown',
        'click .o_move_up': '_onClickMoveup',
        'click .o_remove_all_field': '_onClickRemoveAllFields',
        'click .o_remove_field': '_onClickRemoveField',
        'click .o_toggle_save_list': '_onClickSaveList',
        'click .o_save_list > button': '_onClickSaveListBtn',
        'click .o_export_tree_item': '_onClickTreeItem',
        'dblclick .o_export_tree_item:not(.haschild)': '_onDblclickTreeItem',
        'keydown .o_export_tree_item': '_onKeydownTreeItem'
    },
    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} record
     * @param {string[]} defaultExportFields
     */
    init: function (parent, record, defaultExportFields) {
        var options = {
            title: _t("Export Data"),
            buttons: [
                {text: _t("Export To File"), click: this._exportData, classes: 'btn-primary'},
                {text: _t("Close"), close: true},
            ],
        };
        this._super(parent, options);
        this.records = {};
        this.record = record;
        this.defaultExportFields = defaultExportFields;
        this.exports = new data.DataSetSearch(this, 'ir.exports', this.record.getContext());
        this.rowIndex = 0;
        this.rowIndexLevel = 0;
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        var proms = [this._super.apply(this, arguments)];

        // The default for the ".modal_content" element is "max-height: 100%;"
        // but we want it to always expand to "height: 100%;" for this modal.
        // This can be achieved thanks to CSS modification without touching
        // the ".modal-content" rules... but not with Internet explorer (11).
        this.$modal.find('.modal-content').css('height', '100%');

        this.$fieldsList = this.$('.o_fields_list');
        this.$importCompatRadios = this.$('.o_import_compat input');

        proms.push(this._rpc({route: '/web/export/formats'}).then(doSetupExportFormats));
        proms.push(this._onChangeCompatibleInput());

        proms.push(this.getParent().getActiveDomain().then(function (domain) {
            if (domain === undefined) {
                self.idsToExport = self.getParent().getSelectedIds();
                self.domain = self.record.domain;
            } else {
                self.idsToExport = false;
                self.domain = domain;
            }
        }));

        proms.push(this._showExportsList().then(function () {
            _.each(self.records, function (record, key) {
                if (_.contains(self.defaultExportFields, key)) {
                    self._addField(key, record.string);
                }
            });
        }));

        return Promise.all(proms);

        function doSetupExportFormats(formats) {
            var $fmts = self.$('.o_export_format');

            _.each(formats, function (format) {
                var $radio = $('<input/>', {type: 'radio', value: format.tag, name: 'o_export_format_name'});
                var $label = $('<span/>', {html: format.label});

                if (format.error) {
                    $radio.prop('disabled', true);
                    $label.html(_.str.sprintf("%s — %s", format.label, format.error));
                }

                var $radioButton = $('<label/>').append($radio, $label);
                $fmts.append($("<div class='radio'></div>").append($radioButton));
            });

            self.$exportFormatInputs = $fmts.find('input');
            self.$exportFormatInputs.filter(':enabled').first().prop('checked', true);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add the field in the export list
     *
     * @private
     * @param {string} fieldID
     * @param {string} label
     */
    _addField: function (fieldID, label) {
        var $fieldList = this.$('.o_fields_list');
        fieldID = this.records[fieldID].value || fieldID;
        if ($fieldList.find('option[value="' + fieldID + '"]').length === 0) {
            $fieldList.append(new Option(label, fieldID));
        }
    },
    /**
     * Submit the user data and export the file
     *
     * @private
     */
    _exportData: function () {
        var self = this;
        var exportedFields = this.$('.o_fields_list option').map(function () {
            return {
                name: (self.records[this.value] || this).value,
                label: this.textContent || this.innerText, // DOM property is textContent, but IE8 only knows innerText
            };
        }).get();

        if (_.isEmpty(exportedFields)) {
            Dialog.alert(this, _t("Please select fields to export..."));
            return;
        }
        if (!this.isCompatibleMode) {
            exportedFields.unshift({ name: 'id', label: _t('External ID') });
        }

        var exportFormat = this.$exportFormatInputs.filter(':checked').val();

        framework.blockUI();
        this.getSession().get_file({
            url: '/web/export/' + exportFormat,
            data: {
                data: JSON.stringify({
                    model: this.record.model,
                    fields: exportedFields,
                    ids: this.idsToExport,
                    domain: this.domain,
                    context: pyUtils.eval('contexts', [this.record.getContext()]),
                    import_compat: !!this.$importCompatRadios.filter(':checked').val(),
                })
            },
            complete: framework.unblockUI,
            error: crash_manager.rpc_error.bind(crash_manager),
        });
    },
    /**
     * @private
     * @returns {string[]} exportFields
     */
    _getFields: function () {
        var exportFields = this.$('.o_fields_list option').map(function () {
            return $(this).val();
        }).get();
        if (exportFields.length === 0) {
            Dialog.alert(this, _t("Please select fields to save export list..."));
        }
        return exportFields;
    },
    /**
     * Fetch the field info for the relational field. This method will be
     * invoked when the user expands the relational field from keyboard/mouse.
     *
     * @private
     * @param {Object} record
     */
    _onExpandAction: function (record) {
        var self = this;
        if (!record.children) {
            return;
        }

        var model = record.params.model;
        var prefix = record.params.prefix;
        var name = record.params.name;
        var excludeFields = [];
        if (record.relation_field) {
            excludeFields.push(record.relation_field);
        }

        if (!record.loaded) {
            this._rpc({
                route: '/web/export/get_fields',
                params: {
                    model: model,
                    prefix: prefix,
                    parent_name: name,
                    import_compat: !!this.$importCompatRadios.filter(':checked').val(),
                    parent_field_type: record.field_type,
                    parent_field: record.params.parent_field,
                    exclude: excludeFields,
                },
            }).then(function (results) {
                record.loaded = true;
                self._onShowData(results, record.id);
            });
        } else {
            this._showContent(record.id);
        }
    },
    /**
     * After the fetching the fields info for the relational field, this method
     * will render a list of a field for expanded relational field.
     *
     * @private
     * @param {Object[]} records
     * @param {string} expansion
     */
    _onShowData: function (records, expansion) {
        var self = this;
        if (expansion) {
            this.$('.o_export_tree_item[data-id="' + expansion + '"]')
                .addClass('show')
                .find('.o_expand_parent')
                .toggleClass('fa-chevron-right fa-chevron-down')
                .next()
                .after(QWeb.render('Export.TreeItems', {fields: records, debug: this.getSession().debug}));
        } else {
            this.$('.o_left_field_panel').empty().append(
                $('<div/>').addClass('o_field_tree_structure')
                           .append(QWeb.render('Export.TreeItems', {fields: records, debug: this.getSession().debug}))
            );
            this.records = {};
        }

        _.extend(this.records, _.object(_.pluck(records, 'id'), records));
        this.$records = this.$('.o_export_tree_item');
        this.$records.each(function (i, el) {
            var $el = $(el);
            $el.find('.o_tree_column').first().toggleClass('o_required', !!self.records[$el.data('id')].required);
        });
    },
    /**
     * If relational fields info is already fetched then this method is
     * used to display fields.
     *
     * @private
     * @param {string} fieldID
     */
    _showContent: function (fieldID) {
        var $item = this.$('.o_export_tree_item[data-id="' + fieldID + '"]');
        $item.toggleClass('show');
        var isOpen = $item.hasClass('show');

        $item.children('.o_expand_parent').toggleClass('fa-chevron-down', !!isOpen).toggleClass('fa-chevron-right', !isOpen);

        var $childField = $item.find('.o_export_tree_item');
        var childLength = (fieldID.split('/')).length + 1;
        for (var i = 0 ; i < $childField.length ; i++) {
            var $child = $childField.eq(i);
            if (!isOpen) {
                $child.hide();
            } else if (childLength === $childField.eq(i).data('id').split('/').length) {
                if ($child.hasClass('show')) {
                    $child.removeClass('show');
                    $child.children('.o_expand_parent').removeClass('fa-chevron-down').addClass('fa-chevron-right');
                }
                $child.show();
            }
        }
    },
    /**
     * Fetches the saved export list for the current model
     *
     * @private
     * @returns {Deferred}
     */
    _showExportsList: function () {
        var self = this;
        if (this.$('.o_exported_lists_select').is(':hidden')) {
            this.$('.o_exported_lists').show();
            return Promise.resolve();
        }

        return this._rpc({
            model: 'ir.exports',
            method: 'search_read',
            fields: ['name'],
            domain: [['resource', '=', this.record.model]]
        }).then(function (exportList) {
            if (!exportList.length) {
                return;
            }
            self.$('.o_exported_lists').append(QWeb.render('Export.SavedList', {
                existing_exports: exportList,
            }));
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * This method will fill fields to export when user change exported field list
     *
     * @private
     */
    _onChangeExportList: function () {
        var self = this;
        this.$fieldsList.empty();
        var exportID = this.$('.o_exported_lists_select option:selected').val();
        if (exportID) {
            this._rpc({
                route: '/web/export/namelist',
                params: {
                    model: this.record.model,
                    export_id: parseInt(exportID, 10),
                },
            }).then(function (fieldList) {
                _.each(fieldList, function (field) {
                    self.$fieldsList.append(new Option(field.label, field.name));
                });
            });
        }
    },
    /**
     * @private
     * @returns {Deferred}
     */
    _onChangeCompatibleInput: function () {
        var self = this;
        this.isCompatibleMode = this.$('.o_import_compat input[value="yes"]').is(':checked');

        this.$('.o_field_tree_structure').remove();

        return this._rpc({
            route: '/web/export/get_fields',
            params: {
                model: this.record.model,
                import_compat: this.isCompatibleMode,
            },
        }).then(function (records) {
            var compatibleFields = _.map(records, function (record) { return record.id; });
            self.$fieldsList
                .find('option')
                .filter(function () {
                    var optionField = $(this).attr('value');
                    if (compatibleFields.indexOf(optionField) === -1) {
                        return true;
                    }
                })
                .remove();
            self._onShowData(records);
            // In compatible mode add ID field as first field to export
            if (self.isCompatibleMode) {
                self.$('.o_fields_list').prepend(new Option(_t("External ID"), 'id'));
            }
            _.each(records, function (record) {
                if (_.contains(self.defaultExportFields, record.id)) {
                    self._addField(record.id, record.string);
                }
            });
        });
    },
    /**
     * Add a field to export list
     *
     * @private
     */
    _onClickAddField: function () {
        var self = this;
        this.$('.o_field_tree_structure .o_selected')
            .removeClass('o_selected')
            .each(function () {
                var $this = $(this);
                self._addField($this.data('id'), $this.children('.o_tree_column').text());
            });
    },
    /**
     * Delete selected export list item from the saved export list
     *
     * @private
     */
    _onClickDeleteExportListBtn: function () {
        var self = this;
        var selectExp = this.$('.o_exported_lists_select option:selected');
        var options = {
            confirm_callback: function () {
                if (selectExp.val()) {
                    self.exports.unlink([parseInt(selectExp.val(), 10)]);
                    selectExp.remove();
                    self.$fieldsList.empty();
                    if (self.$('.o_exported_lists_select option').length <= 1) {
                        self.$('.o_exported_lists').hide();
                    }
                }
            }
        };
        Dialog.confirm(this, _t("Do you really want to delete this export template?"), options);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickExpand: function (ev) {
        this._onExpandAction(this.records[$(ev.target).closest('.o_export_tree_item').data('id')]);
    },
    /**
     * @private
     */
    _onClickMovedown: function () {
        var $selectedRows = this.$fieldsList.find('option:selected');
        var $nextRow = $selectedRows.last().next();
        if ($nextRow.length) {
            $nextRow.after($selectedRows.detach());
        }
    },
    /**
     * @private
     */
    _onClickMoveup: function () {
        var $selectedRows = this.$fieldsList.find('option:selected');
        var $prevRow = $selectedRows.first().prev();
        if ($prevRow.length) {
            $prevRow.before($selectedRows.detach());
        }
    },
    /**
     * Remove all fields from export field list
     *
     * @private
     */
    _onClickRemoveAllFields: function () {
        this.$fieldsList.empty();
    },
    /**
     * Remove selected field from export field list
     *
     * @private
     */
    _onClickRemoveField: function () {
        this.$fieldsList.find('option:selected').remove();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickSaveList: function (ev) {
        ev.preventDefault();

        var $saveList = this.$('.o_save_list');
        if ($saveList.is(':empty')) {
            $saveList.append(QWeb.render('Export.SaveList'));
        } else {
            if ($saveList.is(':hidden')) {
                $saveList.show();
                $saveList.find('.o_export_list_input').val('');
            } else {
                $saveList.hide();
            }
        }
    },
    /**
     * This method will create a record in 'ir.exports' model with list of
     * selected fields.
     *
     * @private
     */
    _onClickSaveListBtn: function () {
        var self = this;
        var $saveList = this.$('.o_save_list');

        var value = $saveList.find('input').val();
        if (!value) {
            Dialog.alert(this, _t("Please enter save field list name"));
            return;
        }

        var fields = this._getFields();
        if (fields.length === 0) {
            return;
        }

        $saveList.hide();

        this.exports.create({
            name: value,
            resource: this.record.model,
            export_fields: _.map(fields, function (field) {
                return [0, 0, { name: field }];
            }),
        }).then(function (exportListID) {
            if (!exportListID) {
                return;
            }
            var $select = self.$('.o_exported_lists_select');
            if ($select.length === 0 || $select.is(':hidden')) {
                self._showExportsList();
            }
            $select.append(new Option(value, exportListID));
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickTreeItem: function (ev) {
        ev.stopPropagation();
        var $elem = $(ev.currentTarget);

        var rowIndex = $elem.prevAll('.o_export_tree_item').length;
        var rowIndexLevel = $elem.parents('.o_export_tree_item').length;

        if (ev.shiftKey && rowIndexLevel === this.rowIndexLevel) {
            var minIndex = Math.min(rowIndex, this.rowIndex);
            var maxIndex = Math.max(rowIndex, this.rowIndex);

            this.$records.filter(function () { return ($elem.parent()[0] === $(this).parent()[0]); })
                .slice(minIndex, maxIndex + 1)
                .addClass('o_selected')
                .filter(':not(:last)')
                .each(processChildren);
        }

        this.rowIndex = rowIndex;
        this.rowIndexLevel = rowIndexLevel;

        if (ev.ctrlKey) {
            $elem.toggleClass('o_selected').focus();
        } else if (ev.shiftKey) {
            $elem.addClass('o_selected').focus();
        } else {
            this.$('.o_selected').removeClass('o_selected')
            $elem.addClass('o_selected').focus();
        }

        function processChildren() {
            var $child = $(this);
            if ($child.hasClass('show')) {
                $child.children('.o_export_tree_item')
                    .addClass('o_selected')
                    .each(processChildren);
            }
        }
    },
    /**
     * Add a field to export field list on double click
     *
     * @private
     * @param {Event} ev
     */
    _onDblclickTreeItem: function (ev) {
        var self = this;
        function addElement(el) {
            self._addField(el.getAttribute('data-id'), el.querySelector('.o_tree_column').textContent);
        }
        var target = ev.currentTarget;
        target.classList.remove('o_selected');
        // Add parent fields to export
        [].reverse.call($(target).parents('.o_export_tree_item')).each(function () {
            addElement(this);
        });
        // add field itself
        addElement(target);
    },
    /**
     * Handles the keyboard navigation for the fields
     *
     * @private
     * @param {Event} ev
     */
    _onKeydownTreeItem: function (ev) {
        ev.stopPropagation();
        var $el = $(ev.currentTarget);
        var record = this.records[$el.data('id')];

        switch (ev.keyCode || ev.which) {
            case $.ui.keyCode.LEFT:
                if ($el.hasClass('show')) {
                    this._onExpandAction(record);
                }
                break;
            case $.ui.keyCode.RIGHT:
                if (!$el.hasClass('show')) {
                    this._onExpandAction(record);
                }
                break;
            case $.ui.keyCode.UP:
                var $prev = $el.prev('.o_export_tree_item');
                if ($prev.length === 1) {
                    while ($prev.hasClass('show')) {
                        $prev = $prev.children('.o_export_tree_item').last();
                    }
                } else {
                    $prev = $el.parent('.o_export_tree_item');
                    if ($prev.length === 0) {
                        break;
                    }
                }

                $el.removeClass('o_selected').blur();
                $prev.addClass("o_selected").focus();
                break;
            case $.ui.keyCode.DOWN:
                var $next;
                if ($el.hasClass('show')) {
                    $next = $el.children('.o_export_tree_item').first();
                } else {
                    $next = $el.next('.o_export_tree_item');
                    if ($next.length === 0) {
                        $next = $el.parent('.o_export_tree_item').next('.o_export_tree_item');
                        if ($next.length === 0) {
                            break;
                        }
                    }
                }

                $el.removeClass('o_selected').blur();
                $next.addClass('o_selected').focus();
                break;
        }
    },
});

return DataExport;

});
