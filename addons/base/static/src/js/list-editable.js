/**
 * @namespace handles editability case for lists, because it depends on form and forms already depends on lists it had to be split out
 */
openerp.base.list.editable = function (openerp) {
    var KEY_RETURN = 13,
        KEY_ESCAPE = 27;

    // editability status of list rows
    openerp.base.ListView.prototype.defaults.editable = null;

    var old_actual_search = openerp.base.ListView.prototype.do_actual_search;
    var old_add_record = openerp.base.ListView.prototype.do_add_record;
    var old_on_loaded = openerp.base.ListView.prototype.on_loaded;
    _.extend(openerp.base.ListView.prototype, {
        /**
         * Sets editability status for the list, based on defaults, view
         * architecture and the provided flag, if any.
         *
         * @param {Boolean} [force] forces the list to editability. Sets new row edition status to "bottom".
         */
        set_editable: function (force) {
            // If ``force``, set editability to bottom
            // otherwise rely on view default
            // view' @editable is handled separately as we have not yet
            // fetched and processed the view at this point.
            this.options.editable = (
                    (force && "bottom")
                    || this.defaults.editable);
        },
        /**
         * Replace do_actual_search to handle editability process
         */
        do_actual_search: function (results) {
            this.set_editable(results.context['set_editable']);
            old_actual_search.call(this, results);
        },
        /**
         * Replace do_add_record to handle editability (and adding new record
         * as an editable row at the top or bottom of the list)
         */
        do_add_record: function () {
            if (this.options.editable) {
                this.groups.new_record();
            } else {
                old_add_record.call(this);
            }
        },
        on_loaded: function (data, grouped) {
            // tree/@editable takes priority on everything else if present.
            this.options.editable = data.fields_view.arch.attrs.editable || this.options.editable;
            return old_on_loaded.call(this, data, grouped);
        }
    });

    _.extend(openerp.base.ListView.Groups.prototype, {
        new_record: function () {
            // TODO: handle multiple children
            this.children[null].new_record();
        }
    });

    var old_list_row_clicked = openerp.base.ListView.List.prototype.row_clicked;
    _.extend(openerp.base.ListView.List.prototype, {
        row_clicked: function (event) {
            if (!this.options.editable) {
                return old_list_row_clicked.call(this, event);
            }
            this.render_row_as_form(event.currentTarget);
        },
        render_row_as_form: function (row) {
            var self = this;
            var $new_row = $('<tr>', {
                    id: _.uniqueId('oe-editable-row-'),
                    'class': $(row).attr('class'),
                    onclick: function (e) {e.stopPropagation();}
                })
                .keyup(function (e) {
                    switch (e.which) {
                        case KEY_RETURN:
                            self.save_row(true);
                            break;
                        case KEY_ESCAPE:
                            self.cancel_edition();
                            break;
                        default:
                            return;
                    }
                })
                .delegate('button.oe-edit-row-save', 'click', function () {
                    self.save_row();
                })
                .delegate('button.oe-edit-row-cancel', 'click', function () {
                    self.cancel_edition();
                });
            if (row) {
                $new_row.replaceAll(row);
            } else if (this.options.editable === 'top') {
                this.$current.prepend($new_row);
            } else if (this.options.editable) {
                this.$current.append($new_row);
            }
            this.edition_form = _.extend(new openerp.base.FormView(
                    null, this.group.view.session, $new_row.attr('id'),
                    this.dataset, false), {
                template: 'ListView.row.form',
                registry: openerp.base.list.form.widgets
            });
            this.edition_form.on_loaded({fields_view: this.get_fields_view()});
            this.edition_form.on_record_loaded.add({
                position: 'last',
                unique: true,
                callback: function () {
                    self.edition_form.$element
                        .find('td')
                            .addClass('oe-field-cell')
                            .removeAttr('width')
                        .end()
                        .find('td:first').removeClass('oe-field-cell').end()
                        .find('td:last').removeClass('oe-field-cell').end();
                }
            });
            this.edition_form.do_show();
        },
        /**
         * Saves the current row, and triggers the edition of its following
         * sibling if asked.
         *
         * @param {Boolean} [edit_next=false] should the next row become editable
         */
        save_row: function (edit_next) {
            var self = this;
            this.edition_form.do_save(function () {
                self.reload_record(self.dataset.index, true).then(function () {
                    self.edition_form.stop();
                    delete self.edition_form;
                    if (edit_next) {
                        self.dataset.next();
                        self.row_clicked({
                            currentTarget: self.$current.children().eq(
                                self.dataset.index)
                        });
                    }
                });
            });
        },
        /**
         * Cancels the edition of the row for the current dataset index
         */
        cancel_edition: function () {
            if (this.dataset.index !== null) {
                this.reload_record(this.dataset.index);
            }
            this.edition_form.stop();
            this.edition_form.$element.remove();
            delete this.edition_form;
        },
        new_record: function () {
            this.dataset.index = null;
            this.render_row_as_form();
        }
    });
    openerp.base.list = {form: {}};
    openerp.base.list.form.WidgetFrame = openerp.base.form.WidgetFrame.extend({
        template: 'ListView.row.frame'
    });
    var form_widgets = openerp.base.form.widgets;
    openerp.base.list.form.widgets = form_widgets.clone({
        'frame': 'openerp.base.list.form.WidgetFrame'
    });
    // All form widgets inherit a problematic behavior from
    // openerp.base.form.WidgetFrame: the cell itself is removed when invisible
    // whether it's @invisible or @attrs[invisible]. In list view, only the
    // former should completely remove the cell. We need to override update_dom
    // on all widgets since we can't just hit on widget itself (I think)
    var list_form_widgets = openerp.base.list.form.widgets;
    _(list_form_widgets.map).each(function (widget_path, key) {
        if (key === 'frame') { return; }
        var new_path = 'openerp.base.list.form.' + key;

        openerp.base.list.form[key] = (form_widgets.get_object(key)).extend({
            update_dom: function () {
                this.$element.children().css('visibility', '');
                if (this.invisible && this.node.attrs.invisible !== '1') {
                    this.$element.children().css('visibility', 'hidden');
                } else {
                    this._super();
                }
            }
        });
        list_form_widgets.add(key, new_path);
    });
};
