/**
 * @namespace handles editability case for lists, because it depends on form and forms already depends on lists it had to be split out
 */
openerp.web.list_editable = function (openerp) {
    var KEY_RETURN = 13,
        KEY_ESCAPE = 27;

    // editability status of list rows
    openerp.web.ListView.prototype.defaults.editable = null;

    // TODO: not sure second @lends on existing item is correct, to check
    openerp.web.ListView.include(/** @lends openerp.web.ListView# */{
        init: function () {
            var self = this;
            this._super.apply(this, arguments);
            $(this.groups).bind({
                'edit': function (e, id, dataset) {
                    self.do_edit(dataset.index, id, dataset);
                },
                'saved': function () {
                    if (self.groups.get_selection().length) {
                        return;
                    }
                    self.compute_aggregates();
                }
            })
        },
        /**
         * Handles the activation of a record in editable mode (making a record
         * editable), called *after* the record has become editable.
         *
         * The default behavior is to setup the listview's dataset to match
         * whatever dataset was provided by the editing List
         *
         * @param {Number} index index of the record in the dataset
         * @param {Object} id identifier of the record being edited
         * @param {openerp.web.DataSet} dataset dataset in which the record is available
         */
        do_edit: function (index, id, dataset) {
            _.extend(this.dataset, dataset);
        },
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
            this._super(results);
        },
        /**
         * Replace do_add_record to handle editability (and adding new record
         * as an editable row at the top or bottom of the list)
         */
        do_add_record: function () {
            if (this.options.editable) {
                this.groups.new_record();
            } else {
                this._super();
            }
        },
        on_loaded: function (data, grouped) {
            // tree/@editable takes priority on everything else if present.
            this.options.editable = data.fields_view.arch.attrs.editable || this.options.editable;
            return this._super(data, grouped);
        }
    });

    openerp.web.ListView.Groups.include(/** @lends openerp.web.ListView.Groups# */{
        passtrough_events: openerp.web.ListView.Groups.prototype.passtrough_events + " edit saved",
        new_record: function () {
            // TODO: handle multiple children
            this.children[null].new_record();
        }
    });

    openerp.web.ListView.List.include(/** @lends openerp.web.ListView.List */{
        row_clicked: function (event) {
            if (!this.options.editable) {
                return this._super(event);
            }
            this.edit_record($(event.currentTarget).data('id'));
        },
        /**
         * Checks if a record is being edited, and if so cancels it
         */
        cancel_pending_edition: function () {
            var self = this, cancelled = $.Deferred();
            if (!this.edition) {
                cancelled.resolve();
                return cancelled.promise();
            }

            if (this.edition_id != null) {
                this.reload_record(self.records.get(this.edition_id)).then(function () {
                    cancelled.resolve();
                });
            } else {
                cancelled.resolve();
            }
            cancelled.then(function () {
                self.edition_form.stop();
                self.edition_form.$element.remove();
                delete self.edition_form;
                delete self.edition_id;
                delete self.edition;
            });
            return cancelled.promise();
        },
        /**
         * Adapts this list's view description to be suitable to the inner form
         * view of a row being edited.
         *
         * @returns {Object} fields_view_get's view section suitable for putting into form view of editable rows.
         */
        get_form_fields_view: function () {
            // deep copy of view
            var view = $.extend(true, {}, this.group.view.fields_view);
            _(view.arch.children).each(function (widget) {
                widget.attrs.nolabel = true;
                if (widget.tag === 'button') {
                    delete widget.attrs.string;
                }
            });
            view.arch.attrs.col = 2 * view.arch.children.length;
            return view;
        },
        render_row_as_form: function (row) {
            var self = this;
            this.cancel_pending_edition().then(function () {
                var record_id = $(row).data('id');
                var $new_row = $('<tr>', {
                        id: _.uniqueId('oe-editable-row-'),
                        'data-id': record_id,
                        'class': $(row).attr('class') + ' oe_forms',
                        click: function (e) {e.stopPropagation();}
                    })
                    .delegate('button.oe-edit-row-save', 'click', function () {
                        self.save_row();
                    })
                    .delegate('button.oe-edit-row-cancel', 'click', function () {
                        self.cancel_edition();
                    })
                    .delegate('button', 'keyup', function (e) {
                        e.stopImmediatePropagation();
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
                    });
                if (row) {
                    $new_row.replaceAll(row);
                } else if (self.options.editable === 'top') {
                    self.$current.prepend($new_row);
                } else if (self.options.editable) {
                    self.$current.append($new_row);
                }
                self.edition = true;
                self.edition_id = record_id;
                self.edition_form = _.extend(new openerp.web.FormView(
                        self, $new_row.attr('id'), self.dataset, false), {
                    template: 'ListView.row.form',
                    registry: openerp.web.list.form.widgets
                });
                $.when(self.edition_form.on_loaded({fields_view: self.get_form_fields_view()})).then(function () {
                    // put in $.when just in case  FormView.on_loaded becomes asynchronous
                    $new_row.find('td')
                          .addClass('oe-field-cell')
                          .removeAttr('width')
                      .end()
                      .find('td:first').removeClass('oe-field-cell').end()
                      .find('td:last').removeClass('oe-field-cell').end();
                    // pad in case of groupby
                    _(self.columns).each(function (column) {
                        if (column.meta) {
                            $new_row.prepend('<td>');
                        }
                    });

                    self.edition_form.do_show();
                });
            });
        },
        handle_onwrite: function (source_record_id) {
            var self = this;
            var on_write_callback = self.view.fields_view.arch.attrs.on_write;
            if (!on_write_callback) { return; }
            this.dataset.call(on_write_callback, [source_record_id], function (ids) {
                _(ids).each(function (id) {
                    var record = self.records.get(id);
                    if (!record) {
                        // insert after the source record
                        var index = self.records.indexOf(
                            self.records.get(source_record_id)) + 1;
                        record = new openerp.web.list.Record({id: id});
                        self.records.add(record, {at: index});
                        self.dataset.ids.splice(index, 0, id);
                    }
                    self.reload_record(record);
                });
            });
        },
        /**
         * Saves the current row, and triggers the edition of its following
         * sibling if asked.
         *
         * @param {Boolean} [edit_next=false] should the next row become editable
         */
        save_row: function (edit_next) {
            var self = this;
            this.edition_form.do_save(function (result) {
                if (result.created && !self.edition_id) {
                    self.records.add({id: result.result},
                        {at: self.options.editable === 'top' ? 0 : null});
                    self.edition_id = result.result;
                }
                var edited_record = self.records.get(self.edition_id),
                    next_record = self.records.at(
                            self.records.indexOf(edited_record) + 1);

                self.handle_onwrite(self.edition_id);
                self.cancel_pending_edition().then(function () {
                    $(self).trigger('saved', [self.dataset]);
                    if (!edit_next) {
                        return;
                    }
                    if (result.created) {
                        self.new_record();
                        return;
                    }
                    var next_record_id;
                    if (next_record) {
                        next_record_id = next_record.get('id');
                        self.dataset.index = _(self.dataset.ids)
                                .indexOf(next_record_id);
                    } else {
                        self.dataset.index = 0;
                        next_record_id = self.records.at(0).get('id');
                    }
                    self.edit_record(next_record_id);
                });
            }, this.options.editable === 'top');
        },
        /**
         * Cancels the edition of the row for the current dataset index
         */
        cancel_edition: function () {
            this.cancel_pending_edition();
        },
        /**
         * Edits record currently selected via dataset
         */
        edit_record: function (record_id) {
            this.render_row_as_form(
                this.$current.find('[data-id=' + record_id + ']'));
            $(this).trigger(
                'edit',
                [record_id, this.dataset]);
        },
        new_record: function () {
            this.dataset.index = null;
            this.render_row_as_form();
        }
    });
    if (!openerp.web.list) {
        openerp.web.list = {};
    }
    if (!openerp.web.list.form) {
        openerp.web.list.form = {};
    }
    openerp.web.list.form.WidgetFrame = openerp.web.form.WidgetFrame.extend({
        template: 'ListView.row.frame'
    });
    var form_widgets = openerp.web.form.widgets;
    openerp.web.list.form.widgets = form_widgets.clone({
        'frame': 'openerp.web.list.form.WidgetFrame'
    });
    // All form widgets inherit a problematic behavior from
    // openerp.web.form.WidgetFrame: the cell itself is removed when invisible
    // whether it's @invisible or @attrs[invisible]. In list view, only the
    // former should completely remove the cell. We need to override update_dom
    // on all widgets since we can't just hit on widget itself (I think)
    var list_form_widgets = openerp.web.list.form.widgets;
    _(list_form_widgets.map).each(function (widget_path, key) {
        if (key === 'frame') { return; }
        var new_path = 'openerp.web.list.form.' + key;

        openerp.web.list.form[key] = (form_widgets.get_object(key)).extend({
            update_dom: function () {
                this.$element.children().css('visibility', '');
                if (this.modifiers.tree_invisible) {
                    var old_invisible = this.invisible;
                    this.invisible = !!this.modifiers.tree_invisible;
                    this._super();
                    this.invisible = old_invisible;
                } else if (this.invisible) {
                    this.$element.children().css('visibility', 'hidden');
                }
            }
        });
        list_form_widgets.add(key, new_path);
    });
};
