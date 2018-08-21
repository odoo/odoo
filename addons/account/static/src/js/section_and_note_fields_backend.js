
odoo.define('account.section_and_note_backend', function (require) {
// The goal of this file is to contain JS hacks related to allowing
// section and note on sale order and invoice.

"use strict";
var ListRenderer = require('web.ListRenderer');
var fieldRegistry = require('web.field_registry');
var FieldOne2Many = require('web.relational_fields').FieldOne2Many;
var InputField = require('web.basic_fields').InputField;
var TranslatableFieldMixin = require('web.basic_fields').TranslatableFieldMixin;
var dom = require('web.dom');

var SectionAndNoteListRenderer = ListRenderer.extend({
    /**
     * We want section and note to take the whole line (except handle and trash)
     * to look better and to hide the unnecessary fields.
     *
     * @override
     */
    _renderBodyCell: function (record, node, index, options) {
        var $cell = this._super.apply(this, arguments);

        var isSection = record.data.display_type === 'line_section';
        var isNote = record.data.display_type === 'line_note';

        if (isSection || isNote) {
            if (node.attrs.widget === "handle") {
                return $cell;
            } else if (node.attrs.name === "name") {
                var nbrColumns = this._getNumberOfCols();
                if (this.handleField) {
                    nbrColumns--;
                }
                if (this.addTrashIcon) {
                    nbrColumns--;
                }
                $cell.attr('colspan', nbrColumns);
            } else {
                return $cell.addClass('o_hidden');
            }
        }

        return $cell;
    },
    /**
     * We add the o_is_{display_type} class to allow custom behaviour both in JS and CSS.
     *
     * @override
     */
    _renderRow: function (record, index) {
        var $row = this._super.apply(this, arguments);

        if (record.data.display_type) {
            $row.addClass('o_is_' + record.data.display_type);
        }

        return $row;
    },
    /**
     * We want to add .o_section_and_note_list_view on the table to have stronger CSS.
     *
     * @override
     * @private
     */
    _renderView: function () {
        var def = this._super();
        this.$el.find('> table').addClass('o_section_and_note_list_view');
        return def;
    },
});

// We create a custom widget because this is the cleanest way to do it:
// to be sure this custom code will only impact selected fields having the widget
// and not applied to any other existing ListRenderer.
var SectionAndNoteFieldOne2Many = FieldOne2Many.extend({
    /**
     * We want to use our custom renderer for the list.
     *
     * @override
     */
    _getRenderer: function () {
        if (this.view.arch.tag === 'tree') {
            return SectionAndNoteListRenderer;
        }
        return this._super.apply(this, arguments);
    },
});

// This is a merge between a FieldText and a FieldChar.
// Indeed, we want a FieldChar for section, and a FieldText for the rest (product and note).
var SectionAndNoteFieldText = InputField.extend(TranslatableFieldMixin, {
    /**
     * @constructor
     */
    init: function (parent, name, record, options) {
        this.isSection = record.data.display_type === 'line_section';

        if (!this.isSection) {
            this.className = 'o_field_text';
            this.supportedFieldTypes = ['text'];
            this.tagName = 'span';
        }
        if (this.isSection) {
            this.className = 'o_field_char';
            this.tagName = 'span';
            this.supportedFieldTypes = ['char'];
        }

        this._super.apply(this, arguments);

        if (!this.isSection) {
            if (this.mode === 'edit') {
                this.tagName = 'textarea';
            }
        }
    },
    /**
     * As it it done in the start function, the autoresize is done only once.
     *
     * @override
     */
    start: function () {
        if (!this.isSection) {
            if (this.mode === 'edit') {
                dom.autoresize(this.$el, {parent: this});

                this.$el = this.$el.add(this._renderTranslateButton());
            }
        }
        return this._super.apply(this, arguments);
    },
     /**
     * Override to force a resize of the textarea when its value has changed
     *
     * @override
     */
    reset: function () {
        if (!this.isSection) {
            var self = this;
            return $.when(this._super.apply(this, arguments)).then(function () {
                self.$input.trigger('change');
            });
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Stops the enter navigation in a text area.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onKeydown: function (ev) {
        if (!this.isSection) {
            if (ev.which === $.ui.keyCode.ENTER) {
                return;
            }
        }
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add translation button
     *
     * @override
     * @private
     */
    _renderEdit: function () {
        var def = this._super.apply(this, arguments);
        if (this.isSection) {
            if (this.field.size && this.field.size > 0) {
                this.$el.attr('maxlength', this.field.size);
            }
            this.$el = this.$el.add(this._renderTranslateButton());
        }
        return def;
    },
    /**
     * Trim the value input by the user.
     *
     * @override
     * @private
     * @param {any} value
     * @param {Object} [options]
     */
    _setValue: function (value, options) {
        if (this.isSection) {
            if (this.field.trim) {
                value = value.trim();
            }
        }
        return this._super(value, options);
    },
});

fieldRegistry.add('section_and_note_one2many', SectionAndNoteFieldOne2Many);
fieldRegistry.add('section_and_note_text', SectionAndNoteFieldText);

});
