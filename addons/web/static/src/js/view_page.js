openerp.web.page = function (openerp) {
    var _t = openerp.web._t;
    var QWeb = openerp.web.qweb;

    openerp.web.views.add('page', 'openerp.web.PageView');
    openerp.web.PageView = openerp.web.FormView.extend({
        form_template: "PageView",
        init: function () {
            this._super.apply(this, arguments);
            this.registry = openerp.web.form.readonly;
        },
        on_loaded: function(data) {
            this._super(data);
            this.$form_header.find('button.oe_form_button_edit').click(this.on_button_edit);
            this.$form_header.find('button.oe_form_button_create').click(this.on_button_create);
            this.$form_header.find('button.oe_form_button_duplicate').click(this.on_button_duplicate);
            this.$form_header.find('button.oe_form_button_delete').click(this.on_button_delete);
        },
        on_button_edit: function() {
            return this.do_switch_view('form');
        },
        on_button_create: function() {
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
                    setTimeout(function () {
                        def.reject();
                    }, 0)
                }
            });
            return def.promise();
        }
    });
    openerp.web.form.FieldReadonly = openerp.web.form.Field.extend({

    });
    openerp.web.form.FieldCharReadonly = openerp.web.form.FieldReadonly.extend({
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
    openerp.web.form.FieldURIReadonly = openerp.web.form.FieldCharReadonly.extend({
        template: 'FieldURI.readonly',
        scheme: null,
        set_value: function (value) {
            var displayed = this._super.apply(this, arguments);
            this.$element.find('a')
                    .attr('href', this.scheme + ':' + displayed)
                    .text(displayed);
        }
    });
    openerp.web.form.FieldEmailReadonly = openerp.web.form.FieldURIReadonly.extend({
        scheme: 'mailto'
    });
    openerp.web.form.FieldUrlReadonly = openerp.web.form.FieldURIReadonly.extend({
        set_value: function (value) {
            var s = /(\w+):(.+)/.exec(value);
            if (!s || !(s[1] === 'http' || s[1] === 'https')) { return; }
            this.scheme = s[1];
            this._super(s[2]);
        }
    });
    openerp.web.form.FieldBooleanReadonly = openerp.web.form.FieldCharReadonly.extend({
        set_value: function (value) {
            this._super(value ? '\u2611' : '\u2610');
        }
    });
    openerp.web.form.FieldSelectionReadonly = openerp.web.form.FieldReadonly.extend({
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
    openerp.web.form.FieldMany2OneReadonly = openerp.web.form.FieldURIReadonly.extend({
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
                setTimeout(function() {real_set_value(value);}, 0);
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
    
    openerp.web.form.FieldMany2ManyReadonly = openerp.web.form.FieldMany2Many.extend({
        force_readonly: true
    });
    openerp.web.form.FieldOne2ManyReadonly = openerp.web.form.FieldOne2Many.extend({
        force_readonly: true
    });
    openerp.web.form.readonly = openerp.web.form.widgets.clone({
        'char': 'openerp.web.form.FieldCharReadonly',
        'email': 'openerp.web.form.FieldEmailReadonly',
        'url': 'openerp.web.form.FieldUrlReadonly',
        'text': 'openerp.web.form.FieldCharReadonly',
        'text_wiki' : 'openerp.web.form.FieldCharReadonly',
        'date': 'openerp.web.form.FieldCharReadonly',
        'datetime': 'openerp.web.form.FieldCharReadonly',
        'selection' : 'openerp.web.form.FieldSelectionReadonly',
        'many2one': 'openerp.web.form.FieldMany2OneReadonly',
        'many2many' : 'openerp.web.form.FieldMany2ManyReadonly',
        'one2many' : 'openerp.web.form.FieldOne2ManyReadonly',
        'one2many_list' : 'openerp.web.form.FieldOne2ManyReadonly',
        'boolean': 'openerp.web.form.FieldBooleanReadonly',
        'float': 'openerp.web.form.FieldCharReadonly',
        'integer': 'openerp.web.form.FieldCharReadonly',
        'float_time': 'openerp.web.form.FieldCharReadonly'
    });
};
