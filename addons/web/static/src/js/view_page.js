openerp.web.page = function (openerp) {
    var _t = openerp.web._t,
       _lt = openerp.web._lt;

    openerp.web.views.add('page', 'openerp.web.PageView');
    openerp.web.PageView = openerp.web.FormView.extend({
        form_template: "PageView",
        display_name: _lt('Page'),
        init: function () {
            this._super.apply(this, arguments);
            this.registry = openerp.web.page.readonly;
        },
        reload: function () {
            if (this.dataset.index == null) {
                this.do_prev_view();
                return $.Deferred().reject().promise();
            }
            return this._super();
        },
        on_loaded: function(data) {
            this._super(data);
            this.$form_header.find('button.oe_form_button_edit').click(this.on_button_edit);
            this.$form_header.find('button.oe_form_button_create').click(this.on_button_create);
            this.$form_header.find('button.oe_form_button_duplicate').click(this.on_button_duplicate);
            this.$form_header.find('button.oe_form_button_delete').click(this.on_button_delete);
        },
        do_show: function() {
            if (this.dataset.index === null) {
                this.dataset.index = this.previous_index || this.dataset.ids.length - 1;
            }
            this._super.apply(this, arguments);
        },
        on_button_edit: function() {
            return this.do_switch_view('form');
        },
        on_button_create: function() {
            this.previous_index = this.dataset.index;
            this.dataset.index = null;
            return this.do_switch_view('form');
        },
        on_button_duplicate: function() {
            var self = this;
            var def = $.Deferred();
            $.when(this.has_been_loaded).then(function() {
                self.dataset.call('copy', [self.datarecord.id, {}, self.dataset.context]).then(function(new_id) {
                    return self.on_created({ result : new_id });
                }).then(function() {
                    return self.do_switch_view('form');
                }).then(function() {
                    def.resolve();
                });
            });
            return def.promise();
        },
        on_button_delete: function() {
            var self = this;
            var def = $.Deferred();
            $.when(this.has_been_loaded).then(function() {
                if (self.datarecord.id && confirm(_t("Do you really want to delete this record?"))) {
                    self.dataset.unlink([self.datarecord.id]).then(function() {
                        self.on_pager_action('next');
                        def.resolve();
                    });
                } else {
                    $.async_when().then(function () {
                        def.reject();
                    })
                }
            });
            return def.promise();
        }
    });

    /** @namespace */
    openerp.web.page = {};

    openerp.web.page.WidgetFrameReadonly = openerp.web.form.WidgetFrame.extend({
        template: 'WidgetFrame.readonly'
    });
    openerp.web.page.FieldReadonly = openerp.web.form.Field.extend({

    });
    openerp.web.page.FieldCharReadonly = openerp.web.page.FieldReadonly.extend({
        template: 'FieldChar.readonly',
        init: function(view, node) {
            this._super(view, node);
            this.password = this.node.attrs.password === 'True' || this.node.attrs.password === '1';
        },
        set_value: function (value) {
            this._super.apply(this, arguments);
            var show_value = openerp.web.format_value(value, this, '');
            if (this.password) {
                show_value = new Array(show_value.length + 1).join('*');
            }
            this.$element.find('div').text(show_value);
            return show_value;
        }
    });
    openerp.web.page.FieldFloatReadonly = openerp.web.page.FieldCharReadonly.extend({
        init: function (view, node) {
            this._super(view, node);
            if (node.attrs.digits) {
                this.digits = py.eval(node.attrs.digits).toJSON();
            } else {
                this.digits = view.fields_view.fields[node.attrs.name].digits;
            }
        }
    });
    openerp.web.page.FieldURIReadonly = openerp.web.page.FieldCharReadonly.extend({
        template: 'FieldURI.readonly',
        scheme: null,
        format_value: function (value) {
            return value;
        },
        set_value: function (value) {
            if (!value) {
                this.$element.find('a').text('').attr('href', '#');
                return;
            }
            this.$element.find('a')
                    .attr('href', this.scheme + ':' + value)
                    .text(this.format_value(value));
        }
    });
    openerp.web.page.FieldEmailReadonly = openerp.web.page.FieldURIReadonly.extend({
        scheme: 'mailto'
    });
    openerp.web.page.FieldUrlReadonly = openerp.web.page.FieldURIReadonly.extend({
        set_value: function (value) {
            if (!value) {
                this.$element.find('a').text('').attr('href', '#');
                return;
            }
            var s = /(\w+):(.+)/.exec(value);
            if (!s) {
                value = "http://" + value;
            }
            this.$element.find('a').attr('href', value).text(value);
        }
    });
    openerp.web.page.FieldBooleanReadonly = openerp.web.form.FieldBoolean.extend({
        update_dom: function() {
            this._super.apply(this, arguments);
            this.$element.find('input').prop('disabled', true);
        }
    });
    openerp.web.page.FieldSelectionReadonly = openerp.web.page.FieldReadonly.extend({
        template: 'FieldChar.readonly',
        init: function(view, node) {
            // lifted straight from r/w version
            var self = this;
            this._super(view, node);
            this.values = _.clone(this.field.selection);
            _.each(this.values, function(v, i) {
                if (v[0] === false && v[1] === '') {
                    self.values.splice(i, 1);
                }
            });
            this.values.unshift([false, '']);
        },
        set_value: function (value) {
            value = value === null ? false : value;
            value = value instanceof Array ? value[0] : value;
            var option = _(this.values)
                .detect(function (record) { return record[0] === value; });
            this._super(value);
            this.$element.find('div').text(option ? option[1] : this.values[0][1]);
        }
    });
    openerp.web.page.FieldMany2OneReadonly = openerp.web.page.FieldURIReadonly.extend({
        set_value: function (value) {
            value = value || null;
            this.invalid = false;
            var self = this;
            this.value = value;
            self.update_dom();
            self.on_value_changed();
            var real_set_value = function(rval) {
                self.value = rval;
                self.$element.find('a')
                     .unbind('click')
                     .text(rval ? rval[1] : '')
                     .click(function () {
                        self.do_action({
                            type: 'ir.actions.act_window',
                            res_model: self.field.relation,
                            res_id: self.value[0],
                            context: self.build_context(),
                            views: [[false, 'page'], [false, 'form']],
                            target: 'current'
                        });
                        return false;
                     });
            };
            if (value && !(value instanceof Array)) {
                new openerp.web.DataSetStatic(
                        this, this.field.relation, self.build_context())
                    .name_get([value], function(data) {
                        real_set_value(data[0]);
                });
            } else {
                $.async_when().then(function() {real_set_value(value);});
            }
        },
        get_value: function() {
            if (!this.value) {
                return false;
            } else if (this.value instanceof Array) {
                return this.value[0];
            } else {
                return this.value;
            }
        }
    });
    openerp.web.page.FieldReferenceReadonly = openerp.web.page.FieldMany2OneReadonly.extend({
        set_value: function (value) {
            if (!value) {
                return this._super(null);
            }
            var reference = value.split(',');
            this.field.relation = reference[0];
            var id = parseInt(reference[1], 10);
            return this._super(id);
        },
        get_value: function () {
            if (!this.value) {
                return null;
            }
            var id;
            if (typeof this.value === 'number') {
                // name_get has not run yet
                id = this.value;
            } else {
                id = this.value[0];
            }
            return _.str.sprintf('%s,%d', this.field.relation, id);
        }
    });

    openerp.web.page.FieldMany2ManyReadonly = openerp.web.form.FieldMany2Many.extend({
        force_readonly: true
    });
    openerp.web.page.FieldOne2ManyReadonly = openerp.web.form.FieldOne2Many.extend({
        force_readonly: true
    });
    openerp.web.page.FieldBinaryImageReaonly = openerp.web.form.FieldBinaryImage.extend({
        update_dom: function() {
            this._super.apply(this, arguments);
            this.$element.find('.oe-binary').hide();
        }
    });
    openerp.web.page.FieldBinaryFileReadonly = openerp.web.form.FieldBinary.extend({
        template: 'FieldURI.readonly',
        start: function() {
            this._super.apply(this, arguments);
            var self = this;
            this.$element.find('a').click(function() {
                if (self.value) {
                    self.on_save_as();
                }
                return false;
            });
        },
        set_value: function(value) {
            this._super.apply(this, arguments);
            this.$element.find('a').show(!!value);
            if (value) {
                var show_value = _t("Download") + " " + (this.view.datarecord[this.node.attrs.filename] || '');
                this.$element.find('a').text(show_value);
            }
        }
    });
    openerp.web.page.readonly = openerp.web.form.widgets.extend({
        'frame': 'openerp.web.page.WidgetFrameReadonly',
        'char': 'openerp.web.page.FieldCharReadonly',
        'id': 'openerp.web.page.FieldCharReadonly',
        'email': 'openerp.web.page.FieldEmailReadonly',
        'url': 'openerp.web.page.FieldUrlReadonly',
        'text': 'openerp.web.page.FieldCharReadonly',
        'date': 'openerp.web.page.FieldCharReadonly',
        'datetime': 'openerp.web.page.FieldCharReadonly',
        'selection' : 'openerp.web.page.FieldSelectionReadonly',
        'many2one': 'openerp.web.page.FieldMany2OneReadonly',
        'many2many' : 'openerp.web.page.FieldMany2ManyReadonly',
        'one2many' : 'openerp.web.page.FieldOne2ManyReadonly',
        'one2many_list' : 'openerp.web.page.FieldOne2ManyReadonly',
        'reference': 'openerp.web.page.FieldReferenceReadonly',
        'boolean': 'openerp.web.page.FieldBooleanReadonly',
        'float': 'openerp.web.page.FieldFloatReadonly',
        'integer': 'openerp.web.page.FieldCharReadonly',
        'float_time': 'openerp.web.page.FieldCharReadonly',
        'binary': 'openerp.web.page.FieldBinaryFileReadonly',
        'image': 'openerp.web.page.FieldBinaryImageReaonly'
    });
};
