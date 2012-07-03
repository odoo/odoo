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
            this.options.editable = true || (
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
            var self = this;
            // tree/@editable takes priority on everything else if present.
            this.options.editable = ! this.options.read_only && (data.arch.attrs.editable || this.options.editable);
            var result = this._super(data, grouped);
            if (this.options.editable || true) {
                this.editor = new instance.web.list.Editor(this);

                var editor_ready = this.editor.prependTo(this.$element).then(function () {
                    self.editor.$element.on('keyup', function (e) {
                        switch (e.which) {
                        case KEY_RETURN:
                            self.saveEdition().then(function (saveInfo) {
                                if (saveInfo.created) {
                                    self.startEdition();
                                    return;
                                }
                                var next_index = self.records.indexOf(saveInfo.record) + 1;
                                if (next_index === self.records.length) {
                                    next_index = 0;
                                }

                                self.startEdition(self.records.at(next_index));
                            });
                            break;
                        case KEY_ESCAPE:
                            self.cancelEdition();
                            break;
                        }
                    });
                });

                return $.when(result, editor_ready);
            }

            return result;
        },
        /**
         * Ensures the editable list is saved (saves any pending edition if
         * needed, or tries to)
         *
         * Returns a deferred to the end of the saving.
         *
         * @returns {$.Deferred}
         */
        ensureSaved: function () {
            if (!this.editor.isEditing()) {
                return $.when();
            }
            return this.saveEdition();
        },
        /**
         * Set up the edition of a record of the list view "inline"
         *
         * @param {instance.web.list.Record} [record] record to edit, leave empty to create a new record
         * @return {jQuery.Deferred}
         */
        startEdition: function (record) {
            var self = this;
            if (!record) {
                record = new instance.web.list.Record();
                this.records.add(record, {
                    at: this.options.editable === 'top' ? 0 : null});
            }
            var $recordRow = this.groups.getRowFor(record);
            var cells = this.getCellsFor($recordRow);
            return this.ensureSaved().pipe(function () {
                return self.withEvent('edit', {
                    record: record.attributes,
                    cancel: false
                }, self.editor.edit,
                [record.attributes, function (field_name, field) {
                    var cell = cells[field_name];
                    if (!cell || field.get('effective_readonly')) {
                        // Readonly fields can just remain the list's, form's
                        // usually don't have backgrounds &al
                        field.set({invisible: true});
                        return;
                    }
                    var $cell = $(cell);
                    var position = $cell.position();

                    field.$element.css({
                        top: position.top,
                        left: position.left,
                        width: $cell.outerWidth(),
                        minHeight: $cell.outerHeight()
                    });
                }],
                [record.attributes]);
            }).then(function () {
                $recordRow.addClass('oe_edition')
            });
        },
        getCellsFor: function ($row) {
            var cells = {};
            $row.children('td').each(function (index, el) {
                cells[el.getAttribute('data-field')] = el
            });
            return cells;
        },
        /**
         * @return {jQuery.Deferred}
         */
        saveEdition: function () {
            var self = this;
            return this.withEvent('save', {
                editor: this.editor,
                form: this.editor.form,
                cancel: false
            }, this.editor.save).pipe(function (attrs) {
                var created = false;
                var record = self.records.get(attrs.id);
                if (!record) {
                    // new record
                    created = true;
                    record = self.records.find(function (r) {
                        return !r.get('id');
                    }).set('id', attrs.id);
                }
                // onwrite callback could be altering & reloading the record
                // which has *just* been saved, so first perform all onwrites
                // then do a final reload of the record
                return self.handleOnWrite(record)
                    .pipe(function () { return self.reload_record(record); })
                    .pipe(function () { return { created: created, record: record };
                });
            });
        },
        /**
         * @return {jQuery.Deferred}
         */
        cancelEdition: function () {
            var self = this;
            return this.withEvent('cancel', {
                editor: this.editor,
                form: this.editor.form,
                cancel: false
            }, this.editor.cancel).then(function (attrs) {
                if (attrs.id) {
                    return self.reload_record(self.records.get(attrs.id));
                }
                var to_delete = self.records.find(function (r) {
                    return !r.get('id');
                });
                if (to_delete) {
                    self.records.remove(to_delete);
                }
            });
        },
        /**
         * Executes an action on the view's editor bracketed by a cancellable
         * event of the name provided.
         *
         * The event name provided will be post-fixed with ``:before`` and
         * ``:after``, the ``event`` parameter will be passed alongside the
         * ``:before`` variant and if the parameter's ``cancel`` key is set to
         * ``true`` the action *will not be called* and the method will return
         * a rejection
         *
         * @param {String} event_name name of the event
         * @param {Object} event event object, provided to ``:before`` sub-event
         * @param {Function} action callable, called with the view's editor as its context
         * @param {Array} [args] supplementary arguments provided to the action
         * @param {Array} [trigger_params] supplementary arguments provided to the ``:after`` sub-event, before anything fetched by the ``action`` function
         * @return {jQuery.Deferred}
         */
        withEvent: function (event_name, event, action, args, trigger_params) {
            var self = this;
            event = event || {};
            this.trigger(event_name + ':before', event);
            if (event.cancel) {
                return $.Deferred().reject();
            }
            return $.when(action.apply(this.editor, args || [])).then(function () {
                self.trigger.apply(self, [event_name + ':after']
                        .concat(trigger_params || [])
                        .concat(_.toArray(arguments)));
            });
        },
        editionView: function (editor) {
            var view = $.extend(true, {}, this.fields_view);
            view.arch.tag = 'form';
            _.extend(view.arch.attrs, {
                'class': 'oe_form_container',
                version: '7.0'
            });
            _(view.arch.children).each(function (widget) {
                var modifiers = JSON.parse(widget.attrs.modifiers || '{}');
                widget.attrs.nolabel = true;
                if (modifiers['tree_invisible'] || widget.tag === 'button') {
                    modifiers.invisible = true;
                }
                widget.attrs.modifiers = JSON.stringify(modifiers);
            });
            return view;
        },
        handleOnWrite: function (source_record) {
            var self = this;
            var on_write_callback = self.fields_view.arch.attrs.on_write;
            if (!on_write_callback) { return $.when(); }
            return this.dataset.call(on_write_callback, [source_record.get('id')])
                .pipe(function (ids) {
                    return $.when.apply(null, _(ids).map(function (id) {
                        var record = self.records.get(id);
                        if (!record) {
                            // insert after the source record
                            var index = self.records.indexOf(source_record) + 1;
                            record = new instance.web.list.Record({id: id});
                            self.records.add(record, {at: index});
                            self.dataset.ids.splice(index, 0, id);
                        }
                        return self.reload_record(record);
                    }));
                });
        },
    });

    instance.web.list.Editor = instance.web.Widget.extend({
        /**
         * @constructs instance.web.list.Editor
         * @extends instance.web.Widget
         *
         * Adapter between listview and formview for editable-listview purposes
         *
         * @param {instance.web.Widget} parent
         * @param {Object} options
         * @param {instance.web.FormView} [options.formView=instance.web.FormView]
         */
        init: function (parent, options) {
            this._super(parent);
            this.options = options || {};
            _.defaults(this.options, {
                formView: instance.web.FormView
            });

            this.record = null;

            this.form = new (this.options.formView)(
                this, this.getParent().dataset, false, {
                    initial_mode: 'edit',
                    $buttons: $(),
                    $pager: $()
            });
        },
        start: function () {
            var self = this;
            var _super = this._super();
            // TODO: getParent() should be delegate defaulting to getParent()
            this.form.embedded_view = this.getParent().editionView(this);
            var form_ready = this.form.appendTo(this.$element).then(
                self.form.proxy('do_hide'));
            return $.when(_super, form_ready);
        },

        isEditing: function () {
            return !!this.record;
        },
        edit: function (record, configureField) {
            var self = this;
            var form = self.form;
            record = _.extend({}, record);
            return form.on_record_loaded(record).pipe(function () {
                return form.do_show({reload: false});
            }).pipe(function () {
                self.record = record;
                // TODO: save on action button?
                _(form.fields).each(function (field, name) {
                    configureField(name, field);
                });
                // TODO: actually focus clicked field (if editable)
                _(form.fields_order).detect(function (name) {
                    // look for first visible field in fields_order, focus it
                    var field = form.fields[name];
                    if (!field.$element.is(':visible')) {
                        return false;
                    }
                    field.focus();
                    return true;
                });
                return form;
            });
        },
        save: function () {
            var self = this;
            return this.form
                .do_save(null, this.getParent().options.editable === 'top')
                .pipe(function (result) {
                    var created = result.created && !self.record.id;
                    if (created) {
                        self.record.id = result.result;
                    }
                    return self.cancel();
                });
        },
        cancel: function () {
            var record = this.record;
            this.record = null;
            if (!this.form.can_be_discarded()) {
                return $.Deferred.reject();
            }
            this.form.do_hide();
            return $.when(record);
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
        ensureSaved: function () {
            return $.when.apply(null,
                _.invoke(
                    _.values(this.children),
                    'ensureSaved'));
        },
        getRowFor: function (record) {
            return _(this.children).chain()
                .invoke('getRowFor', record)
                .compact()
                .first()
                .value();
        }
    });

    instance.web.ListView.List.include(/** @lends instance.web.ListView.List# */{
        init: function () {
            var self = this;
            this._super.apply(this, arguments);
            var selection_handler = _.find(this.$_element.data('events').click, function (h) {
                return h.selector === 'th.oe-record-selector';
            }).handler;
            // TODO: cleaner way to do that?
            this.$_element
                .off('click', 'th.oe-record-selector')
                .on('click', '.oe_edition th.oe-record-selector', function (e) {
                    e.stopImmediatePropagation();
                    self.view.saveEdition();
                })
                .on('click', 'th.oe-record-selector', selection_handler);
        },
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
                this.cancelEdition();
                break;
            }
        },
        render_row_as_form: function (id) {
            return this.view.startEdition(
                    id ? this.records.get(id) : null);
        },
        /**
         * If the current list is being edited, ensures it's saved
         */
        ensureSaved: function () {
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
        cancelEdition: function () {
            this.cancel_pending_edition();
        },
        /**
         * Edits record currently selected via dataset
         */
        edit_record: function (record_id) {
            this.render_row_as_form(record_id);
        },
        new_record: function () {
            this.render_row_as_form();
        },
        /**
         * If a row mapping to the record (@data-id matching the record's id or
         * no @data-id if the record has no id), returns it. Otherwise returns
         * ``null``.
         *
         * @param {Record} record the record to get a row for
         * @return {jQuery|null}
         */
        getRowFor: function (record) {
            var id, $row;
            if (id = record.get('id')) {
                $row = this.$current.children('[data-id=' + id + ']');
            } else {
                $row = this.$current.children(':not([data-id])');
            }
            if ($row.length) {
                return $row;
            }
            return null;
        }
    });
};
