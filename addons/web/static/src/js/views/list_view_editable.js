odoo.define('web.ListEditor', function (require) {
"use strict";    
/*---------------------------------------------------------
 * Odoo Editable List view
 *---------------------------------------------------------*/
/**
 * handles editability case for lists, because it depends on form and forms already depends on lists it had to be split out
 * @namespace
 */

var core = require('web.core');
var data = require('web.data');
var FormView = require('web.FormView');
var common = require('web.list_common');
var ListView = require('web.ListView');
var utils = require('web.utils');
var Widget = require('web.Widget');

var _t = core._t;

var Editor = Widget.extend({
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
            formView: FormView,
            delegate: this.getParent(),
        });
        this.delegate = this.options.delegate;

        this.record = null;
        this.form = new (this.options.formView)(this, this.delegate.dataset, false, {
            initial_mode: 'edit',
            is_list_editable: true,
            disable_autofocus: true,
            $buttons: $(),
            $pager: $(),
        });
    },
    start: function () {
        var self = this;
        this.form.embedded_view = this._validate_view(this.delegate.edition_view(this));
        return $.when(this._super(), this.form.appendTo($('<div/>')).then(function() {
            self.form.$el.addClass(self.$el.attr('class'));
            self.replaceElement(self.form.$el);
        }).done(this.proxy('do_hide')));
    },
    _validate_view: function (edition_view) {
        if (!edition_view) {
            throw new Error("editor delegate's #edition_view must return a view descriptor");
        }
        var arch = edition_view.arch;
        if (!(arch && arch.children instanceof Array)) {
            throw new Error("Editor delegate's #edition_view must have a non-empty arch");
        }
        if (arch.tag !== "form") {
            throw new Error("Editor delegate's #edition_view must have a 'form' root node");
        }
        if (!(arch.attrs && arch.attrs.version === "7.0")) {
            throw new Error("Editor delegate's #edition_view must be a version 7 view");
        }
        if (!/\boe_form_container\b/.test(arch.attrs['class'])) {
            throw new Error("Editor delegate's #edition_view must have the class " +
                            "'boe_form_container' on its root element");
        }
        return edition_view;
    },
    is_editing: function () {
        return !!this.record;
    },
    is_creating: function () {
        return (this.is_editing() && !this.record.id);
    },
    edit: function (record, configureField, options) {
        // TODO: specify sequence of edit calls
        var loaded;
        if(record) {
            loaded = this.form.trigger('load_record', _.extend({}, record))
        } else {
            loaded = this.form.load_defaults();
        }

        var self = this;
        return $.when(loaded).then(function () {
            return self.do_show({reload: false});
        }).then(function () {
            self.record = self.form.datarecord;
            _(self.form.fields).each(function (field, name) {
                configureField(name, field);
            });
            return self.form;
        });
    },
    save: function () {
        var self = this;
        return this.form
            .save(this.delegate.prepends_on_create())
            .then(function (result) {
                if(result.created && !self.record.id) {
                    self.record.id = result.result;
                }
                return self.record;
            });
    },
    cancel: function (force) {
        var self = this;
        if(force) {
            return do_cancel();
        }
        var message = _t("The line has been modified, your changes will be discarded. Are you sure you want to discard the changes ?");
        return this.form.can_be_discarded(message).then(do_cancel);

        function do_cancel() {
            var record = self.record;
            self.record = null;
            self.do_hide();
            return $.when(record);
        }
    },
    do_hide: function() {
        this.form.do_hide.apply(this.form, arguments);
        this.form.set({display_invalid_fields: false});
    },
    do_show: function() {
        this.form.do_show.apply(this.form, arguments);
    },
});

// editability status of list rows
ListView.prototype.defaults.editable = null;

