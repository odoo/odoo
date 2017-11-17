odoo.define('base_import.import', function (require) {
"use strict";

var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var session = require('web.session');
var time = require('web.time');
var Widget = require('web.Widget');

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

var DataImport = Widget.extend(ControlPanelMixin, {
    template: 'ImportView',
    opts: [
        {name: 'encoding', label: _lt("Encoding:"), value: 'utf-8'},
        {name: 'separator', label: _lt("Separator:"), value: ','},
        {name: 'quoting', label: _lt("Text Delimiter:"), value: '"'}
    ],
    parse_opts: [
        {name: 'date_format', label: _lt("Date Format:"), value: ''},
        {name: 'datetime_format', label: _lt("Datetime Format:"), value: ''},
        {name: 'float_thousand_separator', label: _lt("Thousands Separator:"), value: ','},
        {name: 'float_decimal_separator', label: _lt("Decimal Separator:"), value: '.'}
    ],
    events: {
        // 'change .oe_import_grid input': 'import_dryrun',
        'change .oe_import_file': 'loaded_file',
        'click .oe_import_file_reload': 'loaded_file',
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
    start: function () {
        var self = this;
        this.setup_encoding_picker();
        this.setup_separator_picker();
        this.setup_float_format_picker();

        return $.when(
            this._super(),
            self.create_model().done(function (id) {
                self.id = id;
                self.$('input[name=import_id]').val(id);

                self.renderButtons();
                self.renderImportLink();
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
            });
    },
    renderButtons: function() {
        var self = this;
        this.$buttons = $(QWeb.render("ImportView.buttons", this));
        this.$buttons.filter('.o_import_validate').on('click', this.validate.bind(this));
        this.$buttons.filter('.o_import_import').on('click', this.import.bind(this));
        this.$buttons.filter('.o_import_cancel').on('click', function(e) {
            e.preventDefault();
            self.exit();
        });
    },
    renderImportLink: function() {
        if (this.res_model == 'res.partner') {
            this.$(".import-link").prop({"text": _t(" Import Template for Customers"), "href": "/base_import/static/csv/res.partner.csv"});
            this.$(".template-import").removeClass("hidden");
        }
    },
    setup_encoding_picker: function () {
        this.$('input.oe_import_encoding').select2({
            width: '160px',
            query: function (q) {
                var make = function (term) { return {id: term, text: term}; };
                var suggestions = _.map(
                    ('utf-8 utf-16 windows-1252 latin1 latin2 big5 ' +
                     'gb18030 shift_jis windows-1251 koir8_r').split(/\s+/),
                    make);
                if (q.term) {
                    suggestions.unshift(make(q.term));
                }
                q.callback({results: suggestions});
            },
            initSelection: function (e, c) {
                return c({id: 'utf-8', text: 'utf-8'});
            }
        }).select2('val', 'utf-8');
    },
    setup_separator_picker: function () {
        this.$('input.oe_import_separator').select2({
            width: '160px',
            query: function (q) {
                var suggestions = [
                    {id: ',', text: _t("Comma")},
                    {id: ';', text: _t("Semicolon")},
                    {id: '\t', text: _t("Tab")},
                    {id: ' ', text: _t("Space")}
                ];
                if (q.term) {
                    suggestions.unshift({id: q.term, text: q.term});
                }
                q.callback({results: suggestions});
            },
            initSelection: function (e, c) {
                return c({id: ',', text: _t("Comma")});
            },
        });
    },
    setup_float_format_picker: function () {
        var sug_query = function (q) {
                    var suggestions = [
                        {id: ',', text: _t("Comma")},
                        {id: '.', text: _t("Dot")},
                    ];
                    if (q.term) {
                        suggestions.unshift({id: q.term, text: q.term});
                    }
                    q.callback({results: suggestions});
                };
        this.$('input.oe_import_float_thousand_separator').select2({
            width: '160px',
            query: sug_query,
            initSelection: function (e, c) {
                return c({id: ',', text: _t("Comma")});
            },
        });
        this.$('input.oe_import_float_decimal_separator').select2({
            width: '160px',
            query: sug_query,
            initSelection: function (e, c) {
                return c({id: ',', text: _t("Dot")});
            },
        });
    },

    import_options: function () {
        var self = this;
        var options = {
            headers: this.$('input.oe_import_has_header').prop('checked'),
            advanced: this.$('input.oe_import_advanced_mode').prop('checked'),
            keep_matches: this.do_not_change_match
        };
        _(this.opts).each(function (opt) {
            options[opt.name] =
                self.$('input.oe_import_' + opt.name).val();
        });
        _(this.parse_opts).each(function (opt) {
            if (opt.name === 'date_format' || opt.name === 'datetime_format') {
                options[opt.name] = time.moment_to_strftime_format(self.$('input.oe_import_' + opt.name).val());
            }
            else {
                options[opt.name] = self.$('input.oe_import_' + opt.name).val();
            }
        });
        options['fields'] = [];
        if (this.do_not_change_match) {
            options['fields'] = this.$('.oe_import_fields input.oe_import_match_field').map(function (index, el) {
                return $(el).select2('val') || false;
            }).get();
        }
        this.do_not_change_match = false;
        return options;
    },

    //- File & settings change section
    onfile_loaded: function () {
        var file = this.$('.oe_import_file')[0].files[0];
        this.$('.oe_import_file_show').val(file !== undefined && file.name || '');
        this.$buttons.filter('.o_import_button').add(this.$('.oe_import_file_reload'))
                .prop('disabled', true);
        if (!this.$('input.oe_import_file').val()) { return this['settings_changed'](); }
        this.$('.oe_import_date_format').val('');
        this.$('.oe_import_datetime_format').val('');

        this.$el.removeClass('oe_import_preview oe_import_error');
        var import_toggle = false;
        var file = this.$('input.oe_import_file')[0].files[0];
        // some platforms send text/csv, application/csv, or other things if Excel is prevent
        if ((file.type && _.last(file.type.split('/')) === "csv") || ( _.last(file.name.split('.')) === "csv")) {
            import_toggle = true;
        }
        this.$el.find('.oe_import_toggle').toggle(import_toggle);
        jsonp(this.$el, {
            url: '/base_import/set_file'
        }, this.proxy('settings_changed'));
    },
    onpreviewing: function () {
        var self = this;
        this.$buttons.filter('.o_import_button').add(this.$('.oe_import_file_reload'))
                .prop('disabled', true);
        this.$el.addClass('oe_import_with_file');
        // TODO: test that write // succeeded?
        this.$el.removeClass('oe_import_preview_error oe_import_error');
        this.$el.toggleClass(
            'oe_import_noheaders',
            !this.$('input.oe_import_has_header').prop('checked'));
        this._rpc({
                model: 'base_import.import',
                method: 'parse_preview',
                args: [this.id, this.import_options()],
            }).done(function (result) {
                var signal = result.error ? 'preview_failed' : 'preview_succeeded';
                self[signal](result);
            });
    },
    onpreview_error: function (event, from, to, result) {
        this.$('.oe_import_options').show();
        this.$('.oe_import_file_reload').prop('disabled', false);
        this.$el.addClass('oe_import_preview_error oe_import_error');
        this.$('.oe_import_error_report').html(
                QWeb.render('ImportView.preview.error', result));
    },
    onpreview_success: function (event, from, to, result) {
        var self = this;
        this.$buttons.filter('.o_import_import').removeClass('btn-primary');
        this.$buttons.filter('.o_import_validate').addClass('btn-primary');
        this.$buttons.filter('.o_import_button').add(this.$('.oe_import_file_reload'))
                .prop('disabled', false);
        this.$el.addClass('oe_import_preview');
        this.$('input.oe_import_advanced_mode').prop('checked', result.advanced_mode);
        this.$('.oe_import_grid').html(QWeb.render('ImportView.preview', result));

        if (result.headers.length === 1) {
            this.$('.oe_import_options').show();
            this.onresults(null, null, null, [{
                type: 'warning',
                message: _t("A single column was found in the file, this often means the file separator is incorrect")
            }]);
        }

        this.$('.oe_import_date_format').val(time.strftime_to_moment_format(result.options.date_format));
        this.$('.oe_import_datetime_format').val(time.strftime_to_moment_format(result.options.datetime_format));
        this.$('.oe_import_float_thousand_separator').val(result.options.float_thousand_separator).change();
        this.$('.oe_import_float_decimal_separator').val(result.options.float_decimal_separator).change();
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

                    callback(item_finder(default_value));
                },
                placeholder: _t('Don\'t import'),
                width: 'resolve',
                dropdownCssClass: 'oe_import_selector'
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
                    required: field.required
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
                args: [this.id, fields, this.import_options()],
                kwargs : kwargs,
            }).fail(function (error, event) {
                // In case of unexpected exception, convert
                // "JSON-RPC error" to an import failure, and
                // prevent default handling (warning dialog)
                if (event) { event.preventDefault(); }
                return $.when([{
                    type: 'error',
                    record: false,
                    message: error.data.arguments && error.data.arguments[1] || error.message,
                }]);
            }) ;
    },
    onvalidate: function () {
        return this.call_import({ dryrun: true, tracking_disable: true })
            .done(this.proxy('validated'));
    },
    onimport: function () {
        var self = this;
        return this.call_import({ dryrun: false }).done(function (message) {
            if (!_.any(message, function (message) {
                    return message.type === 'error'; })) {
                self['import_succeeded']();
                return;
            }
            self['import_failed'](message);
        });
    },
    onimported: function () {
        this.exit();
    },
    exit: function () {
        this.trigger_up('history_back');
    },
    onresults: function (event, from, to, message) {
        var no_messages = _.isEmpty(message);
        this.$buttons.filter('.o_import_import').toggleClass('btn-primary', no_messages);
        this.$buttons.filter('.o_import_import').toggleClass('btn-default', !no_messages);
        this.$buttons.filter('.o_import_validate').toggleClass('btn-primary', !no_messages);
        this.$buttons.filter('.o_import_validate').toggleClass('btn-default', no_messages);
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
    ]
});

return {
    DataImport: DataImport,
};

});
