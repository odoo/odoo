odoo.define('base_import.import', function (require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var session = require('web.session');
var time = require('web.time');
var fieldUtils = require('web.field_utils');

var QWeb = core.qweb;
var _t = core._t;
var _lt = core._lt;
var StateMachine = window.StateMachine;

/**
 * Safari does not deal well at all with raw JSON data being
 * returned. As a result, we're going to cheat by using a
 * pseudo-jsonp: instead of getting JSON data in the iframe, we're
 * getting a ``script`` tag which consists of a function call and
 * the returned data (the json dump).
 *
 * The function is an auto-generated name bound to ``window``,
 * which calls back into the callback provided here.
 *
 * @param {Object} form the form element (DOM or jQuery) to use in the call
 * @param {Object} attributes jquery.form attributes object
 * @param {Function} callback function to call with the returned data
 */
function jsonp(form, attributes, callback) {
    attributes = attributes || {};
    var options = {jsonp: _.uniqueId('import_callback_')};
    window[options.jsonp] = function () {
        delete window[options.jsonp];
        callback.apply(null, arguments);
    };
    if ('data' in attributes) {
        _.extend(attributes.data, options);
    } else {
        _.extend(attributes, {data: options});
    }
    _.extend(attributes, {
        dataType: 'script',
    });
    $(form).ajaxSubmit(attributes);
}
function _make_option(term) { return {id: term, text: term }; }
function _from_data(data, term) {
    return _.findWhere(data, {id: term}) || _make_option(term);
}

/**
 * query returns a list of suggestion select2 objects, this function:
 *
 * * returns data exactly matching query by either id or text if those exist
 * * otherwise it returns a select2 option matching the term and any data
 *   option whose id or text matches (by substring)
 */
function dataFilteredQuery(q) {
    var suggestions = _.clone(this.data);
    if (q.term) {
        var exact = _.filter(suggestions, function (s) {
            return s.id === q.term || s.text === q.term;
        });
        if (exact.length) {
            suggestions = exact;
        } else {
            suggestions = [_make_option(q.term)].concat(_.filter(suggestions, function (s) {
                return s.id.indexOf(q.term) !== -1 || s.text.indexOf(q.term) !== -1
            }));
        }
    }
    q.callback({results: suggestions});
}

var DataImport = AbstractAction.extend({
    hasControlPanel: true,
    contentTemplate: 'ImportView',
    opts: [
        {name: 'encoding', label: _lt("Encoding:"), value: ''},
        {name: 'separator', label: _lt("Separator:"), value: ''},
        {name: 'quoting', label: _lt("Text Delimiter:"), value: '"'}
    ],
    spreadsheet_opts: [
        {name: 'sheet', label: _lt("Selected Sheet:"), value: ''},
    ],
    parse_opts_formats: [
        {name: 'date_format', label: _lt("Date Format:"), value: ''},
        {name: 'datetime_format', label: _lt("Datetime Format:"), value: ''},
    ],
    parse_opts_separators: [
        {name: 'float_thousand_separator', label: _lt("Thousands Separator:"), value: ','},
        {name: 'float_decimal_separator', label: _lt("Decimal Separator:"), value: '.'}
    ],
    events: {
        'change .oe_import_file': 'loaded_file',
        'change input.oe_import_has_header, .oe_import_sheet': 'settings_changed',
        'change input.oe_import_advanced_mode': function (e) {
            this.do_not_change_match = true;
            this['settings_changed']();
        },
        'click .oe_import_report a.oe_import_report_count': function (e) {
            e.preventDefault();
            $(e.target).parent().find('i.arrow').toggleClass('up down');
            $(e.target).parent().parent().toggleClass('oe_import_report_showmore');
        },
        'click .oe_import_report_see_possible_value': function (e) {
            e.preventDefault();
            $(e.target).parent().toggleClass('oe_import_report_showmore');
        },
        'click .oe_import_moreinfo_action a': function (e) {
            e.preventDefault();
            // #data will parse the attribute on its own, we don't like
            // that sort of things
            var action = JSON.parse($(e.target).attr('data-action'));
            // FIXME: when JS-side clean_action
            action.views = _(action.views).map(function (view) {
                var id = view[0], type = view[1];
                return [
                    id,
                    type !== 'tree' ? type
                      : action.view_type === 'form' ? 'list'
                      : 'tree'
                ];
            });
            this.do_action(_.extend(action, {
                target: 'new',
            }));
        },
    },
    init: function (parent, action) {
        this._super.apply(this, arguments);
        this.action_manager = parent;
        this.res_model = action.params.model;
        this.parent_context = action.params.context || {};
        // import object id
        this.id = null;
        this.session = session;
        this._title = action.name || _t('Import a File'); // Displayed in the breadcrumbs
        this.do_not_change_match = false;
        this.sheets = [];
        this.selectionFields = {};  // Used to compute fallback values in backend.
    },
    /**
     * @override
     */
    willStart: function () {
        var self = this;
        var def = this._rpc({
            model: this.res_model,
            method: 'get_import_templates',
            context: this.parent_context,
        }).then(function (result) {
            self.importTemplates = result;
        });
        return Promise.all([this._super.apply(this, arguments), def]);
    },
    start: function () {
        var self = this;
        this.$form = this.$('form');
        this.setup_encoding_picker();
        this.setup_separator_picker();
        this.setup_float_format_picker();
        this.setup_date_format_picker();
        this.setup_sheets_picker();
        this.renderButtons();
        this.controlPanelProps.cp_content = { $buttons: this.$buttons };

        return Promise.all([
            this._super(),
            self.create_model().then(function (id) {
                self.id = id;
                self.$('input[name=import_id]').val(id);
            }),
        ]);
    },
    create_model: function() {
        return this._rpc({
                model: 'base_import.import',
                method: 'create',
                args: [{res_model: this.res_model}],
                kwargs: {context: session.user_context},
            });
    },
    renderButtons: function() {
        var self = this;
        this.$buttons = $(QWeb.render("ImportView.buttons", this));
        this.$buttons.filter('.o_import_validate').on('click', this.validate.bind(this));
        this.$buttons.filter('.o_import_import').on('click', this.import.bind(this));
        this.$buttons.filter('.oe_import_file').on('click', function () {
            self.$('.o_content .oe_import_file').click();
        });
        this.$buttons.filter('.o_import_cancel').on('click', function(e) {
            e.preventDefault();
            self.exit();
        });
    },
    setup_encoding_picker: function () {
        this.$('input.oe_import_encoding').select2({
            width: '50%',
            data: _.map(('utf-8 utf-16 windows-1252 latin1 latin2 big5 gb18030 shift_jis windows-1251 koi8_r').split(/\s+/), _make_option),
            query: dataFilteredQuery,
            minimumResultsForSearch: -1,
            initSelection: function ($e, c) {
                return c(_make_option($e.val()));
            }
        });
    },
    setup_separator_picker: function () {
        var data = [
            {id: ',', text: _t("Comma")},
            {id: ';', text: _t("Semicolon")},
            {id: '\t', text: _t("Tab")},
            {id: ' ', text: _t("Space")}
        ];
        this.$('input.oe_import_separator').select2({
            width: '50%',
            data: data,
            query: dataFilteredQuery,
            minimumResultsForSearch: -1,
            // this is not provided to initSelection so can't use this.data
            initSelection: function ($e, c) {
                c(_from_data(data, $e.val()) || _make_option($e.val()))
            }
        });
    },
    setup_float_format_picker: function () {
        var data_decimal = [
            {id: ',', text: _t("Comma")},
            {id: '.', text: _t("Dot")},
        ];
        var data_digits = data_decimal.concat([{id: '', text: _t("No Separator")}]);
        this.$('input.oe_import_float_thousand_separator').select2({
            width: '50%',
            data: data_digits,
            query: dataFilteredQuery,
            minimumResultsForSearch: -1,
            initSelection: function ($e, c) {
                c(_from_data(data_digits, $e.val()) || _make_option($e.val()))
            }
        });
        this.$('input.oe_import_float_decimal_separator').select2({
            width: '50%',
            data: data_decimal,
            query: dataFilteredQuery,
            minimumResultsForSearch: -1,
            initSelection: function ($e, c) {
                c(_from_data(data_decimal, $e.val()) || _make_option($e.val()))
            }
        });
    },
    setup_date_format_picker: function () {
        var data = _([
            'YYYY-MM-DD',
            'DD/MM/YY',
            'DD/MM/YYYY',
            'DD-MM-YYYY',
            'DD-MMM-YY',
            'DD-MMM-YYYY',
            'DD.MM.YY',
            'DD.MM.YYYY',
            'MM/DD/YY',
            'MM/DD/YYYY',
            'MM-DD-YY',
            'MM-DD-YYYY',
            'DDMMYY',
            'DDMMYYYY',
            'YYMMDD',
            'YYYYMMDD',
            'YY/MM/DD',
            'YYYY/MM/DD',
            'MMDDYY',
            'MMDDYYYY',
        ]).map(_make_option);
        this.$('input.oe_import_date_format').select2({
            width: '50%',
            data: data,
            query: dataFilteredQuery,
            minimumResultsForSearch: -1,
            initSelection: function ($e, c) {
                c(_from_data(data, $e.val()) || _make_option($e.val()));
            }
        })
    },
    setup_sheets_picker: function () {
        var data = this.sheets.map(_make_option);
        this.$('input.oe_import_sheet').select2({
            width: '100%',
            data: data,
            query: dataFilteredQuery,
            minimumResultsForSearch: -1,
            initSelection: function ($e, c) {
                c(_from_data(data, $e.val()) || _make_option($e.val()))
            },
        });
    },

    import_options: function () {
        var self = this;
        var options = {
            has_headers: this.$('input.oe_import_has_header').prop('checked'),
            advanced: this.$('input.oe_import_advanced_mode').prop('checked'),
            keep_matches: this.do_not_change_match,
            name_create_enabled_fields: {},
            import_set_empty_fields: [],
            import_skip_records: [],
            fallback_values: {},
            // start at row 1 = skip 0 lines
            skip: Number(this.$('#oe_import_row_start').val()) - 1 || 0,
            limit: Number(this.$('#oe_import_batch_limit').val()) || null,
        };
        _.each(_.union(this.opts, this.spreadsheet_opts), function (opt) {
            options[opt.name] =
                self.$('input.oe_import_' + opt.name).val();
        });
        _(this.parse_opts_formats).each(function (opt) {
            options[opt.name] = time.moment_to_strftime_format(self.$('input.oe_import_' + opt.name).val());
        });
        _(this.parse_opts_separators).each(function (opt) {
            options[opt.name] = self.$('input.oe_import_' + opt.name).val();
        });

        options['fields'] = [];
        if (this.do_not_change_match) {
            options['fields'] = this.$('input.oe_import_match_field').map(function (index, el) {
                return $(el).select2('val') || false;
            }).get();
        }
        this.do_not_change_match = false;
        this.$('select.o_import_create_option').each(function () {
            var field = this.getAttribute('field');
            var type = this.getAttribute('type');
            if (field) {
                if (['boolean', 'many2one', 'many2many', 'selection'].includes(type) && this.value === 'skip_record') {
                    options.import_skip_records.push(field);
                } else if (['many2one', "many2many", "selection"].includes(type)) {
                    if (this.value === 'set_empty') {
                        options.import_set_empty_fields.push(field);
                    } else {
                        options.name_create_enabled_fields[field] = this.value === 'create';
                    }
                // for selection, include also 'skip' that will be interpreted as 'None' in backend.
                } else if (['boolean','selection'].includes(type) && this.value !== 'prevent') {
                    options.fallback_values[field] = {
                        fallback_value: this.value,
                        field_model: this.getAttribute('model'),
                        field_type: type
                    };
                }
            }
        });
        return options;
    },

    //- File & settings change section
    onfile_loaded: function (event, from, to, arg) {
        // arg is null if reload -> don't reset partial import
        if (arg != null ) {
            var savedSkipLines = 0;
            var isPartialEnabled = this.$('.oe_import').hasClass('o_import_partial_mode');
            if (isPartialEnabled) {
                savedSkipLines = this.$('#oe_import_row_start').val();
            }
            this.toggle_partial(null);
            if (isPartialEnabled && savedSkipLines) {
                // If partial mode was already enabled, we want to keep the 'start at line' parameter
                // This can help the end user when he has partially imported a file and wants to make
                // some modifications into it before re-uploading and resuming the upload.
                this.$('#oe_import_row_start').val(savedSkipLines);
            }
        }

        this.$buttons.filter('.o_import_import, .o_import_validate').addClass('d-none');
        if (!this.$('input.oe_import_file').val()) { return this['settings_changed'](); }
        this.$('.oe_import_date_format').select2('val', '');
        this.$('.oe_import_datetime_format').val('');
        this.$('.oe_import_sheet').val('');

        this.$form.removeClass('oe_import_preview oe_import_error');
        var file = this.$('input.oe_import_file')[0].files[0];
        // some platforms send text/csv, application/csv, or other things if Excel is prevent
        var isCSV = ((file.type && _.last(file.type.split('/')) === "csv") || ( _.last(file.name.split('.')) === "csv"))
        this.$form.find('.o_import_formatting').toggleClass('d-none', !isCSV);

        // get file name and extension separately, to apply ellipsis to the name and still keep the extension visible.
        // E.g. : superLongFileName.csv -> "superLongFi....csv" instead of "superLongFileNa..."
        var fileName = file.name.split('.');
        var fileExtension = fileName.pop();
        fileName = fileName.join('.');
        this.$('#oe_imported_file').text(fileName);
        this.$('#oe_imported_file_extension').text('.' + fileExtension);

        this.$form.find('.oe_import_box').toggle(true);
        jsonp(this.$form, {
            url: '/base_import/set_file'
        }, this.proxy('settings_changed'));
    },
    onpreviewing: function () {
        var self = this;
        this.$buttons.filter('.o_import_import, .o_import_validate').addClass('d-none');
        this.$form.addClass('oe_import_with_file');
        // TODO: test that write // succeeded?
        this.$form.removeClass('oe_import_preview_error oe_import_error');
        this.$form.toggleClass(
            'oe_import_noheaders',
            !this.$('input.oe_import_has_header').prop('checked'));

        // Clear the input value to allow onchange to be triggered
        // if the file is the same (for all browsers)
        this.$('input.oe_import_file').val('');
        this.$('.oe_import_options_cell,.oe_import_options_header').addClass('d-none');

        this._cleanComments();

        // Block UI during loading file.
        $.blockUI({message: QWeb.render('Throbber')});
        $(document.body).addClass('o_ui_blocked');
        $('.oe_throbber_message').text(_t("Loading file..."));

        this._rpc({
                model: 'base_import.import',
                method: 'parse_preview',
                args: [this.id, this.import_options()],
                kwargs: {context: session.user_context},
            }).then(function (result) {
                var signal = result.error ? 'preview_failed' : 'preview_succeeded';
                self[signal](result);
                $(document.body).removeClass('o_ui_blocked');
                $.unblockUI();
            });
    },
    onpreview_error: function (event, from, to, result) {
        this.$('.oe_import_options').show();
        this.$form.addClass('oe_import_preview_error oe_import_error');
        this.$form.find('.oe_import_box, .oe_import_with_file').removeClass('d-none');
        this.$form.find('.o_view_nocontent').addClass('d-none');
        this.$('.oe_import_error_report').html(
                QWeb.render('ImportView.preview.error', result));
    },
    onpreview_success: function (event, from, to, result) {
        var self = this;
        this.$buttons.filter('.oe_import_file')
            .text(_t('Load File'))
            .removeClass('btn-primary').addClass('btn-secondary')
            .blur();
        this.$buttons.filter('.o_import_import, .o_import_validate').removeClass('d-none');
        this.$form.find('.oe_import_box, .oe_import_with_file').removeClass('d-none');
        this.$form.find('.o_view_nocontent').addClass('d-none');
        this.$form.addClass('oe_import_preview');
        this.$('input.oe_import_advanced_mode').prop('checked', result.advanced_mode);
        this.$('.oe_import_grid').html(QWeb.render('ImportView.preview', result));
        this.$('.oe_import_grid .o_import_preview').each((index, element) => {
            $(element).popover({
                title: _t("Preview"),
                trigger: 'hover',
                html: true,
                content: QWeb.render('ImportView.preview_popover', { preview: result.preview[index] }),
            });
        });
        // Activate the batch configuration panel only of the file length > 100. (In order to let the user choose
        // the batch size even for medium size file. Could be useful to reduce the batch size for complex models).
        this.fileLength = result.file_length;
        this.$('.o_import_batch').toggleClass('d-none', !(this.fileLength > 100));
        this.$('.o_import_batch_alert').toggleClass('d-none', !result.batch);

        var messages = [];
        if (result.headers.length === 1) {
            messages.push({type: 'warning', message: _t("A single column was found in the file, this often means the file separator is incorrect")});
        }

        if (!_.isEmpty(messages)) {
            this.$('.oe_import_options').show();
            this.onresults(null, null, null, {'messages': messages});
        }

        if (!_.isEqual(this.sheets, result.options.sheets)) {
            this.sheets = result.options.sheets || [];
            this.setup_sheets_picker();
        }
        this.$('div.oe_import_has_multiple_sheets').toggle(
            this.sheets.length > 1
        );

        // merge option values back in case they were updated/guessed
        _.each(['encoding', 'separator', 'float_thousand_separator', 'float_decimal_separator', 'sheet'], function (id) {
            self.$('.oe_import_' + id).select2('val', result.options[id])
        });
        this.$('.oe_import_date_format').select2('val', time.strftime_to_moment_format(result.options.date_format));
        this.$('.oe_import_datetime_format').val(time.strftime_to_moment_format(result.options.datetime_format));
        // hide all "true debug" options when not in debug mode
        this.$('.oe_import_debug_option').toggleClass('d-none', !result.debug);

        var $fields = this.$('.oe_import_match_field');
        this.render_fields_matches(result, $fields);
        var data = this._generate_fields_completion(result);
        var item_finder = function (id, items) {
            items = items || data;
            for (var i=0; i < items.length; ++i) {
                var item = items[i];
                if (item.id === id) {
                    return item;
                }
                var val;
                if (item.children && (val = item_finder(id, item.children))) {
                    return val;
                }
            }
            return '';
        };
        $fields.each(function (k,v) {
            var $fieldInput = $(v);
            var filteredData = self._generate_fields_completion(result, k);

            var updateFieldInformation = function (fieldInfo) {
                // Get the comment cell on the same row in the table.
                var $commentCell = $fieldInput.closest('tr.oe_import_grid-row').find('.oe_import_comment_cell');
                var $optionsDiv = $commentCell.find('.oe_import_options_div');
                var isRelational = fieldInfo.type === 'many2many' || fieldInfo.type === 'many2one';
                var setEmpty = !fieldInfo.required && (isRelational || fieldInfo.type === 'selection');

                // if relational field is child of one2many then do not display skip record option
                var isO2MField = false;
                if (isRelational && fieldInfo.id.includes('/')) {
                    var fieldName = fieldInfo.id.split('/')[0];
                    var field = result.fields.find((field) => field.name === fieldName);
                    if (field && field.type === 'one2many') {
                        isO2MField = true;
                    }
                }
                var showSkipRecord = setEmpty && !isO2MField || (!fieldInfo.required && fieldInfo.type === 'boolean');

                // get options cell related to that field
                if (isRelational || fieldInfo.type === 'boolean') {
                    $optionsDiv.empty();
                    $optionsDiv.append(
                        QWeb.render('ImportView.create_record_option', {
                            data: fieldInfo,
                            is_relational: isRelational,
                            set_empty: setEmpty,
                            show_skip_record: showSkipRecord
                        })
                    );
                } else if (fieldInfo.type === 'selection') {
                    self._rpc({
                        model: fieldInfo.comodel_name || fieldInfo.model_name,
                        method: 'fields_get',
                    }).then(function (values) {
                        var selectionField = fieldInfo.id.split('/').pop();
                        var selectionLabels = values[selectionField]["selection"].map(value => value[1]);

                        $optionsDiv.empty();
                        $optionsDiv.append(
                            QWeb.render('ImportView.create_record_option', {
                                data: fieldInfo,
                                values: selectionLabels,
                                set_empty: setEmpty,
                                show_skip_record: showSkipRecord
                            })
                        );
                        self.selectionFields[data.id] = values;
                    });
                } else if ($optionsDiv.find('.o_import_create_option').length == 1) {
                    $optionsDiv.empty();
                }

                // re-attribute comment cell to the new selected field
                $commentCell.attr('field', fieldInfo.id || "");
                $commentCell.attr('model', fieldInfo.comodel_name || fieldInfo.model_name || "");

                // assign class for field icon
                var $fieldDropdown = $fieldInput.closest('.oe_import_match_cell').find('.select2-choice');
                var oldType = $fieldDropdown.getAttributes()['type'];
                $fieldDropdown.removeClass(`o_import_field_${oldType}`).addClass(`o_import_field_icon o_import_field_${fieldInfo.type}`);
                $fieldDropdown.attr('type', fieldInfo.type);
            };

            var default_value = $fieldInput.val();
            var fieldInfo = item_finder(default_value);
            if (!fieldInfo) {
                $fieldInput.val('');
            }

            $fieldInput.select2({
                allowClear: true,
                minimumInputLength: 0,
                data: filteredData,
                initSelection: function (element, callback) {
                    if (!default_value) {
                        callback('');
                        return;
                    }

                    updateFieldInformation(fieldInfo);
                    callback(fieldInfo);
                    self._handleMappingComments(v, fieldInfo);
                },
                // Format the tooltip.
                formatSelection: function (object, container) {
                    var fieldTooltipString = `%(label)s: %(labelValue)s
%(name)s: %(nameValue)s
%(type)s: %(typeValue)s
%(model)s: %(modelValue)s`;
                    var tooltip = _.str.sprintf(fieldTooltipString, {
                        'label': _t("Label"), 'labelValue': object.text,
                        'name': _t("Name"), 'nameValue': object.id,
                        'type': _t("Type"), 'typeValue': object.type,
                        'model': _t("Model"), 'modelValue': object.comodel_name || object.model_name,
                    });
                    $(container[0]).closest('a').attr('title', tooltip);
                    return object.text;
                },
                // For each choice, if field is required, make it bold in the list
                formatResultCssClass: function (object) {
                    if (object.required) { return "fw-bold text-decoration-underline"; }
                    return "";
                },
                placeholder: _t('To import, select a field...'),
                width: 'resolve',
                dropdownCssClass: 'oe_import_selector'
            }).on('change', function (event) {
                var changedField = event.currentTarget;
                var fieldRemovedId = event.removed ? event.removed.id : false;
                self._cleanFieldComments(changedField, fieldRemovedId);

                var fieldInfo = item_finder(changedField.value);
                updateFieldInformation(fieldInfo);
                self._handleMappingComments(changedField, fieldInfo);

                if (!event.val) {
                    var $matchingCell = $(changedField).closest('.oe_import_match_cell')
                    $matchingCell.find('.o_import_field_icon').removeClass('o_import_field_icon');
                    $matchingCell.find('a.select2-choice').removeAttr("title");
                }
            });

            $fieldInput.closest('.oe_import_match_cell').find('.select2-input').attr('placeholder', _t('Search for a field...'));
        });
    },

    /**
    * This method is called when changing the field to map with a file column, or when removing it.
    * It will clean the eventual comments, errors and the mapping options related to the previously selected field.
    *
    * @private
    */
    _cleanFieldComments: function (changedField, fieldRemovedId) {
        // Check that the column was not mapped to same field than another column
        if (fieldRemovedId) {
            var $sameMappedFields = this.$(`.oe_import_comment_cell[field=\"${fieldRemovedId}\"]`).find('.oe_import_same_mapped_field');
            if ($sameMappedFields.length == 2) {
                // remove all same mapped field comments
                $sameMappedFields.remove();
            }
        }
        // remove all comments for this header-field mapping row
        var $fieldRow = $(changedField).closest('tr.oe_import_grid-row');
        $fieldRow.find('.oe_import_comments_div').empty();
        $fieldRow.find('.oe_import_options_div').addClass("d-none");
    },

    /**
    * This method is called when selecting a sheet or a new file to import, but also when running to import or the
    * import test. It will remove all the general comments and/or field specific warnings and errors
    *
    * @private
    */
    _cleanComments: function () {
        this.$('.oe_import_error_report').empty();
        this.$('.oe_import_comments_div').find('.alert-error,.alert-warning').remove();
        this.$form.removeClass('oe_import_error');
    },

    /**
     * Called at the start of every batch to update the progress bar display.
     * It also computes an estimated time left based on: starting time of the whole process,
     * percentage done so far and remaining records.
     */
    _onBatchStart: function () {
        var recordsDone = this.batchSize * (this.currentBatchNumber - 1);
        var percentage = parseInt(recordsDone / this.totalToImport * 100);
        $('.o_import_progress_dialog')
            .find('.progress-bar')
            .text(percentage + "%")
            .attr('aria-valuenow', percentage)
            .css('width', percentage + '%');
        $('.o_import_progress_dialog')
            .find('.o_import_progress_dialog_batch_count')
            .text(this.currentBatchNumber);
        if (percentage !== 0) {
            // e.g: it took 1 seconds (1000 millis) to import 33%
            // -> there is (1000) * ((100 - 33) / 33) / 60000 minutes left
            // -> 1000 * (66 / 33) / 60000 -> 2000 / 60000 -> 0.03 minute left (2 seconds) left
            var estimatedTimeLeftMinutes = ((Date.now() - this.importStartTime) * ((100 - percentage) / percentage)) / 60000;
            $('.o_import_progress_dialog_time_left').removeClass('d-none');
            $('.o_import_progress_dialog_time_left_text')
                .text(fieldUtils.format.float_time(estimatedTimeLeftMinutes));
        }
    },

    /**
     * Called when the user manually interrupts the import during a batched import.
     * Sets 'stopImport' to true, which will stop the process when the current batch is done.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onStopImport: function (event) {
        var $currentTarget = $(event.currentTarget);
        $currentTarget.enable(false);
        $currentTarget
            .closest('.o_import_progress_dialog')
            .find('.o_import_progress_dialog_stop, .o_import_progress_dialog_batch')
            .toggleClass('d-none');
        this.stopImport = true;
    },

   /**
    * This method is called when selecting a new mapping field, or when changing/removing an already selected mapping
    * field. It will check if multiple field columns are/were mapped on the same field.
    * 1. In case the field type is char or text:
    *   This method will display / remove the comments informing the user that two columns content will be
    *   concatenated on the field they have chosen.
    * 2. Else:
    *  This method will remove the field mapping from the old column, as each field, except for the case 1., can only
    *  be mapped once.
    *
    * @private
    */
    _handleMappingComments: function (changedField, fieldInfo) {
        // check if two columns are mapped on the same fields (for char/text fields)
        var commentsToAdd = [];
        var $sameMappedFields = this.$('.oe_import_comment_cell[field="' + fieldInfo.id + '"]');

        if (fieldInfo.type == 'many2many') {
            commentsToAdd.push(QWeb.render('ImportView.comment_m2m_field'));
        }
        if ($sameMappedFields.length >= 2) {
            if (['char', 'text', "many2many"].includes(fieldInfo.type)) {
                commentsToAdd.push(QWeb.render('ImportView.comment_same_mapped_field', {
                    field: fieldInfo.text,
                }));
            } else {  // if column is mapped on an already mapped field, remove that field from the old column.
                var $targetMappedFieldId = $(changedField).parent().find('div.oe_import_match_field').getAttributes()['id'];
                _.each($sameMappedFields, function(fieldComment) {
                    var $mappingCell = $(fieldComment).parent().find('div.oe_import_match_field');
                    if ($mappingCell.getAttributes()['id'] !== $targetMappedFieldId) {
                        $mappingCell.find('.select2-search-choice-close').trigger('mousedown').trigger('click');
                    }
                });
            }
        }

        var $commentDiv = $sameMappedFields.find(".oe_import_comments_div");
        $commentDiv.empty();
        _.each($commentDiv, function(fieldComment) {
            _.each(commentsToAdd, function(comment) {
                $(fieldComment).append(comment);
            });
        });
    },

    _generate_fields_completion: function (root, index) {
        var self = this;
        var basic = [];
        var regulars = [];
        var o2m = [];
        var suggested = [];
        var header_types = root.header_types;
        function traverse(field, ancestors, collection, type) {
            var subfields = field.fields;
            var advanced_mode = self.$('input.oe_import_advanced_mode').prop('checked');
            var field_path = ancestors.concat(field);
            var label = _(field_path).pluck('string').join(' / ');
            var id = _(field_path).pluck('name').join('/');
            // If non-relational, m2o or m2m, collection is either suggested if field type is in header_types, either regulars if type does not match
            if (!collection) {
                if (field.name === 'id') {
                    collection = basic;
                } else if (_.isEmpty(subfields)
                        || _.isEqual(_.pluck(subfields, 'name'), ['id', '.id'])) {
                    collection = (type && type.indexOf(field['type']) !== -1) ? suggested : regulars;
                } else {
                    collection = o2m;
                }
            }

            collection.push({
                id: id,
                text: label,
                required: field.required,
                type: field.type,
                default_value: field.default_value,
                comodel_name: field.comodel_name,
                model_name: field.model_name,
            });

            if (advanced_mode){
                for(var i=0, end=subfields.length; i<end; ++i) {
                    traverse(subfields[i], field_path, collection, type);
                }
            }
        }
        _(root.fields).each(function (field) {
            if (index === undefined) {
                traverse(field, []);
            }
            else {
                if (self.$('input.oe_import_advanced_mode').prop('checked')){
                    traverse(field, [], undefined, ['all']);
                }
                else {
                    traverse(field, [], undefined, header_types[index]);
                }
            }
        });

        var cmp = function (field1, field2) {
            return field1.text.localeCompare(field2.text);

        };
        suggested.sort(cmp);
        regulars.sort(cmp);
        o2m.sort(cmp);
        if (!_.isEmpty(regulars) && !_.isEmpty(o2m)){
            if (!_.isEmpty(suggested)) {
                basic = basic.concat({ text: _t("Suggested Fields"), children: suggested });
            }
            return basic.concat([
                { text: !_.isEmpty(suggested) ? _t("Additional Fields") : _t("Standard Fields"), children: regulars },
                { text: _t("Relation Fields"), children: o2m },
            ]);
        } else {
            return basic.concat(suggested, regulars, o2m);
        }
    },
    render_fields_matches: function (result, $fields) {
        if (_(result.matches).isEmpty()) { return; }
        $fields.each(function (index, input) {
            var match = result.matches[index];
            if (!match) { return; }

            var current_field = result;
            input.value = _(match).chain()
                .map(function (name) {
                    // WARNING: does both mapping and folding (over the
                    //          ``field`` iterator variable)
                    return current_field = _(current_field.fields).find(function (subfield) {
                        return subfield.name === name;
                    });
                })
                .pluck('name')
                .value()
                .join('/');
        });
    },

    //- import itself
    call_import: function (kwargs) {
        var fields = this.$('input.oe_import_match_field').map(function (index, el) {
            return $(el).select2('val') || false;
        }).get();
        var columns = this.$('.o_import_header_name').map(function () {
            return $(this).text().trim().toLowerCase() || false;
        }).get();

        var tracking_disable = 'tracking_disable' in kwargs ? kwargs.tracking_disable : !this.$('#oe_import_tracking').prop('checked');
        delete kwargs.tracking_disable;
        kwargs.context = _.extend(
            {}, this.parent_context,
            {tracking_disable: tracking_disable}
        );

        this.importStartTime = Date.now();
        this.stopImport = false;
        this.totalToImport = this.fileLength - parseInt(this.$('#oe_import_row_start').val());
        this.batchSize = parseInt(this.$('#oe_import_batch_limit').val() || 0);
        var isBatch = this.batchSize !== 0 && this.totalToImport > this.batchSize;
        var totalSteps = isBatch ? Math.floor(this.totalToImport / this.batchSize) + 1 : 1;
        this.currentBatchNumber = 1;

        $.blockUI({
            message: QWeb.render(
                'base_import.progressDialog', {
                    importMode: kwargs.dryrun ? _t('Testing') : _t('Importing'),
                    isBatch: isBatch,
                    totalSteps: totalSteps,
                }
            )
        });
        $(document.body).addClass('o_ui_blocked');

        $('.o_import_progress_dialog')
            .find('.o_progress_stop_import')
            .on('click', this._onStopImport.bind(this));

        var opts = this.import_options();

        return this._batchedImport(opts, [this.id, fields, columns], kwargs, {done: 0, prev: 0})
            .then(null, function (reason) {
                var error = reason.message;
                var event = reason.event;
                // In case of unexpected exception, convert
                // "JSON-RPC error" to an import failure, and
                // prevent default handling (warning dialog)
                if (event) { event.preventDefault(); }

                var errordata = error.data || {};
                const msg = errordata.arguments && (errordata.arguments[1] || errordata.arguments[0])
                    || error.message || _t("An unknown issue occurred during import (possibly lost connection, data limit exceeded or memory limits exceeded). Please retry in case the issue is transient. If the issue still occurs, try to split the file rather than import it at once.");

                return Promise.resolve({'messages': [{
                    type: 'error',
                    record: false,
                    message: msg,
                }]});
            }).finally(function () {
                $(document.body).removeClass('o_ui_blocked');
                $.unblockUI();
            });
    }, /**
     *
     * @param opts import options
     * @param args positional arguments to pass along (augmented with the options)
     * @param kwargs keyword arguments to pass along (directly)
     * @param {Object} rec recursion information record
     * @param {Number} rec.done how many records have been loaded so far
     * @param {Number} rec.prev nextrow of the previous call so we can know
     *                          how many rows the call we're here performing
     *                          will have consumed, and thus by how much we
     *                          need to offset the messages of the *next* call
     * @returns {Promise<{name, ids, messages}>}
     * @private
     */
    _batchedImport: function (opts, args, kwargs, rec) {
        var self = this;
        opts.callback && opts.callback(this);
        this._onBatchStart();
        this.currentBatchNumber += 1;

        if (this.stopImport) {
            $(document.body).removeClass('o_ui_blocked');
            $.unblockUI();
            return Promise.resolve({});
        }

        return this._rpc({
            model: 'base_import.import',
            method: 'execute_import',
            args: args.concat([opts]),
            kwargs: kwargs
        }, {
            shadow: true,
        }).then(function (results) {
            _.each(results.messages, offset_by(opts.skip));
            if (!kwargs.dryrun && !results.ids) {
                // update skip to failed batch
                self.$('#oe_import_row_start').val(opts.skip + 1);
                if (opts.skip) {
                    // there's been an error during a "proper" import, stop & warn
                    // about partial import maybe
                    results.messages.push({
                        type: 'info',
                        priority: true,
                        message: _.str.sprintf(_t("This file has been successfully imported up to line %d."), opts.skip)
                    });
                }
                return results;
            }
            if (!results.nextrow) {
                // we're done
                return results;
            }

            // do the next batch
            return self._batchedImport(
                // avoid modifying opts in-place
                _.defaults({skip: results.nextrow}, opts),
                args, kwargs, {
                    done: rec.done + (results.ids || []).length,
                    prev: results.nextrow
                }
            ).then(function (r2) {
                return {
                    name: _.zip(results.name, r2.name).map(function (names) {
                        return names[0] || names[1];
                    }),
                    ids: (results.ids || []).concat(r2.ids || []),
                    messages: r2.messages ? results.messages.concat(r2.messages) : results.messages,
                    skip: r2.skip || results.nextrow,
                    nextrow: r2.nextrow
                }
            });
        });
    },
    onvalidate: function () {
        var prom = this.call_import({ dryrun: true, tracking_disable: true });
        prom.then(this.proxy('validated'));
        return prom;
    },
    onimport: function () {
        var self = this;
        var prom = this.call_import({ dryrun: false });
        prom.then(function (results) {
            if (self.stopImport) {
                var recordsImported = results.ids ? results.ids.length : 0;
                if (recordsImported) {
                    self.$('#oe_import_row_start').val((results.skip || 0) + 1);
                    self.displayNotification({ message: _.str.sprintf(
                        _t("%d records successfully imported"),
                        recordsImported
                    )});
                }
                self['import_interrupted'](results);
            } else if (!_.any(results.messages, function (message) {
                    return message.type === 'error'; })) {
                self['import_succeeded'](results);
                return;
            }
            self['import_failed'](results);
        });
        return prom;
    },
    onimported: function (event, from, to, results) {
        this.displayNotification({ message: _.str.sprintf(
            _t("%d records successfully imported"),
            results.ids.length
        ) });
        this.exit();
    },
    exit: function () {
        this.trigger_up('history_back');
    },
    onresults: function (event, from, to, results) {
        var self = this;
        var fields = this.$('input.oe_import_match_field').map(function (index, el) {
            return $(el).select2('val') || false;
        }).get();

        var error_type = "warning";
        var errorMessages = results.messages;

        if (_.isEmpty(errorMessages) && event !== 'import_interrupted') {
            errorMessages.push({
                type: 'info',
                message: _t("Everything seems valid.")
            });
            error_type = false;
        } else if (event === 'import_interrupted' && results.ids) {
            this.toggle_partial(results);
            error_type = false;
        } else if (event === 'import_failed' && results.ids) {
            // both ids in a failed import -> partial import
            this.toggle_partial(results);
        }

        // row indexes come back 0-indexed, spreadsheets
        // display 1-indexed.
        var offset = 1;
        // offset more if header
        if (this.import_options().has_headers) { offset += 1; }

        // Sort errors by error gravity then by field
        var errorsSorted = _.sortBy(_(errorMessages).groupBy('message'), function (group) {
            if (group[0].priority){
                return -2;
            }

            // sort by gravity, then, order of field in list
            var order = 0;
            switch (group[0].type) {
            case 'error': order = 0; error_type = 'error'; break;
            case 'warning': order = fields.length + 1; break;
            case 'info': order = 2 * (fields.length + 1); break;
            default: order = 3 * (fields.length + 1); break;
            }
            return order + _.indexOf(fields, group[0].field);
        });

        // regroup errors by field
        var errorsByFields = this._regroupErrorsByFields(errorsSorted);

        // If no general comments (index "0"), add general warning that there are some errors/warnings
        if (!errorsByFields[0] && error_type) {
            var message = error_type === "warning" ?
                _t("The file contains non-blocking warnings (see below)") :
                _t("The file contains blocking errors (see below)");
            errorsByFields[0] = [{
                'type': error_type,
                'message': message,
            }];
        }

        // Clean old comments
        self._cleanComments();

        // Add new comments
        _.each(errorsByFields, function (errors, field) {
            var $errorCell = self.$('.oe_import_comment_cell[field="'+ field +'"]');
            var $errorDiv = $errorCell.find(".oe_import_comments_div");
            var errorTemplate = 'ImportView.fieldError';
            // If error not linked to a targeted Odoo field, show in global error div
            if ($errorDiv.length === 0) {
                $errorDiv = self.$('.oe_import_error_report');
                self.$form.addClass('oe_import_error');
                field = 0;
                errorTemplate = 'ImportView.error';
            }
            $errorDiv.append(
                QWeb.render(errorTemplate, {
                    errors: errors,
                    field: field,
                    result_names: results.name,
                    offset: offset,
                })
            );
            var mainError = errors[0];
            if (!mainError.not_matching_error && mainError.type === "error") {
                $errorCell.find(".oe_import_options_div").removeClass('d-none');
            }
        });
    },

    /**
    * This method regroups the errors by their 'field' key.
    * Errors of same nature encountered on multiple rows for the same field are regrouped into the same unique error
    * and rows_from and rows_to are adapted accordingly.
    * The goal is to ease the error attribution by looping through each mapped field and add their corresponding errors
    * to the comment cell of that mapped field.
    * Some errors are not linked to a mapped field and will be displayed in the general error container.
    * Those general errors will be identified with key "0".
    *
    * @private
    * @param {Array} errorsSorted: list of errors sorted by error gravity, then by field.
    *   Each item of the list is a list of error of the same nature and can be therefore composed of 1 or more errors.
    *   E.g.: [
    *       [
    *           {
    *               'type': 'error',
    *               'field_path': 'product_id/price',
    *               'rows': {'from': 1, 'to': 1}, // This error have been encountered between row 1 and row 1 (at row 1)
    *               'message': {"Missing Value"}
    *           },
    *           {
    *               'type': 'error',
    *               'field_path': 'product_id/price',
    *               'rows': {'from': 2, 'to': 2}, // This error have been encountered between row 2 and row 2 (at row 2)
    *               'message': {"Missing Value"}
    *           }
    *       ],
    *       [ // this one is a general error, not linked specifically to a mapped field.
    *           {
    *               'type': 'error',
    *               'message': {"Found more than 10 errors and more than one error per 10 records, interrupted to avoid showing too many errors."}
    *           }
    *       ],
    *       [
    *           {
    *               'type': 'warning',
    *               'field': 'quantity',
    *               'rows': {'from': 2, 'to': 4}, // This error have been encountered between row 2 and row 4 (at 3 different rows)
    *               'message': {}
    *           }
    *       ],
    *   ]
    * @returns {Dict} errorsByFields: {fieldName: [error1, error2, ...]}
    *   E.g.: {
    *       0: [
    *           {
    *               'type': 'error',
    *               'message': {"Found more than 10 errors and more than one error per 10 records, interrupted to avoid showing too many errors."}
    *           }
    *       ],
    *       'product_id/price': [
    *           {
    *               'type': 'error',
    *               'field_path': 'product_id/price',
    *               'rows': {'from': 1, 'to': 2}, // This error have been encountered between row 1 and row 2
    *               'message': {"Missing Value"}
    *           }
    *       ],
    *       'quantity': [
    *           {
    *               'type': 'warning',
    *               'field': 'quantity',
    *               'rows': {'from': 2, 'to': 4}, // This error have been encountered between row 2 and row 4
    *               'message': {}
    *           }
    *       ],
    *   }
    */
    _regroupErrorsByFields: function (errorsSorted) {
        var errorsByFields = {}
        _.each(errorsSorted, function (errors) {
            var mainError = errors[0];
            var field = mainError.field_path ? mainError.field_path.join('/') : mainError.field || 0;

            // regroup errors for same value at different rows in the same error.
            if (errors.length > 1 && mainError.rows) {
                var rowFrom = mainError.rows.from;
                var rowTo = errors[errors.length - 1].rows.to;
                errors = mainError;
                mainError.rows.from = rowFrom;
                mainError.rows.to = rowTo;
            } else {
                errors = mainError;
            }

            if (!errorsByFields[field]) {
                errorsByFields[field] = [errors];
            } else {
                errorsByFields[field].push(errors);
            }
        });

        return errorsByFields;
    },

    toggle_partial: function (result) {
        var $form = this.$('.oe_import');
        var $partial_warning = this.$('.o_import_partial_alert');
        var $partial_count = this.$('.o_import_partial_count');
        if (result == null) {
            $partial_warning.addClass('d-none');
            $form.add(this.$buttons).removeClass('o_import_partial_mode');
            var $skip = this.$('#oe_import_row_start');
            $skip.val($skip.attr('value'));
            $partial_count.text('');
            return;
        }

        this.$('.o_import_batch_alert').addClass('d-none');
        $partial_warning.removeClass('d-none');
        $form.add(this.$buttons).addClass('o_import_partial_mode');
        $partial_count.text((result.skip || 0) + 1);
    }
});
core.action_registry.add('import', DataImport);

// FSM-ize DataImport
StateMachine.create({
    target: DataImport.prototype,
    events: [
        { name: 'loaded_file',
          from: ['none', 'file_loaded', 'preview_error', 'preview_success', 'results', 'imported'],
          to: 'file_loaded' },
        { name: 'settings_changed',
          from: ['file_loaded', 'preview_error', 'preview_success', 'results'],
          to: 'previewing' },
        { name: 'preview_failed', from: 'previewing', to: 'preview_error' },
        { name: 'preview_succeeded', from: 'previewing', to: 'preview_success' },
        { name: 'validate', from: 'preview_success', to: 'validating' },
        { name: 'validate', from: 'results', to: 'validating' },
        { name: 'validated', from: 'validating', to: 'results' },
        { name: 'import', from: ['preview_success', 'results'], to: 'importing' },
        { name: 'import_succeeded', from: 'importing', to: 'imported'},
        { name: 'import_interrupted', from: 'importing', to: 'results' },
        { name: 'import_failed', from: 'importing', to: 'results' }
    ],
});

function offset_by(by) {
    return function offset_message(msg) {
        if (msg.rows) {
            msg.rows.from += by;
            msg.rows.to += by;
        }
    }
}

return {
    DataImport: DataImport,
};

});
