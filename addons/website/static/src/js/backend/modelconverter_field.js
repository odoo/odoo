
odoo.define('website.modelconverter_field', function (require) {
"use strict";

var basic_fields = require('web.basic_fields');
var registry = require('web.field_registry');

var FieldChar = basic_fields.FieldChar;


var ModelConverterChar = FieldChar.extend({
    supportedFieldTypes: [],
    resetOnAnyFieldChange: true,

    /**
     * @constructor
     * Prepares the basic rendering of edit mode by setting the root to be a
     * div
     * @see FieldChar.init
     */
    init: function () {
        this._super.apply(this, arguments);
        if (this.mode === 'edit') {
            this.tagName = 'div';
            this.className += ' input-group';
        }
    },

    /**
     * Activates the right input from the widget. Widget can contains more than
     * one input, so when we call this function, we need to focus the last one
     * if we are coming from an posterior element. In case we come from a
     * ancestor element, we select the first input.
     *
     * @param {integer} inc: -1 when we come from a next element, 1 for previous
     *
     * @returns {jQuery} main focusable element inside the widget
     *
     */
    getFocusableElement: function (inc) {
        if (inc === -1) {  // if coming from a field after this widget.
            return this.$('input:last');
        } else {  // if coming from a field before this widget.
            return this.$('input:first');
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getValue: function () {
        var str = '';
        _.each(this.$('input, span'), function(o) {
            if (o.nodeName === 'INPUT') {
                str += o.value;
            }
            else if (o.nodeName === 'SPAN') {
                str += $(o).data('origin');
            }
        });
        return str;

    },

    _onNavigationMove: function (ev) {
        var $focus;
        switch (ev.data.direction) {
            case 'previous':
                $focus = this.$('input:focus').prevAll('input');
                if ($focus.length) {
                    $focus.focus();
                    ev.stopPropagation();
                }
                break;
            case 'next':
                $focus = this.$('input:focus').nextAll('input');
                if ($focus.length) {
                    $focus.focus();
                    ev.stopPropagation();
                }
                break;
        }

        if (!$focus.length) {
          ev.data.target = this; // apply super of super
        }
    },

    _createInput: function (str) {
        return $('<input />', {
            type: 'text',
            class: 'form-control o_field_char o_field_widget o_input',
        }).val(str);
    },

    _renderEdit: function () {
        var self = this;
        this.$el.empty();
        if (this.recordData.action === "rewrite" && this.value) {
            var node = $('<div/>', {class: 'input-group'});
            var str = '';

            _.each(this.value.trim().split('/'), function (s) {
                if (s) {
                    if (!_.str.startsWith(s, '<')) { //editable route
                        str += '/' + s;
                    } else {
                        if (str) {
                            node.append(self._createInput(str));
                            str = '';
                        }

                        var ns = _.last(s.split(':')).slice(0, -1);
                        node.append($('<span />', {
                            class: 'input-group-addon',
                        }).data('origin', '/' + s).text('/ @' + ns));
                    }
                }
            });
            if (str) {
                node.append(this._createInput(str));
                str = '';
            }
            this.$el.append(node);
        } else {
            this.$el.append(this._createInput(this.value || ''));
        }
    },
});

registry.add('modelconverter', ModelConverterChar);


});
