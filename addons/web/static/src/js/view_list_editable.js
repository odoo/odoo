/**
 * handles editability case for lists, because it depends on form and forms already depends on lists it had to be split out
 * @namespace
 */
openerp.web.list_editable = function (instance) {
    // editability status of list rows
    instance.web.ListView.prototype.defaults.editable = null;

    // TODO: not sure second @lends on existing item is correct, to check
    instance.web.ListView.include(/** @lends instance.web.ListView# */{
        init: function () {
            var self = this;
            this._super.apply(this, arguments);

            this.editor = this.makeEditor();
            // Stores records of {field, cell}, allows for re-rendering fields
            // depending on cell state during and after resize events
            this.fields_for_resize = [];
            instance.web.bus.on('resize', this, this.resizeFields);

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
            });

            this.on('edit:after', this, function () {
                self.$element.add(self.$buttons).addClass('oe_editing');
            });
            this.on('save:after cancel:after', this, function () {
                self.$element.add(self.$buttons).removeClass('oe_editing');
            });
        },
        destroy: function () {
            instance.web.bus.off('resize', this, this.resizeFields);
            this._super();
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
            // TODO: fix handling of editability status to be simpler & clearer & more coherent
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
                this.startEdition();
            } else {
                this._super();
            }
        },
        on_loaded: function (data, grouped) {
            var self = this;
            if (this.editor) {
                this.editor.destroy();
            }
            // tree/@editable takes priority on everything else if present.
            this.options.editable = ! this.options.read_only && (data.arch.attrs.editable || this.options.editable);
            var result = this._super(data, grouped);
            if (this.options.editable) {
                // FIXME: any hook available to ensure this is only done once?
                this.$buttons
                    .off('click', '.oe_list_save')
                    .on('click', '.oe_list_save', this.proxy('saveEdition'))
                    .off('click', '.oe_list_discard')
                    .on('click', '.oe_list_discard', function (e) {
                        e.preventDefault();
                        self.cancelEdition();
                    });
                this.$element
                    .off('click', 'tbody td:not(.oe_list_field_cell)')
                    .on('click', 'tbody td:not(.oe_list_field_cell)', function () {
                        if (!self.editor.isEditing()) {
                            self.startEdition();
                        }
                    });
                // Editor is not restartable due to formview not being
                // restartable
                this.editor = this.makeEditor();
                var editor_ready = this.editor.prependTo(this.$element)
                    .then(this.proxy('setupEvents'));

                return $.when(result, editor_ready);
            }

            return result;
        },
        /**
         * Builds a new editor object
         *
         * @return {instance.web.list.Editor}
         */
        makeEditor: function () {
            return new instance.web.list.Editor(this);
        },
        do_button_action: function () {
            var self = this, args = arguments;
            this.ensureSaved().then(function () {
                self.handleButton.apply(self, args);
            });
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
            var item = false;
            if (record) {
                item = record.attributes;
            } else {
                var attrs = {id: false};
                _(this.columns).chain()
                    .filter(function (x) { return x.tag === 'field'})
                    .pluck('name')
                    .each(function (field) { attrs[field] = false; });
                record = new instance.web.list.Record(attrs);
                this.records.add(record, {
                    at: this.isPrependOnCreate() ? 0 : null});
            }
            var $recordRow = this.groups.getRowFor(record);
            var cells = this.getCellsFor($recordRow);

            return this.ensureSaved().pipe(function () {
                self.fields_for_resize.splice(0, self.fields_for_resize.length);
                return self.withEvent('edit', {
                    record: record.attributes,
                    cancel: false
                }, function () {
                    return self.editor.edit(item, function (field_name, field) {
                        var cell = cells[field_name];
                        if (!cell || field.get('effective_readonly')) {
                            // Readonly fields can just remain the list's, form's
                            // usually don't have backgrounds &al
                            field.set({invisible: true});
                            return;
                        }

                        self.fields_for_resize.push({field: field, cell: cell});
                    }).pipe(function () {
                        $recordRow.addClass('oe_edition');
                        self.resizeFields();
                        return record.attributes;
                    });
                });
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
         * If currently editing a row, resizes all registered form fields based
         * on the corresponding row cell
         */
        resizeFields: function () {
            if (!this.editor.isEditing()) { return; }
            for(var i=0, len=this.fields_for_resize.length; i<len; ++i) {
                var item = this.fields_for_resize[i];
                this.resizeField(item.field, item.cell);
            }
        },
        /**
         * Resizes a field's root element based on the corresponding cell of
         * a listview row
         *
         * @param {instance.web.form.AbstractField} field
         * @param {jQuery} cell
         */
        resizeField: function (field, cell) {
            var $cell = $(cell);
            var position = $cell.position();

            field.$element.css({
                top: position.top,
                left: position.left,
                width: $cell.outerWidth(),
                minHeight: $cell.outerHeight()
            });
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
            }, function () {
                return this.editor.save().pipe(function (attrs) {
                    var created = false;
                    var record = self.records.get(attrs.id);
                    if (!record) {
                        // new record
                        created = true;
                        record = self.records.find(function (r) {
                            return !r.get('id');
                        }).set('id', attrs.id);
                    }
                    // onwrite callback could be altering & reloading the
                    // record which has *just* been saved, so first perform all
                    // onwrites then do a final reload of the record
                    return self.handleOnWrite(record)
                        .pipe(function () {
                            return self.reload_record(record); })
                        .pipe(function () {
                            return { created: created, record: record }; });
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
            }, function () {
                return this.editor.cancel().pipe(function (attrs) {
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
        withEvent: function (event_name, event, action) {
            var self = this;
            event = event || {};
            this.trigger(event_name + ':before', event);
            if (event.cancel) {
                return $.Deferred().reject({
                    message: _.str.sprintf("Event %s:before cancelled",
                                           event_name)});
            }
            return $.when(action.call(this)).then(function () {
                self.trigger.apply(self, [event_name + ':after']
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
                    return $.when.apply(
                        null, _(ids).map(
                            _.bind(self.handleOnWriteRecord, self, source_record)));
                });
        },
        handleOnWriteRecord: function (id, source_record) {
            var record = this.records.get(id);
            if (!record) {
                // insert after the source record
                var index = this.records.indexOf(source_record) + 1;
                record = new instance.web.list.Record({id: id});
                this.records.add(record, {at: index});
                this.dataset.ids.splice(index, 0, id);
            }
            return this.reload_record(record);
        },
        isPrependOnCreate: function () {
            return this.options.editable === 'top';
        },
        setupEvents: function () {
            var self = this;
            this.editor.$element.on('keyup', function (e) {
                var key = _($.ui.keyCode).chain()
                    .map(function (v, k) { return {name: k, code: v}; })
                    .find(function (o) { return o.code === e.which; })
                    .value();
                if (!key) { return; }
                var method = 'keyup_' + key.name;
                if (!(method in self)) { return; }
                self[method](e);
            });
        },
        keyup_ENTER: function () {
            if (!this.editor.isEditing()) { return; }
            var self = this;
            return this.saveEdition().pipe(function (saveInfo) {
                if (saveInfo.created) {
                    return self.startEdition();
                }
                return self.startEdition(
                    self.records.succ(saveInfo.record, {wraparound: true}));
            });
        },
        keyup_ESCAPE: function () {
            if (!this.editor.isEditing()) { return; }
            return this.cancelEdition();
        }
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
         * @param {Object} [options.delegate]
         */
        init: function (parent, options) {
            this._super(parent);
            this.options = options || {};
            _.defaults(this.options, {
                formView: instance.web.FormView,
                delegate: this.getParent()
            });
            this.delegate = this.options.delegate;

            this.record = null;

            this.form = new (this.options.formView)(
                this, this.delegate.dataset, false, {
                    initial_mode: 'edit',
                    $buttons: $(),
                    $pager: $()
            });
        },
        start: function () {
            var self = this;
            var _super = this._super();
            this.form.embedded_view = this._validateView(
                    this.delegate.editionView(this));
            var form_ready = this.form.appendTo(this.$element).then(
                self.form.proxy('do_hide'));
            return $.when(_super, form_ready);
        },
        _validateView: function (edition_view) {
            if (!edition_view) {
                throw new Error("editor delegate's #editionView must return "
                              + "a view descriptor");
            }
            var arch = edition_view.arch;
            if (!(arch && arch.children instanceof Array)) {
                throw new Error("Editor delegate's #editionView must have a" +
                                " non-empty arch")
            }
            if (!(arch.tag === "form")) {
                throw new Error("Editor delegate's #editionView must have a" +
                                " 'form' root node");
            }
            if (!(arch.attrs && arch.attrs.version === "7.0")) {
                throw new Error("Editor delegate's #editionView must be a" +
                                " version 7 view");
            }
            if (!/\boe_form_container\b/.test(arch.attrs['class'])) {
                throw new Error("Editor delegate's #editionView must have the" +
                                " class 'oe_form_container' on its root" +
                                " element");
            }

            return edition_view;
        },

        isEditing: function () {
            return !!this.record;
        },
        edit: function (record, configureField) {
            // TODO: specify sequence of edit calls
            var self = this;
            var form = self.form;
            var loaded = record
                ? form.on_record_loaded(_.extend({}, record))
                : form.load_defaults();

            return loaded.pipe(function () {
                return form.do_show({reload: false});
            }).pipe(function () {
                self.record = form.datarecord;
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
                .do_save(null, this.delegate.isPrependOnCreate())
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
                return $.Deferred().reject({
                    message: "The form's data can not be discarded"}).promise();
            }
            this.form.do_hide();
            return $.when(record);
        }
    });

    instance.web.ListView.Groups.include(/** @lends instance.web.ListView.Groups# */{
        passtrough_events: instance.web.ListView.Groups.prototype.passtrough_events + " edit saved",
        getRowFor: function (record) {
            return _(this.children).chain()
                .invoke('getRowFor', record)
                .compact()
                .first()
                .value();
        }
    });

    instance.web.ListView.List.include(/** @lends instance.web.ListView.List# */{
        row_clicked: function (event) {
            if (!this.options.editable) {
                return this._super.apply(this, arguments);
            }
            var record_id = $(event.currentTarget).data('id');
            this.view.startEdition(record_id ? this.records.get(record_id) : null);
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
            var id;
            var $row = this.$current.children('[data-id=' + record.get('id') + ']');
            if ($row.length) {
                return $row;
            }
            return null;
        }
    });
};
