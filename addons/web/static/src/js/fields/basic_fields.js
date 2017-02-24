odoo.define('web.basic_fields', function (require) {
"use strict";

/**
 * This module contains most of the basic (meaning: non relational) field
 * widgets. Field widgets are supposed to be used in views inheriting from
 * BasicView, so, they can work with the records obtained from a BasicModel.
 */

var AbstractField = require('web.AbstractField');
var ajax = require('web.ajax');
var config = require('web.config');
var core = require('web.core');
var crash_manager = require('web.crash_manager');
var datepicker = require('web.datepicker');
var dom = require('web.dom');
var Domain = require('web.Domain');
var DomainSelector = require('web.DomainSelector');
var DomainSelectorDialog = require('web.DomainSelectorDialog');
var field_utils = require('web.field_utils');
var framework = require('web.framework');
var session = require('web.session');
var utils = require('web.utils');
var view_dialogs = require('web.view_dialogs');

var qweb = core.qweb;
var _t = core._t;


var InputField = AbstractField.extend({
    events: _.extend({}, AbstractField.prototype.events, {
        'input': '_onInput',
    }),
    init: function () {
        this._super.apply(this, arguments);
        if (this.mode === 'edit') {
            this.tagName = 'input';
        }
    },
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    activate: function () {
        this.$el.focus();
        setTimeout(this.$el.select.bind(this.$el), 0);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _renderEdit: function () {
        this.$el.addClass('o_form_input');
        this.$el.attr('type', 'text');
        if (this.attrs.placeholder) {
            this.$el.attr('placeholder', this.attrs.placeholder);
        }
        this.$el.attr('id', this.idForLabel);
        // save cursor position to restore it after updating value
        var selectionStart = this.el.selectionStart;
        var selectionEnd = this.el.selectionEnd;
        this.$el.val(this._formatValue(this.value));
        this.el.selectionStart = selectionStart;
        this.el.selectionEnd = selectionEnd;
    },
    _renderReadonly: function () {
        this.$el.empty().html(this._formatValue(this.value));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Implement keyboard movements.  Mostly useful for its environment, such
     * as a list view.
     *
     * @override
     * @param {any} event
     */
    _onKeydown: function (event) {
        var input = this.$el[0];
        var is_not_selecting;
        switch (event.which) {
            case $.ui.keyCode.DOWN:
                this.trigger_up('move_down');
                break;
            case $.ui.keyCode.UP:
                this.trigger_up('move_up');
                break;
            case $.ui.keyCode.LEFT:
                is_not_selecting = input.selectionEnd === input.selectionStart;
                if (is_not_selecting && input.selectionStart === 0) {
                    this.trigger_up('move_left');
                }
                break;
            case $.ui.keyCode.RIGHT:
                is_not_selecting = input.selectionEnd === input.selectionStart;
                if (is_not_selecting && input.selectionEnd === input.value.length) {
                    this.trigger_up('move_right');
                }
                break;
            case $.ui.keyCode.ENTER:
                this.trigger_up('move_next_line');
                break;
        }
        this._super.apply(this, arguments);
    },
    /**
     * We notify the outside world for each change in this input value. It does
     * not necessarily mean that onchanges will be triggered instantly.
     */
    _onInput: function () {
        this._setValue(this.$el.val());
    },
});

var FieldChar = InputField.extend({
    supportedFieldTypes: ['char', 'text'],
    tagName: 'span',
});

var FieldDate = InputField.extend({
    className: "o_form_field_date",
    tagName: "span",
    replace_element: true,
    supportedFieldTypes: ['date', 'datetime'],

    start: function () {
        var self = this;
        var def;
        if (this.mode === 'edit') {
            this.datewidget = this._makeDatePicker();
            this.datewidget.on('datetime_changed', this, function () {
                if (!this.datewidget.get_value().isSame(this.value)) {
                    this._setValue(this.datewidget.get_value());
                }
            });
            def = this.datewidget.appendTo('<div>').done(function () {
                self.datewidget.$el.addClass(self.$el.attr('class'));
                self.datewidget.$input.addClass('o_form_input');
                self.datewidget.$input.attr('id', self.idForLabel);
                self.replaceElement(self.datewidget.$el);
            });
        }
        return $.when(def, this._super.apply(this, arguments));
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    activate: function () {
        var $input = this.datewidget.$input;
        $input.focus();
        setTimeout($input.select.bind($input), 0);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _makeDatePicker: function () {
        return new datepicker.DateWidget(this);
    },
    _renderEdit: function () {
        this.datewidget.set_value(this.value);
    },
});

var FieldDateTime = FieldDate.extend({
    supportedFieldTypes: ['datetime'],

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _makeDatePicker: function () {
        return new datepicker.DateTimeWidget(this);
    },
});

var FieldMonetary = InputField.extend({
    className: 'o_list_number',
    supportedFieldTypes: ['float', 'monetary'],
    // FieldMonetary overrides _formatValue to ensure that the format_monetary
    // method is used.  This allows this widget to be used with other field
    // types, such as float.
    _formatValue: function (value) {
        var options = _.extend({}, this.nodeOptions, { data: this.recordData });
        return field_utils.format.monetary(value, this.field, options);
    },
    isSet: function () {
        return this.value !== false;
    }
});

var FieldBoolean = AbstractField.extend({
    className: 'o_field_boolean',
    events: _.extend({}, AbstractField.prototype.events, {
        change: '_onChange',
        keydown: '_onKeyDown',
    }),
    replace_element: true,
    supportedFieldTypes: ['boolean'],

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    activate: function () {
        this.$input.focus();
        setTimeout(this.$input.select.bind(this.$input), 0);
    },
    isSet: function () {
        return true;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _renderReadonly: function () {
        var $checkbox = this._formatValue(this.value);
        this.$input = $checkbox.find('input');
        this.$el.empty().append($checkbox);
    },
    _renderEdit: function () {
        this._renderReadonly();
        this.$input.prop('disabled', false);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onChange: function () {
        this._setValue(this.$input[0].checked);
    },
    /**
     * @param {KeyEvent} event
     */
    _onKeydown: function (event) {
        switch (event.which) {
            case $.ui.keyCode.DOWN:
                this.trigger_up('move_down');
                break;
            case $.ui.keyCode.UP:
                this.trigger_up('move_up');
                break;
            case $.ui.keyCode.LEFT:
                this.trigger_up('move_left');
                break;
            case $.ui.keyCode.RIGHT:
                this.trigger_up('move_right');
                break;
            case $.ui.keyCode.TAB:
                this.trigger_up('move_next');
                event.preventDefault();
                break;
            case $.ui.keyCode.ENTER:
                this.$input.prop('checked', !this.value);
                this._setValue(!this.value);
                break;
        }
    },
});

var FieldInteger = InputField.extend({
    supportedFieldTypes: ['integer'],
    isSet: function () {
        return this.value !== false;
    },
});

var FieldFloat = InputField.extend({
    supportedFieldTypes: ['float'],
    _renderReadonly: function () {
        var precision;
        var value = this.value;
        if (this.attrs.digits) {
            precision = this.node.attrs.digits;
        } else {
            precision = this.field.digits;
        }
        if (precision && precision.length === 2) {
            value = utils.round_decimals(value, precision[1]);
        }
        var $span = $('<span>').addClass('o_form_field o_form_field_number').text(this._formatValue(value));
        this.$el.html($span);
    },
    isSet: function () {
        return this.value !== '';
    },
});

var FieldFloatTime = FieldFloat.extend({
    supportedFieldTypes: ['float'],
    _formatValue: function (value) {
        var pattern = '%02d:%02d';
        if (value < 0) {
            value = Math.abs(value);
            pattern = '-' + pattern;
        }
        var hour = Math.floor(value);
        var min = Math.round((value % 1) * 60);
        if (min === 60){
            min = 0;
            hour = hour + 1;
        }
        return _.str.sprintf(pattern, hour, min);
    },
    _parseValue: function (value) {
        var factor = 1;
        if (value[0] === '-') {
            value = value.slice(1);
            factor = -1;
        }
        var float_time_pair = value.split(":");
        if (float_time_pair.length !== 2) {
            return factor * field_utils.parse.float(value, this.field);
        }
        var hours = field_utils.parse.integer(float_time_pair[0]);
        var minutes = field_utils.parse.integer(float_time_pair[1]);
        return factor * (hours + (minutes / 60));
    },
});

var FieldText = AbstractField.extend({
    events: _.extend({}, AbstractField.prototype.events, {
        'input': function () {
            this._setValue(this.$textarea.val());
        },
    }),
    supportedFieldTypes: ['text'],
    start: function () {
        this.$el.addClass('o_list_text o_form_textarea');
        this.$el.attr('id', this.idForLabel);

        if (this.mode === 'edit') {
            // in edit mode, the widget contains a textarea. We append it in
            // start() instead of _renderEdit() to keep the same textarea even
            // if several _renderEdit are done. This allows to keep the cursor
            // position and to autoresize only once
            this.$textarea = $('<textarea>').appendTo(this.$el);
            if (this.attrs.placeholder) {
                this.$textarea.attr('placeholder', this.attrs.placeholder);
            }
            dom.autoresize(this.$textarea, {parent: this});
        }

        return this._super();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    activate: function () {
        var $textarea = this.$('textarea');
        $textarea.focus();
        setTimeout($textarea.select.bind($textarea), 0);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _renderEdit: function () {
        this.$textarea.val(this._formatValue(this.value));
    },
    _renderReadonly: function () {
        this.$el.empty().text(this._formatValue(this.value));
    },
});

var FieldHtml = InputField.extend({
    supportedFieldTypes: ['html'],
    text_to_html: function (text) {
        var value = text || "";
        if (value.match(/^\s*$/)) {
            value = '<p><br/></p>';
        } else {
            value = "<p>"+value.split(/<br\/?>/).join("<br/></p><p>")+"</p>";
            value = value.replace(/<p><\/p>/g, '').replace('<p><p>', '<p>').replace('<p><p ', '<p ').replace('</p></p>', '</p>');
        }
        return value;
    },
    _render: function () {
        this.$el.html(this.text_to_html(this.value));
    },
});

/**
 * displays a handle and allows the resequencing
 * This widget works for integer fields
 */
var HandleWidget = AbstractField.extend({
    tagName: 'span',
    className: 'o_row_handle fa fa-arrows ui-sortable-handle',
    description: "",
    readonly: true,
    replace_element: true,
    supportedFieldTypes: ['integer'],

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * content is only "set" with pure css...
     * @override
     */
    _render: function () {
        this.$el.empty();
    },
});

var EmailWidget = InputField.extend({
    prefix: 'mailto',
    supportedFieldTypes: ['char'],
    init: function () {
        this._super.apply(this, arguments);
        this.tagName = this.mode === 'readonly' ? 'a' : 'input';
    },
    _renderReadonly: function () {
        this.$el.text(this.value)
            .addClass('o_form_uri o_text_overflow')
            .attr('href', this.prefix + ':' + this.value);
    }
});

var FieldPhone = EmailWidget.extend({
    prefix: 'tel',
    init: function () {
        this._super.apply(this, arguments);
        if (this.mode === 'readonly' && !this._can_call()) {
            this.tagName = 'span';
        }
    },
    _renderReadonly: function () {
        this._super();
        if(this._can_call()) {
            var text = this.$el.text();
            this.$el.html(text.substr(0, text.length/2) + "&shy;" + text.substr(text.length/2)); // To prevent Skype app to find the phone number
        } else {
            this.$el.removeClass('o_form_uri');
        }
    },
    _can_call: function () {
        // Phone fields are clickable in readonly on small screens ~= on phones
        // This can be overriden by call-capable modules to display a clickable
        // link in different situations, like always regardless of screen size,
        // or only allow national calls for example.
        return config.device.size_class <= config.device.SIZES.XS;
    }
});

var UrlWidget = InputField.extend({
    supportedFieldTypes: ['char'],
    init: function () {
        this._super.apply(this, arguments);
        this.tagName = this.mode === 'readonly' ? 'a' : 'input';
    },
    _renderReadonly: function () {
        this.$el.text(this.value)
            .addClass('o_form_uri o_text_overflow')
            .attr('href', this.value);
    }
});

var AbstractFieldBinary = AbstractField.extend({
    events: _.extend({}, AbstractField.prototype.events, {
        'change .o_form_input_file': 'on_file_change',
        'click .o_select_file_button': function () {
            this.$('.o_form_input_file').click();
        },
        'click .o_clear_file_button': 'on_clear',
    }),
    init: function (parent, name, record) {
        this._super.apply(this, arguments);
        this.fields = record.fields;
        this.useFileAPI = !!window.FileReader;
        this.max_upload_size = 25 * 1024 * 1024; // 25Mo
        if (!this.useFileAPI) {
            var self = this;
            this.fileupload_id = _.uniqueId('o_fileupload');
            $(window).on(this.fileupload_id, function () {
                var args = [].slice.call(arguments).slice(1);
                self.on_file_uploaded.apply(self, args);
            });
        }
    },
    destroy: function () {
        if (this.fileupload_id) {
            $(window).off(this.fileupload_id);
        }
        this._super.apply(this, arguments);
    },
    on_file_change: function (e) {
        var self = this;
        var file_node = e.target;
        if ((this.useFileAPI && file_node.files.length) || (!this.useFileAPI && $(file_node).val() !== '')) {
            if (this.useFileAPI) {
                var file = file_node.files[0];
                if (file.size > this.max_upload_size) {
                    var msg = _t("The selected file exceed the maximum file size of %s.");
                    this.do_warn(_t("File upload"), _.str.sprintf(msg, utils.human_size(this.max_upload_size)));
                    return false;
                }
                var filereader = new FileReader();
                filereader.readAsDataURL(file);
                filereader.onloadend = function (upload) {
                    var data = upload.target.result;
                    data = data.split(',')[1];
                    self.on_file_uploaded(file.size, file.name, file.type, data);
                };
            } else {
                this.$('form.o_form_binary_form input[name=session_id]').val(this.session.session_id);
                this.$('form.o_form_binary_form').submit();
            }
            this.$('.o_form_binary_progress').show();
            this.$('button').hide();
        }
    },
    on_file_uploaded: function (size, name) {
        if (size === false) {
            this.do_warn(_t("File Upload"), _t("There was a problem while uploading your file"));
            // TODO: use crashmanager
            console.warn("Error while uploading file : ", name);
        } else {
            this.on_file_uploaded_and_valid.apply(this, arguments);
        }
        this.$('.o_form_binary_progress').hide();
        this.$('button').show();
    },
    on_file_uploaded_and_valid: function (size, name, content_type, file_base64) {
        this.set_filename(name);
        this._setValue(file_base64);
        this._render();
    },
    /**
     * We need to update another field.  This method is so deprecated it is not
     * even funny.  We need to replace this with the mechanism of field widgets
     * declaring statically that they need to listen to every changes in other
     * fields
     *
     * @deprecated
     *
     * @param {any} value
     */
    set_filename: function (value) {
        var filename = this.attrs.filename;
        if (filename && filename in this.fields) {
            this.trigger_up('update_field', { name: filename, value: value });
        }
    },
    on_clear: function () {
        this.set_filename('');
        this._setValue(false);
        this._render();
    },
});

var FieldBinaryImage = AbstractFieldBinary.extend({
    template: 'FieldBinaryImage',
    placeholder: "/web/static/src/img/placeholder.png",
    events: _.extend({}, AbstractFieldBinary.prototype.events, {
        'click img': function () {
            if (this.mode === "readonly") {
                this.trigger_up('bounce_edit');
            }
        },
    }),
    supportedFieldTypes: ['binary'],
    _render: function () {
        var self = this;
        var attrs = this.attrs;
        var url = this.placeholder;
        if (this.value) {
            if (!utils.is_bin_size(this.value)) {
                url = 'data:image/png;base64,' + this.value;
            } else {
                url = session.url('/web/image', {
                    model: this.model,
                    id: JSON.stringify(this.res_id),
                    field: this.nodeOptions.preview_image || this.name,
                    // unique forces a reload of the image when the record has been updated
                    unique: (this.recordData.__last_update || '').replace(/[^0-9]/g, ''),
                });
            }
        }
        var $img = $('<img>').attr('src', url);
        $img.css({
            width: this.nodeOptions.size ? this.nodeOptions.size[0] : attrs.img_width || attrs.width,
            height: this.nodeOptions.size ? this.nodeOptions.size[1] : attrs.img_height || attrs.height,
        });
        this.$('> img').remove();
        this.$el.prepend($img);
        $img.on('error', function () {
            self.on_clear();
            $img.attr('src', self.placeholder);
            self.do_warn(_t("Image"), _t("Could not display the selected image."));
        });
    },
    isSet: function () {
        return true;
    },
});

var FieldBinaryFile = AbstractFieldBinary.extend({
    template: 'FieldBinaryFile',
    events: _.extend({}, AbstractFieldBinary.prototype.events, {
        'click': function (event) {
            if (this.mode === 'readonly' && this.value) {
                this.on_save_as(event);
            }
        },
        'click .o_form_input': function () { // eq[0]
            this.$('.o_form_input_file').click();
        },
    }),
    supportedFieldTypes: ['binary'],
    init: function () {
        this._super.apply(this, arguments);
        this.filename_value = this.recordData[this.attrs.filename];
    },
    _renderReadonly: function () {
        this.do_toggle(!!this.value);
        if (this.value) {
            this.$el.empty().append($("<span/>").addClass('fa fa-download'));
            if (this.filename_value) {
                this.$el.append(" " + this.filename_value);
            }
        }
    },
    _renderEdit: function () {
        if(this.value) {
            this.$el.children().removeClass('o_hidden');
            this.$('.o_select_file_button').first().addClass('o_hidden');
            this.$('.o_form_input').eq(0).val(this.filename_value || this.value);
        } else {
            this.$el.children().addClass('o_hidden');
            this.$('.o_select_file_button').first().removeClass('o_hidden');
        }
    },
    set_filename: function (value) {
        this._super.apply(this, arguments);
        this.filename_value = value; // will be used in the re-render
        // the filename being edited but not yet saved, if the user clicks on
        // download, he'll get the file corresponding to the current value
        // stored in db, which isn't the one whose filename is displayed in the
        // input, so we disable the download button
        this.$('.o_save_file_button').prop('disabled', true);
    },
    on_save_as: function (ev) {
        if (!this.value) {
            this.do_warn(_t("Save As..."), _t("The field is empty, there's nothing to save !"));
            ev.stopPropagation();
        } else {
            framework.blockUI();
            var c = crash_manager;
            var filename_fieldname = this.attrs.filename;
            this.session.get_file({
                'url': '/web/content',
                'data': {
                    'model': this.model,
                    'id': this.res_id,
                    'field': this.name,
                    'filename_field': filename_fieldname,
                    'filename': this.recordData[filename_fieldname] || null,
                    'download': true,
                    'data': utils.is_bin_size(this.value) ? null : this.value,
                },
                'complete': framework.unblockUI,
                'error': c.rpc_error.bind(c)
            });
            ev.stopPropagation();
        }
    },
});

var PriorityWidget = AbstractField.extend({
    // the current implementation of this widget makes it
    // only usable for fields of type selection
    className: "o_priority",
    events: {
        'mouseover > a': function (e) {
            clearTimeout(this.hover_timer);
            this.$('.o_priority_star').removeClass('fa-star-o').addClass('fa-star');
            $(e.currentTarget).nextAll().removeClass('fa-star').addClass('fa-star-o');
        },
        'mouseout > a': function () {
            clearTimeout(this.hover_timer);

            var self = this;
            this.hover_timer = setTimeout(function () {
                self._render();
            }, 200);
        },
        'click > a': function (e) {
            e.preventDefault();
            e.stopPropagation();

            var new_value = String($(e.currentTarget).data('value'));
            if(new_value === this.value) {
                new_value = this.empty_value;
            }
            this._setValue(new_value);
        },
    },
    supportedFieldTypes: ['integer'],
    render_star: function (tag, is_full, value, tip) {
        return $(tag)
            .attr('title', tip)
            .attr('data-value', value)
            .addClass('o_priority_star fa')
            .toggleClass('fa-star', is_full)
            .toggleClass('fa-star-o', !is_full);
    },
    _render: function () {
        var self = this;
        var value = parseInt(this.value, 10);
        this.$el.empty();
        this.empty_value = this.field.selection[0][0];
        _.each(this.field.selection.slice(1), function (choice) {
            self.$el.append(self.render_star('<a href="#">', value >= parseInt(choice[0]), choice[0], choice[1]));
        });
    },
});

var AttachmentImage =  AbstractField.extend({
    template: 'AttachmentImage',
});

var StateSelectionWidget = AbstractField.extend({
    template: 'FormSelection',
    events: {
        'click a': function (e) {
            e.preventDefault();
        },
        'click li': 'set_selection'
    },
    prepare_dropdown_values: function () {
        var self = this;
        var _data = [];
        var current_stage_id = self.recordData.stage_id && self.recordData.stage_id[0];
        var stage_data = {
            id: current_stage_id,
            legend_normal: this.recordData.legend_normal || undefined,
            legend_blocked : this.recordData.legend_blocked || undefined,
            legend_done: this.recordData.legend_done || undefined,
        };
        _.map(this.field.selection || [], function (selection_item) {
            var value = {
                'name': selection_item[0],
                'tooltip': selection_item[1],
            };
            if (selection_item[0] === 'normal') {
                value.state_name = stage_data.legend_normal ? stage_data.legend_normal : selection_item[1];
            } else if (selection_item[0] === 'done') {
                value.state_class = 'o_status_green';
                value.state_name = stage_data.legend_done ? stage_data.legend_done : selection_item[1];
            } else {
                value.state_class = 'o_status_red';
                value.state_name = stage_data.legend_blocked ? stage_data.legend_blocked : selection_item[1];
            }
            _data.push(value);
        });
        return _data;
    },
    _render: function () {
        var self = this;
        var states = this.prepare_dropdown_values();
        // Adapt "FormSelection"
        var current_state = _.find(states, function (state) {
            return state.name === self.value;
        });
        this.$('.o_status')
            .removeClass('o_status_red o_status_green')
            .addClass(current_state.state_class);

        // Render "FormSelection.Items" and move it into "FormSelection"
        var $items = $(qweb.render('FormSelection.items', {
            states: _.without(states, current_state)
        }));
        var $dropdown = this.$('.dropdown-menu');
        $dropdown.children().remove(); // remove old items
        $items.appendTo($dropdown);
    },
    set_selection: function (ev) {
        var li = $(ev.target).closest('li');
        if (li.length) {
            var value = String(li.data('value'));
            this._setValue(value);
            if (this.mode === 'edit') {
                this._render();
            }
        }
    },
});

var LabelSelection = AbstractField.extend({
    _render: function () {
        this.classes = this.nodeOptions && this.nodeOptions.classes || {};
        var lbl_class = this.classes[this.value] || 'primary';
        this.$el.addClass('label label-' + lbl_class).text(this._formatValue(this.value));
    },
});

var FieldBooleanButton = AbstractField.extend({
    className: 'o_stat_info',
    supportedFieldTypes: ['boolean'],
    _render: function () {
        this.$el.empty();
        var text, hover;
        switch (this.nodeOptions.terminology) {
            case "active":
                text = this.value ? _t("Active") : _t("Inactive");
                hover = this.value ? _t("Deactivate") : _t("Activate");
                break;
            case "archive":
                text = this.value ? _t("Active") : _t("Archived");
                hover = this.value ? _t("Archive") : _t("Restore");
                break;
            case "close":
                text = this.value ? _t("Active") : _t("Closed");
                hover = this.value ? _t("Close") : _t("Open");
                break;
            default:
                var opt_terms = this.nodeOptions.terminology || {};
                if (typeof opt_terms === 'string') {
                    opt_terms = {}; //unsupported terminology
                }
                text = this.value ? _t(opt_terms.string_true) || _t("On")
                                  : _t(opt_terms.string_false) || _t("Off");
                hover = this.value ? _t(opt_terms.hover_true) || _t("Switch Off")
                                   : _t(opt_terms.hover_false) || _t("Switch On");
        }
        var val_color = this.value ? 'text-success' : 'text-danger';
        var hover_color = this.value ? 'text-danger' : 'text-success';
        var $val = $('<span>').addClass('o_stat_text o_not_hover ' + val_color).text(text);
        var $hover = $('<span>').addClass('o_stat_text o_hover ' + hover_color).text(hover);
        this.$el.append($val).append($hover);
    },
    isSet: function () {
        return true;
    },
});

var FieldID = InputField.extend({
    supportedFieldTypes: ['integer'],
    init: function () {
        this._super.apply(this, arguments);
        this.mode = 'readonly';
    },
});

var StatInfo = AbstractField.extend({
    supportedFieldTypes: ['integer', 'float'],
    _render: function () {
        var options = {
            value: this.value || 0,
        };
        if (! this.nodeOptions.nolabel) {
            if(this.nodeOptions.label_field && this.recordData[this.nodeOptions.label_field]) {
                options.text = this.recordData[this.nodeOptions.label_field];
            } else {
                options.text = this.string;
            }
        }
        this.$el.html(qweb.render("StatInfo", options));
        this.$el.addClass('o_stat_info');
    },
    isSet: function () {
        return true;
    },
});

var FieldPercentPie = AbstractField.extend({
    template: 'FieldPercentPie',
    supportedFieldTypes: ['integer'],
    start: function () {
        this.$left_mask = this.$('.o_mask').first();
        this.$right_mask = this.$('.o_mask').last();
        this.$pie_value = this.$('.o_pie_value');
        return this._super();
    },
    _render: function () {
        var value = this.value || 0;
        var degValue = 360*value/100;

        this.$right_mask.toggleClass('o_full', degValue >= 180);

        var leftDeg = 'rotate(' + ((degValue < 180)? 180 : degValue) + 'deg)';
        var rightDeg = 'rotate(' + ((degValue < 180)? degValue : 0) + 'deg)';
        this.$left_mask.css({transform: leftDeg, msTransform: leftDeg, mozTransform: leftDeg, webkitTransform: leftDeg});
        this.$right_mask.css({transform: rightDeg, msTransform: rightDeg, mozTransform: rightDeg, webkitTransform: rightDeg});

        this.$pie_value.html(Math.round(value) + '%');
    },
    isSet: function () {
        return true;
    },
});

/**
 * FieldProgressBar
 * parameters
 * - title: title of the bar, displayed on top of the bar
 * options
 * - editable: boolean if value is editable
 * - current_value: get the current_value from the field that must be present in the view
 * - max_value: get the max_value from the field that must be present in the view
 * - edit_max_value: boolean if the max_value is editable
 * - title: title of the bar, displayed on top of the bar --> not translated,  use parameter "title" instead
 */
var FieldProgressBar = AbstractField.extend({
    template: "ProgressBar",
    events: {
        'change input': 'on_change_input',
        'input input': 'on_change_input',
        'keyup input': function (e) {
            if(e.which === $.ui.keyCode.ENTER) {
                this.on_change_input(e);
            }
        },
    },
    supportedFieldTypes: ['integer', 'float'],
    init: function () {
        this._super.apply(this, arguments);

        // the progressbar needs the values and not the field name, passed in options
        if (this.recordData[this.nodeOptions.current_value]) {
            this.value = this.recordData[this.nodeOptions.current_value];
        }
        this.max_value = this.recordData[this.nodeOptions.max_value] || 100;
        this.readonly = this.nodeOptions.readonly || !this.nodeOptions.editable;
        this.edit_max_value = this.nodeOptions.edit_max_value || false;
        this.title = _t(this.attrs.title || this.nodeOptions.title) || '';
        this.edit_on_click = !this.nodeOptions.edit_max_value || false;

        this.write_mode = false;
    },
    _render: function () {
        var self = this;
        this._render_value();

        if(!this.readonly) {
            if(this.edit_on_click) {
                this.$el.on('click', '.o_progress', function (e) {
                    var $target = $(e.currentTarget);
                    self.value = Math.floor((e.pageX - $target.offset().left) / $target.outerWidth() * self.max_value);
                    self._render_value();
                    self.on_update(self.value);
                });
            } else {
                this.$el.on('click', function () {
                    if (!self.write_mode) {
                        var $input = $('<input>', {type: 'text', class: 'o_progressbar_value'});
                        $input.on('blur', _.bind(self.on_change_input, self));
                        self.$('.o_progressbar_value').replaceWith($input);
                        self.write_mode = true;
                        self._render_value();
                    }
                });
            }
        }
        return this._super();
    },
    on_update: function (value) {
        if(!isNaN(value)) {
            if (this.edit_max_value) {
                try {
                    this.max_value = this._parseValue(value);
                    this._isValid = true;
                } catch(e) {
                    this._isValid = false;
                }
                var changes = {};
                changes[this.nodeOptions.max_value] = this.max_value;
                this.trigger_up('field_changed', {
                    dataPointID: this.dataPointID,
                    changes: changes,
                });
            } else {
                this._setValue(value);
            }
        }
    },
    on_change_input: function (e) {
        var $input = $(e.target);
        if(e.type === 'change' && !$input.is(':focus')) {
            return;
        }
        if(isNaN($input.val())) {
            this.do_warn(_t("Wrong value entered!"), _t("Only Integer Value should be valid."));
        } else {
            if(e.type === 'input') {
                this._render_value($input.val());
                if(parseFloat($input.val()) === 0) {
                    $input.select();
                }
            } else {
                if(this.edit_max_value) {
                    this.max_value = $(e.target).val();
                } else {
                    this.value = $(e.target).val() || 0;
                }
                var $div = $('<div>', {class: 'o_progressbar_value'});
                this.$('.o_progressbar_value').replaceWith($div);
                this.write_mode = false;

                this._render_value();
                this.on_update(this.edit_max_value ? this.max_value : this.value);
            }
        }
    },
    _render_value: function (v) {
        var value = this.value;
        var max_value = this.max_value;
        if(!isNaN(v)) {
            if(this.edit_max_value) {
                max_value = v;
            } else {
                value = v;
            }
        }
        value = value || 0;
        max_value = max_value || 0;

        var widthComplete;
        if(value <= max_value) {
            widthComplete = value/max_value * 100;
        } else {
            widthComplete = 100;
        }

        this.$('.o_progress').toggleClass('o_progress_overflow', value > max_value);
        this.$('.o_progressbar_complete').css('width', widthComplete + '%');

        if(!this.write_mode) {
            if(max_value !== 100) {
                this.$('.o_progressbar_value').html(utils.human_number(value) + " / " + utils.human_number(max_value));
            } else {
                this.$('.o_progressbar_value').html(utils.human_number(value) + "%");
            }
        } else if(isNaN(v)) {
            this.$('.o_progressbar_value').val(this.edit_max_value ? max_value : value);
            this.$('.o_progressbar_value').focus().select();
        }
    },
    isSet: function () {
        return true;
    },
});

/**
    This widget is intended to be used on boolean fields. It toggles a button
    switching between a green bullet / gray bullet.
*/
var FieldToggleBoolean = AbstractField.extend({
    template: "toggle_button",
    events: {
        'click': 'set_toggle_button'
    },
    supportedFieldTypes: ['boolean'],
    _render: function () {
        var class_name = this.value ? 'o_toggle_button_success' : 'text-muted';
        this.$('i').attr('class', ('fa fa-circle ' + class_name));
    },
    set_toggle_button: function () {
        var toggle_value = !this.value;
        this._setValue(toggle_value);
        if (this.mode === 'edit') {
            this._render();
        }
    },
    isSet: function () {
        return true;
    },
});

var JournalDashboardGraph = AbstractField.extend({
    className: "o_dashboard_graph",
    init: function () {
        this._super.apply(this, arguments);
        this.graph_type = this.attrs.graph_type;
        this.data = JSON.parse(this.value);
    },
    start: function () {
        nv.utils.windowResize(this._onResize.bind(this));
        return this._super.apply(this, arguments);
    },
    destroy: function () {
        nv.utils.offWindowResize(this._onResize);
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _customizeChart: function () {
        if (this.graph_type === 'bar') {
            // Add classes related to time on each bar of the bar chart
            var bar_classes = _.map(this.data[0].values, function (v) {return v.type; });

            _.each(this.$('.nv-bar'), function (v, k){
                // classList doesn't work with phantomJS & addClass doesn't work with a SVG element
                $(v).attr('class', $(v).attr('class') + ' ' + bar_classes[k]);
            });
        }
    },
    /**
     * @private
     */
    _render: function () {
        // note: the rendering of this widget is aynchronous as nvd3 does a
        // setTimeout(0) before executing the callback given to addGraph
        var self = this;
        this.chart = null;
        nv.addGraph(function () {
            self.$svg = self.$el.append('<svg>');
            switch(self.graph_type) {
                case "line":
                    self.$svg.addClass('o_graph_linechart');

                    self.chart = nv.models.lineChart();
                    self.chart.forceY([0]);
                    self.chart.options({
                        x: function (d, u) { return u; },
                        margin: {'left': 0, 'right': 0, 'top': 0, 'bottom': 0},
                        showYAxis: false,
                        showLegend: false,
                    });
                    self.chart.xAxis.tickFormat(function (d) {
                        var label = '';
                        _.each(self.data, function (v){
                            if (v.values[d] && v.values[d].x){
                                label = v.values[d].x;
                            }
                        });
                        return label;
                    });
                    self.chart.yAxis.tickFormat(d3.format(',.2f'));

                    break;

                case "bar":
                    self.$svg.addClass('o_graph_barchart');

                    self.chart = nv.models.discreteBarChart()
                        .x(function (d) { return d.label; })
                        .y(function (d) { return d.value; })
                        .showValues(false)
                        .showYAxis(false)
                        .margin({'left': 0, 'right': 0, 'top': 0, 'bottom': 40});

                    self.chart.xAxis.axisLabel(self.data[0].title);
                    self.chart.yAxis.tickFormat(d3.format(',.2f'));

                    break;
            }
            d3.select(self.$('svg')[0])
                .datum(self.data)
                .transition().duration(1200)
                .call(self.chart);

            self._customizeChart();
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onResize: function () {
        if (this.chart) {
            this.chart.update();
            this._customizeChart();
        }
    },

});

/**
 * The "Domain" field allows the user to construct a technical-prefix domain
 * thanks to a tree-like interface and see the selected records in real time.
 * In debug mode, an input is also there to be able to enter the prefix char
 * domain directly (or to build advanced domains the tree-like interface does
 * not allow to).
 */
var FieldDomain = AbstractField.extend({
    /**
     * The model this field widget works with could be dependant on another
     * field value. This field widget must then be reset when a field is changed
     * in the view.
     */
    resetOnAnyFieldChange: true,

    events: _.extend({}, AbstractField.prototype.events, {
        "click .o_domain_show_selection_button": "_onShowSelectionButtonClick",
        "click .o_form_field_domain_dialog_button": "_onDialogEditButtonClick",
    }),
    custom_events: {
        "domain_changed": "_onDomainSelectorValueChange",
        "domain_selected": "_onDomainSelectorDialogValueChange",
    },
    /**
     * @constructor
     * @override init from AbstractField
     */
    init: function () {
        this._super.apply(this, arguments);

        this.inDialog = !!this.nodeOptions.in_dialog;
        this.modelOption = this.nodeOptions.model;
        this.fsFilters = this.nodeOptions.fs_filters || {};

        this.className = "o_form_field_domain";
        if (this.mode === "edit") {
            this.className += " o_edit_mode";
        }
        if (!this.inDialog) {
            this.className += " o_inline_mode";
        }

        this._initModel();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override isValid from AbstractField.isValid
     * Parsing the char value is not enough for this field. It is considered
     * valid if the internal domain selector was built correctly and that the
     * query to the model to test the domain did not fail.
     *
     * @returns {boolean}
     */
    isValid: function () {
        return (
            this._super.apply(this, arguments)
            && this._isValidForModel
        );
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override _render from AbstractField
     * @returns {Deferred}
     */
    _render: function () {
        // If there is no model, only change the non-domain-selector content
        if (!this.domainModel) {
            this._replaceContent();
            return $.when();
        }

        // Convert char value to array value
        var value = this.value || "[]";
        var domain = Domain.prototype.stringToArray(value);

        // Create the domain selector or change the value of the current one...
        var def;
        if (!this.domainSelector) {
            this.domainSelector = new DomainSelector(this, this.domainModel, domain, {
                readonly: this.mode === "readonly" || this.inDialog,
                filters: this.fsFilters,
                debugMode: session.debug,
            });
            def = this.domainSelector.prependTo(this.$el);
        } else {
            def = this.domainSelector.setDomain(domain);
        }
        // ... then query the model to get the number of matched record if valid
        var self = this;
        return def.then(function () {
            var context = {}; // FIXME ?
            return self.performModelRPC(self.domainModel, "search_count", [
                domain,
                context
            ]).then(
                function (data) {
                    self._isValidForModel = true;
                    return data;
                },
                function (error, e) {
                    e.preventDefault();
                    self._isValidForModel = false;
                }
            ).always(self._replaceContent.bind(self));
        });
    },
    /**
     * Render the field DOM except for the domain selector part. The full field
     * DOM is composed of a DIV which contains the domain selector widget,
     * followed by other content. This other content is handled by this method.
     *
     * @private
     * @param {integer} [nbRecords=0] - The number of records the domain matches
     */
    _replaceContent: function (nbRecords) {
        if (this._$content) {
            this._$content.remove();
        }
        this._$content = $(qweb.render("FieldDomain.content", {
            hasModel: !!this.domainModel,
            isValid: !!this._isValidForModel,
            nbRecords: nbRecords || 0,
            inDialogEdit: this.inDialog && this.mode === "edit",
        }));
        this._$content.appendTo(this.$el);
    },
    /**
     * @override _reset from AbstractField
     * Check if the model the field works with has (to be) changed.
     */
    _reset: function () {
        this._super.apply(this, arguments);
        var oldDomainModel = this.domainModel;
        this._initModel();
        if (this.domainSelector && this.domainModel !== oldDomainModel) {
            // If the model has changed, destroy the current domain selector
            this.domainSelector.destroy();
            this.domainSelector = null;
        }
    },
    /**
     * Checks the model the field must work with. It is either directly given
     * in the field option or it is the value of another field in the view.
     *
     * @private
     */
    _initModel: function () {
        this.domainModel = this.modelOption;
        if (this.recordData.hasOwnProperty(this.domainModel)) {
            this.domainModel = this.recordData[this.domainModel];
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the "Show selection" button is clicked
     * -> Open a modal to see the matched records
     *
     * @param {Event} e
     */
    _onShowSelectionButtonClick: function (e) {
        e.preventDefault();
        new view_dialogs.SelectCreateDialog(this, {
            title: _t("Selected records"),
            res_model: this.domainModel,
            domain: this.value || "[]",
            no_create: true,
            readonly: true,
            disable_multiple_selection: true,
        }).open();
    },
    /**
     * Called when the "Edit domain" button is clicked (when using the in_dialog
     * option) -> Open a DomainSelectorDialog to edit the value
     *
     * @param {Event} e
     */
    _onDialogEditButtonClick: function (e) {
        e.preventDefault();
        new DomainSelectorDialog(this, this.domainModel, this.value || "[]", {
            readonly: this.mode === "readonly",
            filters: this.fsFilters,
            debugMode: session.debug,
        }).open();
    },
    /**
     * Called when the domain selector value is changed (do nothing if it is the
     * one which is in a dialog (@see _onDomainSelectorDialogValueChange))
     * -> Adapt the internal value state
     *
     * @param {OdooEvent} e
     */
    _onDomainSelectorValueChange: function (e) {
        if (this.inDialog) return;
        this._setValue(Domain.prototype.arrayToString(this.domainSelector.getDomain()));
    },
    /**
     * Called when the in-dialog domain selector value is confirmed
     * -> Adapt the internal value state
     *
     * @param {OdooEvent} e
     */
    _onDomainSelectorDialogValueChange: function (e) {
        this._setValue(Domain.prototype.arrayToString(e.data.domain));
    },
});

/**
 * This widget is intended to be used on Text fields. It will provide Ace Editor
 * for editing XML and Python.
 */
var AceEditor = AbstractField.extend({
    template: "AceEditor",
    willStart: function () {
        if (!window.ace && !this.loadJS_def) {
            this.loadJS_def = ajax.loadJS('/web/static/lib/ace/ace.odoo-custom.js').then(function () {
                return $.when(ajax.loadJS('/web/static/lib/ace/mode-python.js'),
                    ajax.loadJS('/web/static/lib/ace/mode-xml.js')
                );
            });
        }
        return $.when(this._super(), this.loadJS_def);
    },
    start: function () {
        this._startAce(this.$('.ace-view-editor')[0]);
        return this._super();
    },
    destroy: function () {
        if (this.aceEditor) {
            this.aceEditor.destroy();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _renderEdit: function () {
        var value = this._formatValue(this.value);
        if (value !== this.lastValue) {
            this.aceSession.setValue(this._formatValue(this.value));
        }
    },
    _renderReadonly: function () {
        this.aceSession.setValue(this._formatValue(this.value));
    },
    _setValue: function (value) {
        this.lastValue = value;
        this._super(value);
    },
    _startAce: function (node) {
        var self = this;
        this.aceEditor = ace.edit(node);
        this.aceEditor.setOptions({
            "maxLines": Infinity,
            showPrintMargin: false,
        });
        if (this.mode === 'readonly') {
            this.aceEditor.renderer.setOptions({
                displayIndentGuides: false,
                showGutter: false,
            });
            this.aceEditor.setOptions({
                highlightActiveLine: false,
                highlightGutterLine: false,
                readOnly: true,
            });
            this.aceEditor.renderer.$cursorLayer.element.style.display = "none";
        }
        this.aceEditor.$blockScrolling = true;
        this.aceSession = this.aceEditor.getSession();
        this.aceSession.setOptions({
            useWorker: false,
            mode: "ace/mode/"+(this.nodeOptions.mode || 'xml'),
            tabSize: 2,
            useSoftTabs: true,
        });
        this.aceEditor.on("change", function () {
            if (self.aceSession.getUndoManager().hasUndo()) {
                self._setValue(self.aceSession.getValue());
            }
        });
    },
});

return {
    EmailWidget: EmailWidget,
    FieldBinaryFile: FieldBinaryFile,
    FieldBinaryImage: FieldBinaryImage,
    FieldBoolean: FieldBoolean,
    FieldBooleanButton: FieldBooleanButton,
    FieldChar: FieldChar,
    FieldDate: FieldDate,
    FieldDateTime: FieldDateTime,
    FieldDomain: FieldDomain,
    FieldFloat: FieldFloat,
    FieldFloatTime: FieldFloatTime,
    FieldHtml: FieldHtml,
    FieldID: FieldID,
    FieldInteger: FieldInteger,
    FieldMonetary: FieldMonetary,
    FieldPercentPie: FieldPercentPie,
    FieldPhone: FieldPhone,
    FieldProgressBar: FieldProgressBar,
    FieldText: FieldText,
    FieldToggleBoolean: FieldToggleBoolean,
    HandleWidget: HandleWidget,
    InputField: InputField,
    AttachmentImage: AttachmentImage,
    LabelSelection: LabelSelection,
    StateSelectionWidget: StateSelectionWidget,
    PriorityWidget: PriorityWidget,
    StatInfo: StatInfo,
    UrlWidget: UrlWidget,
    JournalDashboardGraph: JournalDashboardGraph,
    AceEditor: AceEditor,
};

});