// TODO: not sure second @lends on existing item is correct, to check
ListView.include(/** @lends instance.web.ListView# */{
    init: function () {
        var self = this;
        this._super.apply(this, arguments);

        this.saving_mutex = new utils.Mutex();

        this._force_editability = null;
        this._context_editable = false;
        this.editor = new Editor(this);
        // Stores records of {field, cell}, allows for re-rendering fields
        // depending on cell state during and after resize events
        this.fields_for_resize = [];
        core.bus.on('resize', this, this.resize_fields);

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
        core.bus.off('resize', this, this.resize_fields);
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
        var next = (this.editor.is_editing())? this.cancel_edition(true) : $.when();
        return next.then(function () {
            return _super(nonfalse);
        });
    },
    editable: function () {
        return !this.grouped
            && !this.options.disable_editable_mode
            && (this.fields_view.arch.attrs.editable || this._context_editable || this.options.editable);
    },
    /**
     * Replace do_search to handle editability process
     */
    do_search: function(domain, context, group_by) {
        var self = this;
        var _super = this._super;
        var args = arguments;
        var ready = (this.editor.is_editing())? this.cancel_edition(true) : $.when();
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
        if (this.editable()) {
            this.$('table:first').show();
            this.$('.oe_view_nocontent').remove();
            this.start_edition();
        } else {
            this._super.apply(this, arguments);
        }
    },
    load_list: function (data, grouped) {
        // tree/@editable takes priority on everything else if present.
        var result = this._super.apply(this, arguments);

        // In case current editor was started previously, also has to run
        // when toggling from editable to non-editable in case form widgets
        // have setup global behaviors expecting themselves to exist somehow.
        this.editor.destroy();
        this.editor = new Editor(this); // Editor is not restartable due to formview not being restartable

        if(this.editable()) {
            this.$el.addClass('oe_list_editable');
            return $.when(result, this.editor.prependTo(this.$el).done(this.proxy('setup_events')));
        } else {
            this.$el.removeClass('oe_list_editable');
        }
        return result;
    },
    /**
     * Extend the render_buttons function of ListView by adding event listeners
     * in the case of an editable list.
     * @return {jQuery} the rendered buttons
     */
    render_buttons: function() {
        var add_button = !this.$buttons; // Ensures that this is only done once
        var result = this._super.apply(this, arguments); // Sets this.$buttons

        if (add_button && (this.editable() || this.grouped)) {
            var self = this;
            this.$buttons
                .off('click', '.o_list_button_save')
                .on('click', '.o_list_button_save', this.proxy('save_edition'))
                .off('click', '.o_list_button_discard')
                .on('click', '.o_list_button_discard', function (e) {
                    e.preventDefault();
                    self.cancel_edition();
                });
        }
        return result;
    },
    do_button_action: function (name, id, callback) {
        var self = this;
        this.save_edition().done(function (data) {
            if(!id && data.created) {
                id = data.record.get('id');
            }
            self.handle_button(name, id, callback);
        });
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
            .filter(function (x) { return x.tag === 'field'; })
            .pluck('name')
            .each(function (field) { attrs[field] = false; });
        return new common.Record(attrs);
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
            this.dataset.select_id(record.get('id'));
        } else {
            record = this.make_empty_record(false);
            this.records.add(record, {at: (this.prepends_on_create())? 0 : null});
        }

        return this.save_edition().then(function() {
            return $.when.apply($, self.editor.form.render_value_defs);
        }).then(function () {
            var $recordRow = self.groups.get_row_for(record);
            var cells = self.get_cells_for($recordRow);
            var fields = {};
            self.fields_for_resize.splice(0, self.fields_for_resize.length); // Empty array
            return self.with_event('edit', {
                record: record.attributes,
                cancel: false,
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
                    // Local function that returns true if field is visible and editable
                    var is_focusable = function(field) {
                        return field && field.$el.is(':visible:not(.oe_readonly)');
                    };
                    var focus_field = options && options.focus_field ? options.focus_field : undefined;
                    if (!is_focusable(fields[focus_field])) {
                        focus_field = _.find(self.editor.form.fields_order, function(field) {
                            return is_focusable(fields[field]);
                        });
                    }
                    if (fields[focus_field]) {
                        fields[focus_field].$el.find('input, textarea').andSelf().filter('input, textarea').focus();
                    }
                    return record.attributes;
                });
            }).fail(function () {
                // if the start_edition event is cancelled and it was a creation, remove the newly-created empty record
                if(!record.get('id')) {
                    self.records.remove(record);
                }
            });
        }, function() {
            return $.Deferred().resolve(); // Here the save/cancel edition failed so the start_edition is considered as done and succeeded
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
        if (!this.editor.is_editing()) {
            return;
        }
        for(var i = 0, len = this.fields_for_resize.length ; i < len ; i++) {
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
        field.$el.addClass('o_temp_visible').css({top: 0, left: 0}).position({
            my: 'left top',
            at: 'left top',
            of: $cell,
        }).removeClass('o_temp_visible');
        if(field.get('effective_readonly')) {
            field.$el.addClass('oe_readonly');
        }
        if(field.widget == "handle") {
            field.$el.addClass('oe_list_field_handle');
        }
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
                cancel: false,
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
                    return self.cancel_edition(true)
                        .then(function() {
                            return self.handle_onwrite(record);
                        })
                        .then(function () {
                            return self.reload_record(record);
                        })
                        .then(function () {
                            return {created: created, record: record};
                        });
                }, function() {
                    return self.cancel_edition();
                });
            });
        });
    },
    /**
     * @param {Boolean} [force] force the line to be discarded (even if there was changes)
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
                        return; // Record removed by third party during edition
                    }
                    return self.reload_record(record, {do_not_evict: true});
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
                return !(c instanceof ListView.MetaColumn);}))
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
        if (!on_write_callback) {
            return $.when();
        }
        var context = new data.CompoundContext(self.dataset.get_context(), {'on_write_domain': self.dataset.domain}).eval();
        return this.dataset.call(on_write_callback, [source_record.get('id'), context])
            .then(function (ids) {
                return $.when.apply(null, _(ids).map(_.bind(self.handle_onwrite_record, self, source_record)));
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
        return (this.editable() === 'top');
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
            var record = self.records[next_record](saveInfo.record, {wraparound: true});
            return self.start_edition(record, options);
        });
    },
    keyup_ENTER: function () {
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
        if (!this.editor.is_editing() || this.editor.is_creating()) { return $.when(); }
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
    keyup_UP: function (e) {
        var self = this;
        return this._key_move_record(e, 'pred', function (el, cursor) {
            return self._at_start(cursor, el);
        });
    },
    keyup_DOWN: function (e) {
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
    keydown_TAB: function (e) { // Keydown and not keyup because this handler must be called before the browser has focused the next field
        var form = this.editor.form;
        var last_field = _(form.fields_order).chain()
            .map(function (name) { return form.fields[name]; })
            .filter(function (field) { return field.$el.is(':visible') && !field.get('effective_readonly'); })
            .last()
            .value();
        // tabbed from last field in form
        if (last_field && $(e.target).closest(last_field.el).length) {
            e.preventDefault();
            return this._next();
        }
        this.editor.form.__clicked_inside = true;
        return $.when();
    },
});


ListView.Groups.include(/** @lends instance.web.ListView.Groups# */{
    passthrough_events: ListView.Groups.prototype.passthrough_events + " edit saved",
    get_row_for: function (record) {
        return _(this.children).chain()
            .invoke('get_row_for', record)
            .compact()
            .first()
            .value();
    }
});

ListView.List.include(/** @lends instance.web.ListView.List# */{
    row_clicked: function (event) {
        if (!this.view.editable() || !this.view.is_action_enabled('edit')) {
            return this._super.apply(this, arguments);
        }

        var self = this;
        var args = arguments;
        var _super = self._super;

        var record_id = $(event.currentTarget).data('id');
        return this.view.start_edition(
            ((record_id)? this.records.get(record_id) : null), {
            focus_field: $(event.target).not(".oe_readonly").data('field'),
        }).fail(function() {
            return _super.apply(self, args); // The record can't be edited so open it in a modal (use-case: readonly mode)
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
        var $row = this.$current.children('[data-id=' + record.get('id') + ']');
        return (($row.length)? $row : null);
    },
});

return Editor;

});
