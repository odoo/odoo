odoo.define('base_import.import', function (require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var session = require('web.session');
var time = require('web.time');

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

var DataImport = AbstractAction.extend(ControlPanelMixin, {
    template: 'ImportView',
    opts: [
        {name: 'encoding', label: _lt("Encoding:"), value: ''},
        {name: 'separator', label: _lt("Separator:"), value: ''},
        {name: 'quoting', label: _lt("Text Delimiter:"), value: '"'}
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
        // 'change .oe_import_grid input': 'import_dryrun',
        'change .oe_import_file': 'loaded_file',
        'change input.oe_import_has_header, .js_import_options input': 'settings_changed',
        'change input.oe_import_advanced_mode': function (e) {
            this.do_not_change_match = true;
            this['settings_changed']();
        },
        'click a.oe_import_toggle': function (e) {
            e.preventDefault();
            this.$('.oe_import_options').toggle();
        },
        'click .oe_import_report a.oe_import_report_count': function (e) {
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
                flags: {
                    search_view: true,
                    display_title: true,
                    pager: true,
                    list: {selectable: false}
                }
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
        action.display_name = _t('Import a File'); // Displayed in the breadcrumbs
        this.do_not_change_match = false;
    },
    /**
     * @override
     */
    willStart: function () {
        var self = this;
        return this._rpc({
            model: this.res_model,
            method: 'get_import_templates',
            context: this.parent_context,
        }).then(function (result) {
            self.importTemplates = result;
        });
    },
    start: function () {
        var self = this;
        this.setup_encoding_picker();
        this.setup_separator_picker();
        this.setup_float_format_picker();
        this.setup_date_format_picker();

        return $.when(
            this._super(),
            self.create_model().done(function (id) {
                self.id = id;
                self.$('input[name=import_id]').val(id);

                self.renderButtons();
                var status = {
                    cp_content: {$buttons: self.$buttons},
                };
                self.update_control_panel(status);
            })
        );
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
            self.$('.oe_import_file').click();
        });
        this.$buttons.filter('.o_import_cancel').on('click', function(e) {
            e.preventDefault();
            self.exit();
        });
    },
    setup_encoding_picker: function () {
        this.$('input.oe_import_encoding').select2({
            width: '160px',
            data: _.map(('utf-8 utf-16 windows-1252 latin1 latin2 big5 gb18030 shift_jis windows-1251 koir8_r').split(/\s+/), _make_option),
            query: dataFilteredQuery,
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
            width: '160px',
            data: data,
            query: dataFilteredQuery,
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
            width: '160px',
            data: data_digits,
            query: dataFilteredQuery,
            initSelection: function ($e, c) {
                c(_from_data(data_digits, $e.val()) || _make_option($e.val()))
            }
        });
        this.$('input.oe_import_float_decimal_separator').select2({
            width: '160px',
            data: data_decimal,
            query: dataFilteredQuery,
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
            width: '160px',
            data: data,
            query: dataFilteredQuery,
            initSelection: function ($e, c) {
                c(_from_data(data, $e.val()) || _make_option($e.val()));
            }
        })
    },

    import_options: function () {
        var self = this;
        var options = {
            headers: this.$('input.oe_import_has_header').prop('checked'),
            advanced: this.$('input.oe_import_advanced_mode').prop('checked'),
            keep_matches: this.do_not_change_match,
            name_create_enabled_fields: {},
        };
        _(this.opts).each(function (opt) {
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
            options['fields'] = this.$('.oe_import_fields input.oe_import_match_field').map(function (index, el) {
                return $(el).select2('val') || false;
            }).get();
        }
        this.do_not_change_match = false;
        this.$('input.o_import_create_option').each(function () {
            var field = this.getAttribute('field');
            if (field) {
                options.name_create_enabled_fields[field] = this.checked;
            }
        });
        return options;
    },

    //- File & settings change section
    onfile_loaded: function () {
        this.$buttons.filter('.o_import_import, .o_import_validate').addClass('d-none');
        if (!this.$('input.oe_import_file').val()) { return this['settings_changed'](); }
        this.$('.oe_import_date_format').select2('val', '');
        this.$('.oe_import_datetime_format').val('');

        this.$el.removeClass('oe_import_preview oe_import_error');
        var import_toggle = false;
        var file = this.$('input.oe_import_file')[0].files[0];
        // some platforms send text/csv, application/csv, or other things if Excel is prevent
        if ((file.type && _.last(file.type.split('/')) === "csv") || ( _.last(file.name.split('.')) === "csv")) {
            import_toggle = true;
        }
        this.$el.find('.oe_import_box').toggle(import_toggle);
        jsonp(this.$el, {
            url: '/base_import/set_file'
        }, this.proxy('settings_changed'));
    },
    onpreviewing: function () {
        var self = this;
        this.$buttons.filter('.o_import_import, .o_import_validate').addClass('d-none');
        this.$el.addClass('oe_import_with_file');
        // TODO: test that write // succeeded?
        this.$el.removeClass('oe_import_preview_error oe_import_error');
        this.$el.toggleClass(
            'oe_import_noheaders text-muted',
            !this.$('input.oe_import_has_header').prop('checked'));

        // Clear the input value to allow onchange to be triggered
        // if the file is the same (for all browsers)
        self.$('input.oe_import_file').val('');

        this._rpc({
                model: 'base_import.import',
                method: 'parse_preview',
                args: [this.id, this.import_options()],
                kwargs: {context: session.user_context},
            }).done(function (result) {
                var signal = result.error ? 'preview_failed' : 'preview_succeeded';
                self[signal](result);
            });
    },
    onpreview_error: function (event, from, to, result) {
        this.$('.oe_import_options').show();
        this.$el.addClass('oe_import_preview_error oe_import_error');
        this.$el.find('.oe_import_box, .oe_import_with_file').removeClass('d-none');
        this.$el.find('.o_view_nocontent').addClass('d-none');
        this.$('.oe_import_error_report').html(
                QWeb.render('ImportView.preview.error', result));
    },
    onpreview_success: function (event, from, to, result) {
        var self = this;
        this.$buttons.filter('.oe_import_file')
            .text(_t('Load New File'))
            .removeClass('btn-primary').addClass('btn-secondary')
            .blur();
        this.$buttons.filter('.o_import_import, .o_import_validate').removeClass('d-none');
        this.$el.find('.oe_import_box, .oe_import_with_file').removeClass('d-none');
        this.$el.find('.o_view_nocontent').addClass('d-none');
        this.$el.addClass('oe_import_preview');
        this.$('input.oe_import_advanced_mode').prop('checked', result.advanced_mode);
        this.$('.oe_import_grid').html(QWeb.render('ImportView.preview', result));

        if (result.headers.length === 1) {
            this.$('.oe_import_options').show();
            this.onresults(null, null, null, {'messages': [{
                type: 'warning',
                message: _t("A single column was found in the file, this often means the file separator is incorrect")
            }]});
        }

        // merge option values back in case they were updated/guessed
        _.each(['encoding', 'separator', 'float_thousand_separator', 'float_decimal_separator'], function (id) {
            self.$('.oe_import_' + id).select2('val', result.options[id])
        });
        this.$('.oe_import_date_format').select2('val', time.strftime_to_moment_format(result.options.date_format));
        this.$('.oe_import_datetime_format').val(time.strftime_to_moment_format(result.options.datetime_format));
        if (result.debug === false){
            this.$('.oe_import_tracking').hide();
            this.$('.oe_import_deferparentstore').hide();
        }

        var $fields = this.$('.oe_import_fields input');
        this.render_fields_matches(result, $fields);
        var data = this.generate_fields_completion(result);
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
            var filtered_data = self.generate_fields_completion(result, k);

            var $thing = $();
            var bind = function (d) {};
            if (session.debug) {
                $thing = $(QWeb.render('ImportView.create_record_option')).insertAfter(v).hide();
                bind = function (data) {
                    switch (data.type) {
                    case 'many2one': case 'many2many':
                        $thing.find('input').attr('field', data.id);
                        $thing.show();
                        break;
                    default:
                        $thing.find('input').attr('field', '').prop('checked', false);
                        $thing.hide();
                    }
                }
            }

            $(v).select2({
                allowClear: true,
                minimumInputLength: 0,
                data: filtered_data,
                initSelection: function (element, callback) {
                    var default_value = element.val();
                    if (!default_value) {
                        callback('');
                        return;
                    }

                    var data = item_finder(default_value);
                    bind(data);
                    callback(data);
                },
                placeholder: _t('Don\'t import'),
                width: 'resolve',
                dropdownCssClass: 'oe_import_selector'
            }).on('change', function (e) {
                bind(item_finder(e.currentTarget.value));
            });
        });
    },
    generate_fields_completion: function (root, index) {
        var basic = [];
        var regulars = [];
        var o2m = [];
        var headers_type = root.headers_type;
        function traverse(field, ancestors, collection, type) {
            var subfields = field.fields;
            var advanced_mode = self.$('input.oe_import_advanced_mode').prop('checked');
            var field_path = ancestors.concat(field);
            var label = _(field_path).pluck('string').join(' / ');
            var id = _(field_path).pluck('name').join('/');
            if (type === undefined || (type !== undefined && (type.indexOf('all') !== -1 || type.indexOf(field['type']) !== -1))){
                // If non-relational, m2o or m2m, collection is regulars
                if (!collection) {
                    if (field.name === 'id') {
                        collection = basic;
                    } else if (_.isEmpty(subfields)
                            || _.isEqual(_.pluck(subfields, 'name'), ['id', '.id'])) {
                        collection = regulars;
                    } else {
                        collection = o2m;
                    }
                }

                collection.push({
                    id: id,
                    text: label,
                    required: field.required,
                    type: field.type
                });

            }
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
                    traverse(field, [], undefined, headers_type[index]);
                }
            }
        });

        var cmp = function (field1, field2) {
            return field1.text.localeCompare(field2.text);

        };
        regulars.sort(cmp);
        o2m.sort(cmp);
        if (!_.isEmpty(regulars) && !_.isEmpty(o2m)){
            basic = basic.concat([
                { text: _t("Normal Fields"), children: regulars },
                { text: _t("Relation Fields"), children: o2m },
            ]);
        }
        else if (!_.isEmpty(regulars)) {
            basic = basic.concat(regulars);
        }
        else if (!_.isEmpty(o2m)) {
            basic = basic.concat(o2m);
        }
        return basic;
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
        var fields = this.$('.oe_import_fields input.oe_import_match_field').map(function (index, el) {
            return $(el).select2('val') || false;
        }).get();
        var columns = this.$('.oe_import_grid-header .oe_import_grid-cell .o_import_header_name').map(function () {
            return $(this).text().trim().toLowerCase() || false;
        }).get();

        var tracking_disable = 'tracking_disable' in kwargs ? kwargs.tracking_disable : !this.$('#oe_import_tracking').prop('checked')
        var defer_parent_store = 'defer_parent_store' in kwargs ? kwargs.defer_parent_store : !!this.$('#oe_import_deferparentstore').prop('checked')
        delete kwargs.tracking_disable;
        delete kwargs.defer_parent_store;
        kwargs.context = _.extend(
            {}, this.parent_context,
            {tracking_disable: tracking_disable, defer_parent_store_computation: defer_parent_store}
        );
        return this._rpc({
                model: 'base_import.import',
                method: 'do',
                args: [this.id, fields, columns, this.import_options()],
                kwargs : kwargs,
            }).then(null, function (error, event) {
                // In case of unexpected exception, convert
                // "JSON-RPC error" to an import failure, and
                // prevent default handling (warning dialog)
                if (event) { event.preventDefault(); }

                var msg;
                if (error.data.type === 'xhrerror') {
                    var xhr = error.data.objects[0];
                    switch (xhr.status) {
                    case 504: // gateway timeout
                        msg = _t("Import timed out. Please retry. If you still encounter this issue, the file may be too big for the system's configuration, try to split it (import less records per file).");
                        break;
                    default:
                        msg = _t("An unknown issue occurred during import (possibly lost connection, data limit exceeded or memory limits exceeded). Please retry in case the issue is transient. If the issue still occurs, try to split the file rather than import it at once.");
                    }
                } else {
                    msg = (error.data.arguments && error.data.arguments[1] || error.data.arguments[0])
                        || error.message;
                }

                return $.when({'messages': [{
                    type: 'error',
                    record: false,
                    message: msg,
                }]});
            }) ;
    },
    onvalidate: function () {
        return this.call_import({ dryrun: true, tracking_disable: true })
            .done(this.proxy('validated'));
    },
    onimport: function () {
        var self = this;
        return this.call_import({ dryrun: false }).done(function (results) {
            var message = results.messages;
            if (!_.any(message, function (message) {
                    return message.type === 'error'; })) {
                self['import_succeeded'](results);
                return;
            }
            self['import_failed'](results);
        });
    },
    onimported: function (event, from, to, results) {
        this.do_notify(_t("Import completed"), _.str.sprintf(_t("%d records were successfully imported"), results.ids.length));
        this.exit();
    },
    exit: function () {
        this.trigger_up('history_back');
    },
    onresults: function (event, from, to, results) {
        var message = results.messages;
        var no_messages = _.isEmpty(message);
        if (no_messages) {
            message.push({
                type: 'info',
                message: _t("Everything seems valid.")
            });
        }
        // row indexes come back 0-indexed, spreadsheets
        // display 1-indexed.
        var offset = 1;
        // offset more if header
        if (this.import_options().headers) { offset += 1; }

        this.$el.addClass('oe_import_error');
        this.$('.oe_import_error_report').html(
            QWeb.render('ImportView.error', {
                errors: _(message).groupBy('message'),
                at: function (rows) {
                    var from = rows.from + offset;
                    var to = rows.to + offset;
                    if (from === to) {
                        return _.str.sprintf(_t("at row %d"), from);
                    }
                    return _.str.sprintf(_t("between rows %d and %d"),
                                         from, to);
                },
                more: function (n) {
                    return _.str.sprintf(_t("(%d more)"), n);
                },
                info: function (msg) {
                    if (typeof msg === 'string') {
                        return _.str.sprintf(
                            '<div class="oe_import_moreinfo oe_import_moreinfo_message">%s</div>',
                            _.str.escapeHTML(msg));
                    }
                    if (msg instanceof Array) {
                        return _.str.sprintf(
                            '<div class="oe_import_moreinfo oe_import_moreinfo_choices">%s <ul>%s</ul></div>',
                            _.str.escapeHTML(_t("Here are the possible values:")),
                            _(msg).map(function (msg) {
                                return '<li>'
                                    + _.str.escapeHTML(msg)
                                + '</li>';
                            }).join(''));
                    }
                    // Final should be object, action descriptor
                    return [
                        '<div class="oe_import_moreinfo oe_import_moreinfo_action">',
                            _.str.sprintf('<a href="#" data-action="%s">',
                                    _.str.escapeHTML(JSON.stringify(msg))),
                                _.str.escapeHTML(
                                    _t("Get all possible values")),
                            '</a>',
                        '</div>'
                    ].join('');
                },
            }));
    },
});
core.action_registry.add('import', DataImport);

// FSM-ize DataImport
StateMachine.create({
    target: DataImport.prototype,
    events: [
        { name: 'loaded_file',
          from: ['none', 'file_loaded', 'preview_error', 'preview_success', 'results'],
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
        { name: 'import_failed', from: 'importing', to: 'results' }
    ],
});

return {
    DataImport: DataImport,
};

});
