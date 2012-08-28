openerp.web.data_import = function(openerp) {
var QWeb = openerp.web.qweb,
    _t = openerp.web._t;
/**
 * Safari does not deal well at all with raw JSON data being returned. As a
 * result, we're going to cheat by using a pseudo-jsonp: instead of getting
 * JSON data in the iframe, we're getting a ``script`` tag which consists of a
 * function call and the returned data (the json dump).
 *
 * The function is an auto-generated name bound to ``window``, which calls
 * back into the callback provided here.
 *
 * @param {Object} form the form element (DOM or jQuery) to use in the call
 * @param {Object} attributes jquery.form attributes object
 * @param {Function} callback function to call with the returned data
 */
function jsonp(form, attributes, callback) {
    attributes = attributes || {};
    var options = {jsonp: _.uniqueId('import_callback_')};
    window[options.jsonp] = function () {
        try{
            delete window[options.jsonp];
        } catch(e){
            window[options.jsonp] = null;
        }
        callback.apply(null, arguments);
    };
    if ('data' in attributes) {
        _.extend(attributes.data, options);
    } else {
        _.extend(attributes, {data: options});
    }
    $(form).ajaxSubmit(attributes);
}

openerp.web.DataImport = openerp.web.Dialog.extend({
    template: 'ImportDataView',
    dialog_title: {toString: function () { return _t("Import Data"); }},
    init: function(parent, dataset){
        var self = this;
        this._super(parent, {});
        this.model = parent.model;
        this.fields = [];
        this.all_fields = [];
        this.fields_with_defaults = [];
        this.required_fields = null;
        this.context = dataset.get_context();

        var convert_fields = function (root, prefix) {
            prefix = prefix || '';
            _(root.fields).each(function (f) {
                self.all_fields.push(prefix + f.name);
                if (f.fields) {
                    convert_fields(f, prefix + f.id + '/');
                }
            });
        };
        this.ready  = $.Deferred.queue().then(function () {
            self.required_fields = _(self.fields).chain()
                .filter(function (field) {
                    return field.required &&
                           !_.include(self.fields_with_defaults, field.id); })
                .pluck('id')
                .uniq()
                .value();
            convert_fields(self);
            self.all_fields.sort();
        });
    },
    start: function() {
        var self = this;
        this._super();
        this.open({
            buttons: [
                {text: _t("Close"), click: function() { self.stop(); }},
                {text: _t("Import File"), click: function() { self.do_import(); }, 'class': 'oe-dialog-import-button'}
            ],
            close: function(event, ui) {
                self.stop();
            }
        });
        this.toggle_import_button(false);
        this.$element.find('#csvfile').change(this.on_autodetect_data);
        this.$element.find('fieldset').change(this.on_autodetect_data);
        this.$element.delegate('fieldset legend', 'click', function() {
            $(this).parent().toggleClass('oe-closed');
        });
        this.ready.push(new openerp.web.DataSet(
                this, this.model, this.context).call(
            'fields_get', [], function (fields) {
                self.graft_fields(fields);
                self.ready.push(new openerp.web.DataSet(self, self.model)
                        .default_get(_.pluck(self.fields, 'id')).then(function (fields) {
                    _.each(fields, function(val, key) {
                        if (val) {
                            self.fields_with_defaults.push(key);
                        }
                    });
                })
            )
        }));
    },
    graft_fields: function (fields, parent, level) {
        parent = parent || this;
        level = level || 0;

        var self = this;
        if (level === 0) {
            parent.fields.push({
                id: 'id',
                name: 'id',
                string: _t('External ID'),
                required: false
            });
        }
        _(fields).each(function (field, field_name) {
            // Ignore spec for id field
            // Don't import function fields (function and related)
            if (field_name === 'id') {
                return;
            }
            // Skip if there's no state which could disable @readonly,
            // if a field is ever always readonly we can't import it
            if (field.readonly) {
                // no states at all
                if (_.isEmpty(field.states)) { return; }
                // no state altering @readonly
                if (!_.any(field.states, function (modifiers) {
                    return _(modifiers).chain().pluck(0).contains('readonly').value();
                })) { return; }
            }

            var f = {
                id: field_name,
                name: field_name,
                string: field.string,
                required: field.required
            };

            switch (field.type) {
            case 'many2many':
            case 'many2one':
                // push a copy for the bare many2one field, to allow importing
                // using name_search too - even if we default to exporting the XML ID
                var many2one_field = _.extend({}, f);
                parent.fields.push(many2one_field);
                f.name += '/id';
                break;
            case 'one2many':
                f.name += '/id';
                f.fields = [];
                // only fetch sub-fields to a depth of 2 levels
                if (level < 2) {
                    self.ready.push(new openerp.web.DataSet(self, field.relation, self.context).call(
                        'fields_get', [], function (fields) {
                            self.graft_fields(fields, f, level+1);
                    }));
                }
                break;
            }
            parent.fields.push(f);
        });
    },
    toggle_import_button: function (newstate) {
        this.$element.dialog('widget')
                .find('.oe-dialog-import-button')
                .button('option', 'disabled', !newstate);
    },
    do_import: function() {
        if(!this.$element.find('#csvfile').val()) { return; }
        var lines_to_skip = parseInt(this.$element.find('#csv_skip').val(), 10);
        var with_headers = this.$element.find('#file_has_headers').prop('checked');
        if (!lines_to_skip && with_headers) {
            lines_to_skip = 1;
        }
        var indices = [], fields = [];
        this.$element.find(".sel_fields").each(function(index, element) {
            var val = element.value;
            if (!val) {
                return;
            }
            indices.push(index);
            fields.push(val);
        });

        jsonp(this.$element.find('#import_data'), {
            url: '/web/import/import_data',
            data: {
                model: this.model,
                meta: JSON.stringify({
                    skip: lines_to_skip,
                    indices: indices,
                    fields: fields,
                    context: this.context
                })
            }
        }, this.on_import_results);
    },
    on_autodetect_data: function() {
        if(!this.$element.find('#csvfile').val()) { return; }
        jsonp(this.$element.find('#import_data'), {
            url: '/web/import/detect_data'
        }, this.on_import_results);
    },
    on_import_results: function(results) {
        this.$element.find('#result').empty();
        var headers, result_node = this.$element.find("#result");

        if (results['error']) {
            result_node.append(QWeb.render('ImportView.error', {
                'error': results['error']}));
            this.$element.find('fieldset').removeClass('oe-closed');
            return;
        }
        if (results['success']) {
            if (this.widget_parent.widget_parent.active_view == "list") {
                this.widget_parent.reload_content();
            }
            this.stop();
            return;
        }

        if (results['records']) {
            var lines_to_skip = parseInt(this.$element.find('#csv_skip').val(), 10),
                with_headers = this.$element.find('#file_has_headers').prop('checked');
            headers = with_headers ? results.records[0] : null;

            result_node.append(QWeb.render('ImportView.result', {
                'headers': headers,
                'records': lines_to_skip ? results.records.slice(lines_to_skip)
                          : with_headers ? results.records.slice(1)
                          : results.records
            }));
            this.$element.find('fieldset').addClass('oe-closed');
        }
        this.$element.find('form').removeClass('oe-import-no-result');

        this.$element.delegate('.oe-m2o-drop-down-button', 'click', function () {
            $(this).prev('input').focus();
        });

        var self = this;
        this.ready.then(function () {
            var $fields = self.$element.find('.sel_fields').bind('blur', function () {
                if (this.value && !_(self.all_fields).contains(this.value)) {
                    this.value = '';
                }
            }).autocomplete({
                minLength: 0,
                source: self.all_fields,
                change: self.on_check_field_values
            }).focus(function () {
                $(this).autocomplete('search');
            });
            // Column auto-detection
            _(headers).each(function (header, index) {
                var field_name = self.match_column_to_field(header);
                if (field_name) {
                    $fields.eq(index).val(field_name);
                }
            });
            self.on_check_field_values();
        });
    },
    /**
     * Returns the name of the field (nested) matching the provided column name
     *
     * @param {String} name column name to look for
     * @param {Array} [fields] fields to look into for the provided name
     * @returns {String|undefined}
     */
    match_column_to_field: function (name, fields) {
        fields = fields || this.fields;
        var f;
        f = _(fields).detect(function (field) {
            return field.name === name
        });
        if (!f) {
            f = _(fields).detect(function (field) {
                // TODO: levenshtein between header and field.string
                return field.string.toLowerCase() === name.toLowerCase();
            });
        }
        if (f) { return f.name; }

        // if ``name`` is a path (o2m), we need to recurse through its .fields
        var index = name.indexOf('/');
        if (index === -1) { return undefined; }
        // Get the first path section, try to find the matching field
        var column_name = name.substring(0, index);
        f = _(fields).detect(function (field) {
            // field.name for o2m is $foo/id, so we want to match on id
            return field.id === column_name;
        });
        if (!f) {
            f = _(fields).detect(function (field) {
                return field.string.toLowerCase() === column_name.toLowerCase();
            });
        }
        if (!f) { return undefined; }

        // if we found a matching field for the first path section, recurse in
        // its own .fields to try and get the rest of the path matched
        var rest = this.match_column_to_field(
                name.substring(index+1), f.fields);
        if (!rest) { return undefined; }
        return f.id + '/' + rest;
    },
    /**
     * Looks through all the field selections, and tries to find if two
     * (or more) columns were matched to the same model field.
     *
     * Returns a map of the multiply-mapped fields to an array of offending
     * columns (not actually columns, but the inputs containing the same field
     * names).
     *
     * Also has the side-effect of marking the discovered inputs with the class
     * ``duplicate_fld``.
     *
     * @returns {Object<String, Array<String>>} map of duplicate field matches to same-valued inputs
     */
    find_duplicate_fields: function() {
        // Maps values to DOM nodes, in order to discover duplicates
        var values = {}, duplicates = {};
        this.$element.find(".sel_fields").each(function(index, element) {
            var value = element.value;
            var $element = $(element).removeClass('duplicate_fld');
            if (!value) { return; }

            if (!(value in values)) {
                values[value] = element;
            } else {
                var same_valued_field = values[value];
                if (value in duplicates) {
                    duplicates[value].push(element);
                } else {
                    duplicates[value] = [same_valued_field, element];
                }
                $element.add(same_valued_field).addClass('duplicate_fld');
            }
        });
        return duplicates;
    },
    on_check_field_values: function () {
        this.$element.find("#message, #msg").remove();

        var required_valid = this.check_required();

        var duplicates = this.find_duplicate_fields();
        if (_.isEmpty(duplicates)) {
            this.toggle_import_button(required_valid);
        } else {
            var $err = $('<div id="msg" style="color: red;">'+_t("Destination fields should only be selected once, some fields are selected more than once:")+'</div>').insertBefore(this.$element.find('#result'));
            var $dupes = $('<dl>').appendTo($err);
            _(duplicates).each(function(elements, value) {
                $('<dt>').text(value).appendTo($dupes);
                _(elements).each(function(element) {
                    var cell = $(element).closest('td');
                    $('<dd>').text(cell.parent().children().index(cell)).appendTo($dupes);
                });
            });
            this.toggle_import_button(false);
        }

    },
    check_required: function() {
        var self = this;
        if (!self.required_fields.length) { return true; }

        // Resolve field id based on column name, as there may be
        // several ways to provide the value for a given field and
        // thus satisfy the requirement. 
        // (e.g. m2o_id or m2o_id/id columns may be provided)
        var resolve_field_id = function(column_name) {
            var f = _.detect(self.fields, function(field) {
                return field.name === column_name;
            });
            if (!f) { return column_name; };
            return f.id;
        };

        var selected_fields = _(this.$element.find('.sel_fields').get()).chain()
            .pluck('value')
            .compact()
            .map(resolve_field_id)
            .value();

        var missing_fields = _.difference(this.required_fields, selected_fields);
        if (missing_fields.length) {
            this.$element.find("#result").before('<div id="message" style="color:red">' + _t("*Required Fields are not selected :") + missing_fields + '.</div>');
            return false;
        }
        return true;
    },
    stop: function() {
        this.$element.remove();
        this._super();
    }
});
};
