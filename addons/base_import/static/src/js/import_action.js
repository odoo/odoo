odoo.define('base_import.import', function (require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var config = require('web.config');
var core = require('web.core');
var session = require('web.session');
var time = require('web.time');
var AbstractWebClient = require('web.AbstractWebClient');
var Loading = require('web.Loading');

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
        this._title = _t('Import a File'); // Displayed in the breadcrumbs
        this.do_not_change_match = false;
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

        return Promise.all([
            this._super(),
            self.create_model().then(function (id) {
                self.id = id;
                self.$('input[name=import_id]').val(id);

                self.renderButtons();
                var status = {
                    cp_content: {$buttons: self.$buttons},
                };
                self.updateControlPanel(status);
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
        this.$buttons.filter('.o_import_file_reload').on('click', this.loaded_file.bind(this, null));
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
            width: '50%',
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
            width: '50%',
            data: data_digits,
            query: dataFilteredQuery,
            initSelection: function ($e, c) {
                c(_from_data(data_digits, $e.val()) || _make_option($e.val()))
            }
        });
        this.$('input.oe_import_float_decimal_separator').select2({
            width: '50%',
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
            width: '50%',
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
            // start at row 1 = skip 0 lines
            skip: Number(this.$('#oe_import_row_start').val()) - 1 || 0,
            limit: Number(this.$('#oe_import_batch_limit').val()) || null,
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
    onfile_loaded: function (event, from, to, arg) {
        // arg is null if reload -> don't reset partial import
        if (arg != null ) {
            this.toggle_partial(null);
        }

        this.$buttons.filter('.o_import_import, .o_import_validate, .o_import_file_reload').addClass('d-none');
        if (!this.$('input.oe_import_file').val()) { return this['settings_changed'](); }
        this.$('.oe_import_date_format').select2('val', '');
        this.$('.oe_import_datetime_format').val('');

        this.$form.removeClass('oe_import_preview oe_import_error');
        var import_toggle = false;
        var file = this.$('input.oe_import_file')[0].files[0];
        // some platforms send text/csv, application/csv, or other things if Excel is prevent
        if ((file.type && _.last(file.type.split('/')) === "csv") || ( _.last(file.name.split('.')) === "csv")) {
            import_toggle = true;
        }
        this.$form.find('.oe_import_box').toggle(import_toggle);
        jsonp(this.$form, {
            url: '/base_import/set_file'
        }, this.proxy('settings_changed'));
    },
    onpreviewing: function () {
        var self = this;
        this.$buttons.filter('.o_import_import, .o_import_validate, .o_import_file_reload').addClass('d-none');
        this.$form.addClass('oe_import_with_file');
        // TODO: test that write // succeeded?
        this.$form.removeClass('oe_import_preview_error oe_import_error');
        this.$form.toggleClass(
            'oe_import_noheaders text-muted',
            !this.$('input.oe_import_has_header').prop('checked'));
        this._rpc({
                model: 'base_import.import',
                method: 'parse_preview',
                args: [this.id, this.import_options()],
                kwargs: {context: session.user_context},
            }).then(function (result) {
                var signal = result.error ? 'preview_failed' : 'preview_succeeded';
                self[signal](result);
            });
    },
    onpreview_error: function (event, from, to, result) {
        this.$('.oe_import_options').show();
        this.$buttons.filter('.o_import_file_reload').removeClass('d-none');
        this.$form.addClass('oe_import_preview_error oe_import_error');
        this.$form.find('.oe_import_box, .oe_import_with_file').removeClass('d-none');
        this.$form.find('.o_view_nocontent').addClass('d-none');
        this.$('.oe_import_error_report').html(
                QWeb.render('ImportView.preview.error', result));
    },
    onpreview_success: function (event, from, to, result) {
        var self = this;
        this.$buttons.filter('.oe_import_file')
            .text(_t('Load New File'))
            .removeClass('btn-primary').addClass('btn-secondary')
            .blur();
        this.$buttons.filter('.o_import_import, .o_import_validate, .o_import_file_reload').removeClass('d-none');
        this.$form.find('.oe_import_box, .oe_import_with_file').removeClass('d-none');
        this.$form.find('.o_view_nocontent').addClass('d-none');
        this.$form.addClass('oe_import_preview');
        this.$('input.oe_import_advanced_mode').prop('checked', result.advanced_mode);
        this.$('.oe_import_grid').html(QWeb.render('ImportView.preview', result));

        this.$('.o_import_batch_alert').toggleClass('d-none', !result.batch);

        var messages = [];
        if (result.headers.length === 1) {
            messages.push({type: 'warning', message: _t("A single column was found in the file, this often means the file separator is incorrect")});
        }

        if (!_.isEmpty(messages)) {
            this.$('.oe_import_options').show();
            this.onresults(null, null, null, {'messages': messages});
        }

        // merge option values back in case they were updated/guessed
        _.each(['encoding', 'separator', 'float_thousand_separator', 'float_decimal_separator'], function (id) {
            self.$('.oe_import_' + id).select2('val', result.options[id])
        });
        this.$('.oe_import_date_format').select2('val', time.strftime_to_moment_format(result.options.date_format));
        this.$('.oe_import_datetime_format').val(time.strftime_to_moment_format(result.options.datetime_format));
        // hide all "true debug" options when not in debug mode
        this.$('.oe_import_debug_option').toggleClass('d-none', !result.debug);

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
            if (config.isDebug()) {
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
        var self = this;
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
        delete kwargs.tracking_disable;
        kwargs.context = _.extend(
            {}, this.parent_context,
            {tracking_disable: tracking_disable}
        );
        var self = this;
        this.trigger_up('with_client', {callback: function () {
            this.loading.ignore_events = true;
        }});
        $.blockUI({message: QWeb.render('Throbber')});
        $(document.body).addClass('o_ui_blocked');
        var opts = this.import_options();

        var $el = $('.oe_throbber_message');
        var msg = kwargs.dryrun ? _t("%d records tested...")
                                : _t("%d records successfully imported...");
        opts.callback = function (count) {
            $el.text(_.str.sprintf(msg, count));
        };

        return this._batchedImport(opts, [this.id, fields, columns], kwargs, {done: 0, prev: 0})
            .then(null, function (reason) {
                var error = reason.message;
                var event = reason.event;
                // In case of unexpected exception, convert
                // "JSON-RPC error" to an import failure, and
                // prevent default handling (warning dialog)
                if (event) { event.preventDefault(); }

                var msg;
                var errordata = error.data || {};
                if (errordata.type === 'xhrerror') {
                    var xhr = errordata.objects[0];
                    switch (xhr.status) {
                    case 504: // gateway timeout
                        msg = _t("Import timed out. Please retry. If you still encounter this issue, the file may be too big for the system's configuration, try to split it (import less records per file).");
                        break;
                    default:
                        msg = _t("An unknown issue occurred during import (possibly lost connection, data limit exceeded or memory limits exceeded). Please retry in case the issue is transient. If the issue still occurs, try to split the file rather than import it at once.");
                    }
                } else {
                    msg = errordata.arguments && (errordata.arguments[1] || errordata.arguments[0])
                        || error.message;
                }

                return Promise.resolve({'messages': [{
                    type: 'error',
                    record: false,
                    message: msg,
                }]});
            }).finally(function () {
                $(document.body).removeClass('o_ui_blocked');
                $.unblockUI();
                self.trigger_up('with_client', {callback: function () {
                    delete this.loading.ignore_events;
                }});
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
        opts.callback && opts.callback(rec.done || 0);
        var self = this;
        return this._rpc({
            model: 'base_import.import',
            method: 'do',
            args: args.concat([opts]),
            kwargs: kwargs
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
                    messages: results.messages.concat(r2.messages),
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
            var message = results.messages;
            if (!_.any(message, function (message) {
                    return message.type === 'error'; })) {
                self['import_succeeded'](results);
                return;
            }
            self['import_failed'](results);
        });
        return prom;
    },
    onimported: function (event, from, to, results) {
        this.do_notify(_t("Import completed"), _.str.sprintf(_t("%d records were successfully imported"), results.ids.length));
        this.exit();
    },
    exit: function () {
        this.trigger_up('history_back');
    },
    onresults: function (event, from, to, results) {
        var fields = this.$('.oe_import_fields input.oe_import_match_field').map(function (index, el) {
            return $(el).select2('val') || false;
        }).get();

        var message = results.messages;
        var no_messages = _.isEmpty(message);
        if (no_messages) {
            message.push({
                type: 'info',
                message: _t("Everything seems valid.")
            });
        } else if (event === 'import_failed' && results.ids) {
            // both ids in a failed import -> partial import
            this.toggle_partial(results);
        }

        // row indexes come back 0-indexed, spreadsheets
        // display 1-indexed.
        var offset = 1;
        // offset more if header
        if (this.import_options().headers) { offset += 1; }

        var messagesSorted = _.sortBy(_(message).groupBy('message'), function (group) {
            if (group[0].priority){
                return -2;
            }

            // sort by gravity, then, order of field in list
            var order = 0;
            switch (group[0].type) {
            case 'error': order = 0; break;
            case 'warning': order = fields.length + 1; break;
            case 'info': order = 2 * (fields.length + 1); break;
            default: order = 3 * (fields.length + 1); break;
            }
            return order + _.indexOf(fields, group[0].field);
        });

        this.$form.addClass('oe_import_error');
        this.$('.oe_import_error_report').html(
            QWeb.render('ImportView.error', {
                errors: messagesSorted,
                at: function (rows) {
                    var from = rows.from + offset;
                    var to = rows.to + offset;
                    var rowName = '';
                    if (results.name.length > rows.from && results.name[rows.from] !== '') {
                        rowName = _.str.sprintf(' (%s)', results.name[rows.from]);
                    }
                    if (from === to) {
                        return _.str.sprintf(_t("at row %d%s"), from, rowName);
                    }
                    return _.str.sprintf(_t("between rows %d and %d"),
                                         from, to);
                },
                at_multi: function (rows) {
                    var from = rows.from + offset;
                    var to = rows.to + offset;
                    var rowName = '';
                    if (results.name.length > rows.from && results.name[rows.from] !== '') {
                        rowName = _.str.sprintf(' (%s)', results.name[rows.from]);
                    }
                    if (from === to) {
                        return _.str.sprintf(_t("Row %d%s"), from, rowName);
                    }
                    return _.str.sprintf(_t("Between rows %d and %d"),
                                         from, to);
                },
                at_multi_header: function (numberLines) {
                    return _.str.sprintf(_t("at %d different rows:"),
                                         numberLines);
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
                            '<div class="oe_import_moreinfo oe_import_moreinfo_choices"><a href="#" class="oe_import_report_see_possible_value oe_import_see_all"><i class="fa fa-arrow-right"/> %s </a><ul class="oe_import_report_more">%s</ul></div>',
                            _.str.escapeHTML(_t("See possible values")),
                            _(msg).map(function (msg) {
                                return '<li>'
                                    + _.str.escapeHTML(msg)
                                + '</li>';
                            }).join(''));
                    }
                    // Final should be object, action descriptor
                    return [
                        '<div class="oe_import_moreinfo oe_import_moreinfo_action">',
                            _.str.sprintf('<a href="#" data-action="%s" class="oe_import_see_all"><i class="fa fa-arrow-right"/> ',
                                    _.str.escapeHTML(JSON.stringify(msg))),
                                _.str.escapeHTML(
                                    _t("See possible values")),
                            '</a>',
                        '</div>'
                    ].join('');
                },
            }));
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

Loading.include({
    on_rpc_event: function () {
        if (this.ignore_events) {
            return
        }
        this._super.apply(this, arguments);
    }
});
AbstractWebClient.prototype.custom_events['with_client'] = function (ev) {
    ev.data.callback.call(this);
};

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
