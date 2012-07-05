/**
 * handles editability case for lists, because it depends on form and forms already depends on lists it had to be split out
 * @namespace
 */
openerp.web.list_editable = function (instance) {
    var KEY_RETURN = 13,
        KEY_ESCAPE = 27;
    var QWeb = instance.web.qweb;

    // editability status of list rows
    instance.web.ListView.prototype.defaults.editable = null;

    // TODO: not sure second @lends on existing item is correct, to check
    instance.web.ListView.include(/** @lends instance.web.ListView# */{
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
                    self.configure_pager(self.dataset);
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
         * @param {instance.web.DataSet} dataset dataset in which the record is available
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
                    ! this.options.read_only && ((force && "bottom") || this.defaults.editable));
        },
        /**
         * Replace do_search to handle editability process
         */
        do_search: function(domain, context, group_by) {
            this.set_editable(context['set_editable']);
            this._super.apply(this, arguments);
        },
        /**
         * Replace do_add_record to handle editability (and adding new record
         * as an editable row at the top or bottom of the list)
         */
        do_add_record: function () {
            if (this.options.editable) {
                this.$element.find('table:first').show();
                this.$element.find('.oe_view_nocontent').remove();
                this.groups.new_record();
            } else {
                this._super();
            }
        },
        on_loaded: function (data, grouped) {
            // tree/@editable takes priority on everything else if present.
            this.options.editable = ! this.options.read_only && (data.arch.attrs.editable || this.options.editable);
            return this._super(data, grouped);
        },
        /**
         * Ensures the editable list is saved (saves any pending edition if
         * needed, or tries to)
         *
         * Returns a deferred to the end of the saving.
         *
         * @returns {$.Deferred}
         */
        ensure_saved: function () {
            return this.groups.ensure_saved();
        }
    });

    instance.web.ListView.Groups.include(/** @lends instance.web.ListView.Groups# */{
        passtrough_events: instance.web.ListView.Groups.prototype.passtrough_events + " edit saved",
        new_record: function () {
            // TODO: handle multiple children
            this.children[null].new_record();
        },
        /**
         * Ensures descendant editable List instances are all saved if they have
         * pending editions.
         *
         * @returns {$.Deferred}
         */
        ensure_saved: function () {
            return $.when.apply(null,
                _.invoke(
                    _.values(this.children),
                    'ensure_saved'));
        }
    });

    instance.web.ListView.List.include(/** @lends instance.web.ListView.List# */{
        row_clicked: function (event) {
            if (!this.options.editable) {
                return this._super.apply(this, arguments);
            }
            this.edit_record($(event.currentTarget).data('id'));
        },
        /**
         * Checks if a record is being edited, and if so cancels it
         */
        cancel_pending_edition: function () {
            var self = this, cancelled;
            if (!this.edition) {
                return $.when();
            }

            if (this.edition_id) {
                cancelled = this.reload_record(this.records.get(this.edition_id));
            } else {
                cancelled = $.when();
            }
            cancelled.then(function () {
                self.view.unpad_columns();
                self.edition_form.destroy();
                self.edition_form.$element.remove();
                delete self.edition_form;
                self.dataset.index = null;
                delete self.edition_id;
                delete self.edition;
            });
            this.pad_table_to(5);
            return cancelled;
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
        on_row_keyup: function (e) {
            var self = this;
            switch (e.which) {
            case KEY_RETURN:
                $(e.target).blur();
                e.preventDefault();
                //e.stopImmediatePropagation();
                setTimeout(function () {
                    self.save_row().then(function (result) {
                        if (result.created) {
                            self.new_record();
                            return;
                        }

                        var next_record_id,
                            next_record = self.records.at(
                                    self.records.indexOf(result.edited_record) + 1);
                        if (next_record) {
                            next_record_id = next_record.get('id');
                            self.dataset.index = _(self.dataset.ids)
                                    .indexOf(next_record_id);
                        } else {
                            self.dataset.index = 0;
                            next_record_id = self.records.at(0).get('id');
                        }
                        self.edit_record(next_record_id);
                    }, 0);
                });
                break;
            case KEY_ESCAPE:
                this.cancel_edition();
                break;
            }
        },
        render_row_as_form: function (row) {
            var self = this;
            return this.ensure_saved().pipe(function () {
                var record_id = $(row).data('id');
                var $new_row = $('<tr>', {
                        id: _.uniqueId('oe-editable-row-'),
                        'data-id': record_id,
                        'class': (row ? $(row).attr('class') : ''),
                        click: function (e) {e.stopPropagation();}
                    })
                    .addClass('oe_form oe_form_container')
                    .delegate('button.oe_list_edit_row_save', 'click', function () {
                        self.save_row();
                    })
                    .delegate('button', 'keyup', function (e) {
                        e.stopImmediatePropagation();
                    })
                    .keyup(function () {
                        return self.on_row_keyup.apply(self, arguments); })
                    .keydown(function (e) { e.stopPropagation(); })
                    .keypress(function (e) {
                        if (e.which === KEY_RETURN) {
                            return false;
                        }
                    });

                if (row) {
                    $new_row.replaceAll(row);
                } else if (self.options.editable) {
                    var $last_child = self.$current.children('tr:last');
                    if (self.records.length) {
                        if (self.options.editable === 'top') {
                            $new_row.insertBefore(
                                self.$current.children('[data-id]:first'));
                        } else {
                            $new_row.insertAfter(
                                self.$current.children('[data-id]:last'));
                        }
                    } else {
                        $new_row.prependTo(self.$current);
                    }
                    if ($last_child.is(':not([data-id])')) {
                        $last_child.remove();
                    }
                }
                self.edition = true;
                self.edition_id = record_id;
                self.dataset.index = _(self.dataset.ids).indexOf(record_id);
                if (self.dataset.index === -1) {
                    self.dataset.index = null;
                }
                self.edition_form = _.extend(new instance.web.ListEditableFormView(self.view, self.dataset, false), {
                    $element: $new_row,
                    editable_list: self
                });
                // put in $.when just in case  FormView.on_loaded becomes asynchronous
                return $.when(self.edition_form.on_loaded(self.get_form_fields_view())).then(function () {
                    $new_row.find('> td')
                      .end()
                      .find('td:last').removeClass('oe_list_field_cell').end();
                    // pad in case of groupby
                    _(self.columns).each(function (column) {
                        if (column.meta) {
                            $new_row.prepend('<td>');
                        }
                    });
                    // Add column for the save, if
                    // there is none in the list
                    if (!self.options.deletable) {
                        self.view.pad_columns(
                            1, {except: $new_row});
                    }

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
                        record = new instance.web.list.Record({id: id});
                        self.records.add(record, {at: index});
                        self.dataset.ids.splice(index, 0, id);
                    }
                    self.reload_record(record);
                });
            });
        },
        /**
         * Saves the current row, and returns a Deferred resolving to an object
         * with the following properties:
         *
         * ``created``
         *   Boolean flag indicating whether the record saved was being created
         *   (``true`` or edited (``false``)
         * ``edited_record``
         *   The result of saving the record (either the newly created record,
         *   or the post-edition record), after insertion in the Collection if
         *   needs be.
         *
         * @returns {$.Deferred<{created: Boolean, edited_record: Record}>}
         */
        save_row: function () {
            //noinspection JSPotentiallyInvalidConstructorUsage
            var self = this;
            return this.edition_form
                .do_save(null, this.options.editable === 'top')
                .pipe(function (result) {
                    if (result.created && !self.edition_id) {
                        self.records.add({id: result.result},
                            {at: self.options.editable === 'top' ? 0 : null});
                        self.edition_id = result.result;
                    }
                    var edited_record = self.records.get(self.edition_id);

                    return $.when(
                        self.handle_onwrite(self.edition_id),
                        self.cancel_pending_edition().then(function () {
                            $(self).trigger('saved', [self.dataset]);
                        })).pipe(function () {
                            return {
                                created: result.created || false,
                                edited_record: edited_record
                            };
                        });
                });
        },
        /**
         * If the current list is being edited, ensures it's saved
         */
        ensure_saved: function () {
            if (this.edition) {
                // kinda-hack-ish: if the user has entered data in a field,
                // oe_form_dirty will be set on the form so save, otherwise
                // discard the current (entirely empty) line
                if (this.edition_form.$element.is('.oe_form_dirty')) {
                    return this.save_row();
                }
                return this.cancel_pending_edition();
            }
            //noinspection JSPotentiallyInvalidConstructorUsage
            return $.when();
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
            this.render_row_as_form();
        },
        render_record: function (record) {
            var index = this.records.indexOf(record),
                 self = this;
            // FIXME: context dict should probably be extracted cleanly
            return QWeb.render('ListView.row', {
                columns: this.columns,
                options: this.options,
                record: record,
                row_parity: (index % 2 === 0) ? 'even' : 'odd',
                view: this.view,
                render_cell: function () {
                    return self.render_cell.apply(self, arguments); },
                edited: !!this.edition_form
            });
        }
    });
    
    instance.web.ListEditableFormView = instance.web.FormView.extend({
        init: function() {
            this._super.apply(this, arguments);
            this.rendering_engine = new instance.web.ListEditableRenderingEngine(this);
            this.options.initial_mode = "edit";
        },
        renderElement: function() {}
    });
    
    instance.web.ListEditableRenderingEngine = instance.web.form.FormRenderingEngineInterface.extend({
        init: function(view) {
            this.view = view;
        },
        set_fields_view: function(fields_view) {
            this.fvg = fields_view;
        },
        set_tags_registry: function(tags_registry) {
            this.tags_registry = tags_registry;
        },
        set_fields_registry: function(fields_registry) {
            this.fields_registry = fields_registry;
        },
        render_to: function($element) {
            var self = this;
    
            var xml = instance.web.json_node_to_xml(this.fvg.arch);
            var $xml = $(xml);
            
            if (this.view.editable_list.options.selectable)
                $("<td>").appendTo($element);
                
            $xml.children().each(function(i, el) {
                var modifiers = JSON.parse($(el).attr("modifiers") || "{}");
                var $td = $("<td>");
                if (modifiers.tree_invisible === true)
                    $td.hide();
                var tag_name = el.tagName.toLowerCase();
                var w;
                if (tag_name === "field") {
                    var name = $(el).attr("name");
                    var key = $(el).attr('widget') || self.fvg.fields[name].type;
                    var obj = self.view.fields_registry.get_object(key);
                    w = new (obj)(self.view, instance.web.xml_to_json(el));
                    self.view.register_field(w, $(el).attr("name"));
                } else {
                    var obj = self.tags_registry.get_object(tag_name);
                    w = new (obj)(self.view, instance.web.xml_to_json(el));
                }
                w.appendTo($td);
                $td.appendTo($element);
            });
            $(QWeb.render('ListView.row.save')).appendTo($element);
        },
    });
};
