openerp.base_import = function (instance) {
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;
    var _lt = instance.web._lt;

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

    // if true, the 'Import', 'Export', etc... buttons will be shown
    instance.web.ListView.prototype.defaults.import_enabled = true;
    instance.web.ListView.include({
        on_loaded: function () {
            var self = this;
            var add_button = false;
            if (!this.$buttons) {
                add_button = true;
            }
            this._super.apply(this, arguments);
            if(add_button) {
                this.$buttons.on('click', '.oe_list_button_import', function() {
                    self.do_action({
                        type: 'ir.actions.client',
                        tag: 'import',
                        params: {
                            model: self.dataset.model
                        }
                    });
                    return false;
                });
            }
        }
    });

    instance.web.client_actions.add(
        'import', 'instance.web.DataImport');
    instance.web.DataImport = instance.web.Widget.extend({
        template: 'ImportView',
        opts: [
            {name: 'encoding', label: _lt("Encoding:"), value: 'utf-8'},
            {name: 'separator', label: _lt("Separator:"), value: ','},
            {name: 'quoting', label: _lt("Quoting:"), value: '"'}
        ],
        events: {
            // 'change .oe_import_grid input': 'import_dryrun',
            'change input.oe_import_file': 'file_update',
            'change input.oe_import_has_header, .oe_import_options input': 'settings_updated',
            'click a.oe_import_csv': function (e) {
                e.preventDefault();
            },
            'click a.oe_import_export': function (e) {
                e.preventDefault();
            },
            'click a.oe_import_toggle': function (e) {
                e.preventDefault();
                var $el = $(e.target);
                ($el.next().length
                        ? $el.next()
                        : $el.parent().next())
                    .toggle();
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
                this.do_action(_.extend(action, {target: 'new'}));
            },
            // buttons
            'click .oe_import_validate': 'import_dryrun',
            'click .oe_import_import': 'do_import',
            'click .oe_import_cancel': function (e) {
                e.preventDefault();
                this.exit();
            }
        },
        init: function (parent, params) {
            this._super.apply(this, arguments);
            this.res_model = params.model;
            // import object id
            this.id = null;
            this.Import = new instance.web.Model('base_import.import');
        },
        start: function () {
            var self = this;

            return $.when(
                this._super(),
                this.Import.call('create', [{
                    'res_model': this.res_model
                }]).then(function (id) {
                    self.id = id;
                    self.$('input[name=import_id]').val(id);
                })
            )
        },

        import_options: function () {
            var self = this;
            var options = {
                headers: this.$('input.oe_import_has_header').prop('checked')
            };
            _(this.opts).each(function (opt) {
                options[opt.name] =
                    self.$('input.oe_import_' + opt.name).val();
            });
            return options;
        },

        //- File & settings change section
        file_update: function (e) {
            this.$('.oe_import_button').prop('disabled', true);
            if (!this.$('input.oe_import_file').val()) { return; }

            this.$el.removeClass('oe_import_preview oe_import_error');
            jsonp(this.$el, {
                url: '/base_import/set_file'
            }, this.proxy('settings_updated'));
        },
        settings_updated: function () {
            this.$el.addClass('oe_import_with_file');
            // TODO: test that write // succeeded?
            this.Import.call(
                'parse_preview', [this.id, this.import_options()])
                .then(this.proxy('preview'));
        },
        preview: function (result) {
            this.$el.removeClass('oe_import_preview_error oe_import_error');
            this.$el.toggleClass(
                'oe_import_noheaders',
                !this.$('input.oe_import_has_header').prop('checked'));
            if (result.error) {
                this.$('.oe_import_options').show();
                this.$el.addClass('oe_import_preview_error oe_import_error');
                this.$('.oe_import_error_report').html(
                        QWeb.render('ImportView.preview.error', result))
                    .get(0).scrollIntoView();
                return;
            }
            this.$('.oe_import_button').prop('disabled', false);
            this.$el.addClass('oe_import_preview');
            this.$('table').html(QWeb.render('ImportView.preview', result));

            if (result.headers.length === 1) {
                this.$('.oe_import_options').show();
                this.render_import_result([{
                    type: 'warning',
                    message: _t("A single column was found in the file, this often means the file separator is incorrect")
                }]);
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
            $fields.select2({
                allowClear: true,
                minimumInputLength: 0,
                data: data,
                initSelection: function (element, callback) {
                    var default_value = element.val();
                    if (!default_value) {
                        callback('');
                        return;
                    }

                    callback(item_finder(default_value));
                },

                width: 'resolve',
                dropdownCssClass: 'oe_import_selector'
            });
            //this.import_dryrun();
        },
        generate_fields_completion: function (root) {
            var basic = [];
            var regulars = [];
            var o2m = [];
            function traverse(field, ancestors, collection) {
                var subfields = field.fields;
                var field_path = ancestors.concat(field);
                var label = _(field_path).pluck('string').join(' / ');
                var id = _(field_path).pluck('name').join('/');

                // If non-relational, m2o or m2m, collection is regulars
                if (!collection) {
                    if (field.name === 'id') {
                        collection = basic
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

                for(var i=0, end=subfields.length; i<end; ++i) {
                    traverse(subfields[i], field_path, collection);
                }
            }
            _(root.fields).each(function (field) {
                traverse(field, []);
            });

            var cmp = function (field1, field2) {
                return field1.text.localeCompare(field2.text);

            };
            regulars.sort(cmp);
            o2m.sort(cmp);
            return basic.concat([
                { text: _t("Normal Fields"), children: regulars },
                { text: _t("Relation Fields"), children: o2m }
            ]);
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
        call_import: function (options) {
            var fields = this.$('.oe_import_fields input.oe_import_match_field').map(function (index, el) {
                return $(el).select2('val') || false;
            }).get();
            return this.Import.call(
                'do', [this.id, fields, this.import_options()], options);
        },
        import_dryrun: function () {
            return this.call_import({ dryrun: true })
                .then(this.proxy('render_import_result'));
        },
        do_import: function () {
            var self = this;
            return this.call_import({ dryrun: false }).then(function (message) {
                if (!_.any(message, function (message) {
                        return message.type === 'error' })) {
                    self.exit();
                    return;
                }
                self.render_import_result(message);
            });
        },
        exit: function () {
            this.do_action({
                type: 'ir.actions.client',
                tag: 'history_back'
            });
        },
        render_import_result: function (message) {
            if (_.isEmpty(message)) {
                this.$('.oe_import_import').addClass('oe_highlight');
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
                        ].join('')
                    },
                })).get(0).scrollIntoView();
        },
    });
};
