/**
 * handles editability case for lists, because it depends on form and forms already depends on lists it had to be split out
 * @namespace
 */
(function() {

    var instance = openerp;
    openerp.web.list_editable = {};
    var _t = instance.web._t;

    // editability status of list rows
    instance.web.ListView.prototype.defaults.editable = null;

    // TODO: not sure second @lends on existing item is correct, to check
    instance.web.ListView.include(/** @lends instance.web.ListView# */{
        init: function () {
            var self = this;
            this._super.apply(this, arguments);

            this.saving_mutex = new $.Mutex();

            this._force_editability = null;
            this._context_editable = false;
            this.editor = this.make_editor();
            // Stores records of {field, cell}, allows for re-rendering fields
            // depending on cell state during and after resize events
            this.fields_for_resize = [];
            instance.web.bus.on('resize', this, this.resize_fields);

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

            this.records.bind('remove', function () {
                if (self.editor.is_editing()) {
                    self.cancel_edition();
                }
            });

            this.on('edit:before', this, function (event) {
                if (!self.editable() || self.editor.is_editing()) {
                    event.cancel = true;
                }
            });
            this.on('edit:after', this, function () {
                self.$el.add(self.$buttons).addClass('oe_editing');
                self.$('.ui-sortable').sortable('disable');
            });
            this.on('save:after cancel:after', this, function () {
                self.$('.ui-sortable').sortable('enable');
                self.$el.add(self.$buttons).removeClass('oe_editing');
            });
        },
        destroy: function () {
            instance.web.bus.off('resize', this, this.resize_fields);
            this._super();
        },
        do_hide: function () {
            if (this.editor.is_editing()) {
                this.cancel_edition(true);
            }
            this._super();
        },
        sort_by_column: function (e) {
            e.stopPropagation();
            if (!this.editor.is_editing()) {
                this._super.apply(this, arguments);
            }
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
        do_delete: function (ids) {
            var nonfalse = _.compact(ids);
            var _super = this._super.bind(this);
            var next = this.editor.is_editing()
                    ? this.cancel_edition(true)
                    : $.when();
            return next.then(function () {
                return _super(nonfalse);
            });
        },
        editable: function () {
            return !this.grouped
                && !this.options.disable_editable_mode
                && (this.fields_view.arch.attrs.editable
                || this._context_editable
                || this.options.editable);
        },
        /**
         * Replace do_search to handle editability process
         */
        do_search: function(domain, context, group_by) {
            var self=this, _super = self._super, args=arguments;
            var ready = this.editor.is_editing()
                    ? this.cancel_edition(true)
                    : $.when();

            return ready.then(function () {
                self._context_editable = !!context.set_editable;
                return _super.apply(self, args);
            });
        },
        /**
         * Replace do_add_record to handle editability (and adding new record
         * as an editable row at the top or bottom of the list)
         */
        do_add_record: function () {
            var self = this;
            if (this.editable()) {
                this.$el.find('table:first').show();
                this.$el.find('.oe_view_nocontent').remove();
                this.start_edition();
            } else {
                this._super();
            }
        },
        load_list: function (data, grouped) {
            var self = this;
            // tree/@editable takes priority on everything else if present.
            var result = this._super(data, grouped);

            // In case current editor was started previously, also has to run
            // when toggling from editable to non-editable in case form widgets
            // have setup global behaviors expecting themselves to exist
            // somehow.
            this.editor.destroy();
            // Editor is not restartable due to formview not being restartable
            this.editor = this.make_editor();

            if (this.editable()) {
                this.$el.addClass('oe_list_editable');
                // FIXME: any hook available to ensure this is only done once?
                this.$buttons
                    .off('click', '.oe_list_save')
                    .on('click', '.oe_list_save', this.proxy('save_edition'))
                    .off('click', '.oe_list_discard')
                    .on('click', '.oe_list_discard', function (e) {
                        e.preventDefault();
                        self.cancel_edition();
                    });
                var editor_ready = this.editor.prependTo(this.$el)
                    .done(this.proxy('setup_events'));

                return $.when(result, editor_ready);
            } else {
                this.$el.removeClass('oe_list_editable');
            }

            return result;
        },
        /**
         * Builds a new editor object
         *
         * @return {instance.web.list.Editor}
         */
        make_editor: function () {
            return new instance.web.list.Editor(this);
        },
        do_button_action: function (name, id, callback) {
            var self = this, args = arguments;
            this.ensure_saved().done(function (done) {
                if (!id && done.created) {
                    id = done.record.get('id');
                }
                self.handle_button(name, id, callback);
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
        ensure_saved: function () {
            return this.save_edition();
        },
        /**
         * Builds a record with the provided id (``false`` for a creation),
         * setting all columns with ``false`` value so code which relies on
         * having an actual value behaves correctly
         *
         * @param {*} id
         * @return {instance.web.list.Record}
         */
        make_empty_record: function (id) {
            var attrs = {id: id};
            _(this.columns).chain()
                .filter(function (x) { return x.tag === 'field';})
                .pluck('name')
                .each(function (field) { attrs[field] = false; });
            return new instance.web.list.Record(attrs);
        },
        /**
         * Set up the edition of a record of the list view "inline"
         *
         * @param {instance.web.list.Record} [record] record to edit, leave empty to create a new record
         * @param {Object} [options]
         * @param {String} [options.focus_field] field to focus at start of edition
         * @return {jQuery.Deferred}
         */
        start_edition: function (record, options) {
            var self = this;
            var item = false;
            if (record) {
                item = record.attributes;
            } else {
                record = this.make_empty_record(false);
                this.records.add(record, {
                    at: this.prepends_on_create() ? 0 : null});
            }

            return this.ensure_saved().then(function () {
                var $recordRow = self.groups.get_row_for(record);
                var cells = self.get_cells_for($recordRow);
                var fields = {};
                self.fields_for_resize.splice(0, self.fields_for_resize.length);
                return self.with_event('edit', {
                    record: record.attributes,
                    cancel: false
                }, function () {
                    return self.editor.edit(item, function (field_name, field) {
                        var cell = cells[field_name];
                        if (!cell) {
                            return;
                        }

                        // FIXME: need better way to get the field back from bubbling (delegated) DOM events somehow
                        field.$el.attr('data-fieldname', field_name);
                        fields[field_name] = field;
                        self.fields_for_resize.push({field: field, cell: cell});
                    }, options).then(function () {
                        $recordRow.addClass('oe_edition');
                        self.resize_fields();
                        var focus_field = options && options.focus_field ? options.focus_field : undefined;
                        if (!focus_field){
                            focus_field = _.find(self.editor.form.fields_order, function(field){ return fields[field] && fields[field].$el.is(':visible:has(input)'); });
                        }
                        if (focus_field) fields[focus_field].$el.find('input').select();
                        return record.attributes;
                    });
                }).fail(function () {
                    // if the start_edition event is cancelled and it was a
                    // creation, remove the newly-created empty record
                    if (!record.get('id')) {
                        self.records.remove(record);
                    }
                });
            });
        },
        get_cells_for: function ($row) {
            var cells = {};
            $row.children('td').each(function (index, el) {
                cells[el.getAttribute('data-field')] = el;
            });
            return cells;
        },
        /**
         * If currently editing a row, resizes all registered form fields based
         * on the corresponding row cell
         */
        resize_fields: function () {
            if (!this.editor.is_editing()) { return; }
            for(var i=0, len=this.fields_for_resize.length; i<len; ++i) {
                var item = this.fields_for_resize[i];
                this.resize_field(item.field, item.cell);
            }
        },
        /**
         * Resizes a field's root element based on the corresponding cell of
         * a listview row
         *
         * @param {instance.web.form.AbstractField} field
         * @param {jQuery} cell
         */
        resize_field: function (field, cell) {
            var $cell = $(cell);

            field.set_dimensions($cell.outerHeight(), $cell.outerWidth());
            field.$el.position({
                my: 'left top',
                at: 'left top',
                of: $cell
            });
            if (field.get('effective_readonly')) {
                field.$el.addClass('oe_readonly');
            }
            if(field.widget == "handle")
                field.$el.addClass('oe_list_field_handle');
        },
        /**
         * @return {jQuery.Deferred}
         */
        save_edition: function () {
            var self = this;
            return self.saving_mutex.exec(function() {
                if (!self.editor.is_editing()) {
                    return $.when();
                }
                return self.with_event('save', {
                    editor: self.editor,
                    form: self.editor.form,
                    cancel: false
                }, function () {
                    return self.editor.save().then(function (attrs) {
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
                        return self.handle_onwrite(record)
                            .then(function () {
                                return self.reload_record(record); })
                            .then(function () {
                                return { created: created, record: record }; });
                    });
                });
            });
        },
        /**
         * @param {Boolean} [force=false] discards the data even if the form has been edited
         * @return {jQuery.Deferred}
         */
        cancel_edition: function (force) {
            var self = this;
            return this.with_event('cancel', {
                editor: this.editor,
                form: this.editor.form,
                cancel: false
            }, function () {
                return this.editor.cancel(force).then(function (attrs) {
                    if (attrs.id) {
                        var record = self.records.get(attrs.id);
                        if (!record) {
                            // Record removed by third party during edition
                            return;
                        }
                        return self.reload_record(record);
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
        with_event: function (event_name, event, action) {
            var self = this;
            event = event || {};
            this.trigger(event_name + ':before', event);
            if (event.cancel) {
                return $.Deferred().reject({
                    message: _.str.sprintf("Event %s:before cancelled",
                                           event_name)});
            }
            return $.when(action.call(this)).done(function () {
                self.trigger.apply(self, [event_name + ':after']
                        .concat(_.toArray(arguments)));
            });
        },
        edition_view: function (editor) {
            var view = $.extend(true, {}, this.fields_view);
            view.arch.tag = 'form';
            _.extend(view.arch.attrs, {
                'class': 'oe_form_container',
                version: '7.0'
            });
            _(view.arch.children).chain()
                .zip(_(this.columns).filter(function (c) {
                    return !(c instanceof instance.web.list.MetaColumn);}))
                .each(function (ar) {
                    var widget = ar[0], column = ar[1];
                    var modifiers = _.extend({}, column.modifiers);
                    widget.attrs.nolabel = true;
                    if (modifiers['tree_invisible'] || widget.tag === 'button') {
                        modifiers.invisible = true;
                    }
                    widget.attrs.modifiers = JSON.stringify(modifiers);
                });
            return view;
        },
        handle_onwrite: function (source_record) {
            var self = this;
            var on_write_callback = self.fields_view.arch.attrs.on_write;
            if (!on_write_callback) { return $.when(); }
            return this.dataset.call(on_write_callback, [source_record.get('id')])
                .then(function (ids) {
                    return $.when.apply(
                        null, _(ids).map(
                            _.bind(self.handle_onwrite_record, self, source_record)));
                });
        },
        handle_onwrite_record: function (source_record, id) {
            var record = this.records.get(id);
            if (!record) {
                // insert after the source record
                var index = this.records.indexOf(source_record) + 1;
                record = this.make_empty_record(id);
                this.records.add(record, {at: index});
            }
            return this.reload_record(record);
        },
        prepends_on_create: function () {
            return this.editable() === 'top';
        },
        setup_events: function () {
            var self = this;
            _.each(this.editor.form.fields, function(field, field_name) {
                field.on("change:effective_readonly", self, function(){
                    var item = _(self.fields_for_resize).find(function (item) {
                        return item.field === field;
                    });
                    if (item) {
                        setTimeout(function() {
                            self.resize_field(item.field, item.cell);
                        }, 0);
                    }
                     
                });
            });

            this.editor.$el.on('keyup keypress keydown', function (e) {
                if (!self.editor.is_editing()) { return true; }
                var key = _($.ui.keyCode).chain()
                    .map(function (v, k) { return {name: k, code: v}; })
                    .find(function (o) { return o.code === e.which; })
                    .value();
                if (!key) { return true; }
                var method = e.type + '_' + key.name;
                if (!(method in self)) { return true; }
                return self[method](e);
            });
        },
        /**
         * Saves the current record, and goes to the next one (creation or
         * edition)
         *
         * @private
         * @param {String} [next_record='succ'] method to call on the records collection to get the next record to edit
         * @param {Object} [options]
         * @param {String} [options.focus_field]
         * @return {*}
         */
        _next: function (next_record, options) {
            next_record = next_record || 'succ';
            var self = this;
            return this.save_edition().then(function (saveInfo) {
                if (!saveInfo) { return null; }
                if (saveInfo.created) {
                    return self.start_edition();
                }
                var record = self.records[next_record](
                        saveInfo.record, {wraparound: true});
                return self.start_edition(record, options);
            });
        },
        keypress_ENTER: function () {
            return this._next();
        },
        keydown_ESCAPE: function (e) {
            return false;
        },
        keyup_ESCAPE: function (e) {
            return this.cancel_edition();
        },
        /**
         * Gets the selection range (start, end) for the provided element,
         * returns ``null`` if it can't get a range.
         *
         * @private
         */
        _text_selection_range: function (el) {
            var selectionStart;
            try {
                selectionStart = el.selectionStart;
            } catch (e) {
                // radio or checkbox throw on selectionStart access
                return null;
            }
            if (selectionStart !== undefined) {
                return {
                    start: selectionStart,
                    end: el.selectionEnd
                };
            } else if (document.body.createTextRange) {
                throw new Error("Implement text range handling for MSIE");
            }
            // Element without selection ranges (select, div/@contenteditable)
            return null;
        },
        _text_cursor: function (el) {
            var selection = this._text_selection_range(el);
            if (!selection) {
                return null;
            }
            if (selection.start !== selection.end) {
                return {position: null, collapsed: false};
            }
            return {position: selection.start, collapsed: true};
        },
        /**
         * Checks if the cursor is at the start of the provided el
         *
         * @param {HTMLInputElement | HTMLTextAreaElement}
         * @returns {Boolean}
         * @private
         */
        _at_start: function (cursor, el) {
            return cursor.collapsed && (cursor.position === 0);
        },
        /**
         * Checks if the cursor is at the end of the provided el
         *
         * @param {HTMLInputElement | HTMLTextAreaElement}
         * @returns {Boolean}
         * @private
         */
        _at_end: function (cursor, el) {
            return cursor.collapsed && (cursor.position === el.value.length);
        },
        /**
         * @param DOMEvent event
         * @param {String} record_direction direction to move into to get the next record (pred | succ)
         * @param {Function} is_valid_move whether the edition should be moved to the next record
         * @private
         */
        _key_move_record: function (event, record_direction, is_valid_move) {
            if (!this.editor.is_editing('edit')) { return $.when(); }
            var cursor = this._text_cursor(event.target);
            // if text-based input (has a cursor)
            //    and selecting (not collapsed) or not at a field boundary
            //        don't move to the next record
            if (cursor && !is_valid_move(event.target, cursor)) { return $.when(); }

            event.preventDefault();
            var source_field = $(event.target).closest('[data-fieldname]')
                    .attr('data-fieldname');
            return this._next(record_direction, {focus_field: source_field});

        },
        keydown_UP: function (e) {
            var self = this;
            return this._key_move_record(e, 'pred', function (el, cursor) {
                return self._at_start(cursor, el);
            });
        },
        keydown_DOWN: function (e) {
            var self = this;
            return this._key_move_record(e, 'succ', function (el, cursor) {
                return self._at_end(cursor, el);
            });
        },

        keydown_LEFT: function (e) {
            // If the cursor is at the beginning of the field
            var source_field = $(e.target).closest('[data-fieldname]')
                    .attr('data-fieldname');
            var cursor = this._text_cursor(e.target);
            if (cursor && !this._at_start(cursor, e.target)) { return $.when(); }

            var fields_order = this.editor.form.fields_order;
            var field_index = _(fields_order).indexOf(source_field);

            // Look for the closest visible form field to the left
            var fields = this.editor.form.fields;
            var field;
            do {
                if (--field_index < 0) { return $.when(); }

                field = fields[fields_order[field_index]];
            } while (!field.$el.is(':visible'));

            // and focus it
            field.focus();
            return $.when();
        },
        keydown_RIGHT: function (e) {
            // same as above, but with cursor at the end of the field and
            // looking for new fields at the right
            var source_field = $(e.target).closest('[data-fieldname]')
                    .attr('data-fieldname');
            var cursor = this._text_cursor(e.target);
            if (cursor && !this._at_end(cursor, e.target)) { return $.when(); }

            var fields_order = this.editor.form.fields_order;
            var field_index = _(fields_order).indexOf(source_field);

            var fields = this.editor.form.fields;
            var field;
            do {
                if (++field_index >= fields_order.length) { return $.when(); }

                field = fields[fields_order[field_index]];
            } while (!field.$el.is(':visible'));

            field.focus();
            return $.when();
        },
        keydown_TAB: function (e) {
            var form = this.editor.form;
            var last_field = _(form.fields_order).chain()
                .map(function (name) { return form.fields[name]; })
                .filter(function (field) { return field.$el.is(':visible'); })
                .last()
                .value();
            // tabbed from last field in form
            if (last_field && last_field.$el.has(e.target).length) {
                e.preventDefault();
                return this._next();
            }
            return $.when();
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
                    disable_autofocus: true,
                    $buttons: $(),
                    $pager: $()
            });
        },
        start: function () {
            var self = this;
            var _super = this._super();            
            this.form.embedded_view = this._validate_view(
                    this.delegate.edition_view(this));
            var form_ready = this.form.appendTo(this.$el).done(
                self.form.proxy('do_hide'));
            return $.when(_super, form_ready);
        },
        _validate_view: function (edition_view) {
            if (!edition_view) {
                throw new Error("editor delegate's #edition_view must return "
                              + "a view descriptor");
            }
            var arch = edition_view.arch;
            if (!(arch && arch.children instanceof Array)) {
                throw new Error("Editor delegate's #edition_view must have a" +
                                " non-empty arch");
            }
            if (arch.tag !== "form") {
                throw new Error("Editor delegate's #edition_view must have a" +
                                " 'form' root node");
            }
            if (!(arch.attrs && arch.attrs.version === "7.0")) {
                throw new Error("Editor delegate's #edition_view must be a" +
                                " version 7 view");
            }
            if (!/\boe_form_container\b/.test(arch.attrs['class'])) {
                throw new Error("Editor delegate's #edition_view must have the" +
                                " class 'oe_form_container' on its root" +
                                " element");
            }

            return edition_view;
        },

        /**
         *
         * @param {String} [state] either ``new`` or ``edit``
         * @return {Boolean}
         */
        is_editing: function (state) {
            if (!this.record) {
                return false;
            }
            switch(state) {
            case null: case undefined:
                return true;
            case 'new': return !this.record.id;
            case 'edit': return !!this.record.id;
            }
            throw new Error("is_editing's state filter must be either `new` or" +
                            " `edit` if provided");
        },
        edit: function (record, configureField, options) {
            // TODO: specify sequence of edit calls
            var self = this;
            var form = self.form;
            var loaded = record
                ? form.trigger('load_record', _.extend({}, record))
                : form.load_defaults();
            return $.when(loaded).then(function () {
                return form.do_show({reload: false});
            }).then(function () {
                self.record = form.datarecord;
                _(form.fields).each(function (field, name) {
                    configureField(name, field);
                });
                return form;
            });
        },
        save: function () {
            var self = this;
            return this.form
                .save(this.delegate.prepends_on_create())
                .then(function (result) {
                    var created = result.created && !self.record.id;
                    if (created) {
                        self.record.id = result.result;
                    }
                    return self.cancel();
                });
        },
        cancel: function (force) {
            if (!(force || this.form.can_be_discarded())) {
                return $.Deferred().reject({
                    message: _t("The form's data can not be discarded")}).promise();
            }
            var record = this.record;
            this.record = null;
            this.form.do_hide();
            return $.when(record);
        }
    });

    instance.web.ListView.Groups.include(/** @lends instance.web.ListView.Groups# */{
        passthrough_events: instance.web.ListView.Groups.prototype.passthrough_events + " edit saved",
        get_row_for: function (record) {
            return _(this.children).chain()
                .invoke('get_row_for', record)
                .compact()
                .first()
                .value();
        }
    });

    instance.web.ListView.List.include(/** @lends instance.web.ListView.List# */{
        row_clicked: function (event) {
            if (!this.view.editable() || ! this.view.is_action_enabled('edit')) {
                return this._super.apply(this, arguments);
            }
            var record_id = $(event.currentTarget).data('id');
            return this.view.start_edition(
                record_id ? this.records.get(record_id) : null, {
                focus_field: $(event.target).data('field')
            });
        },
        /**
         * If a row mapping to the record (@data-id matching the record's id or
         * no @data-id if the record has no id), returns it. Otherwise returns
         * ``null``.
         *
         * @param {Record} record the record to get a row for
         * @return {jQuery|null}
         */
        get_row_for: function (record) {
            var id;
            var $row = this.$current.children('[data-id=' + record.get('id') + ']');
            if ($row.length) {
                return $row;
            }
            return null;
        }
    });
})();
