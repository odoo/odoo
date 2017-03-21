odoo.define('web.KanbanRecord', function (require) {
"use strict";

/**
 * This file defines the KanbanRecord widget, which corresponds to a card in
 * a Kanban view.
 */

var core = require('web.core');
var Domain = require('web.Domain');
var field_utils = require('web.field_utils');
var utils = require('web.utils');
var Widget = require('web.Widget');

var _t = core._t;
var QWeb = core.qweb;

var KanbanRecord = Widget.extend({
    events: {
        'click .oe_kanban_action': '_onKanbanActionClicked',
        'click .o_kanban_manage_toggle_button': '_onManageTogglerClicked',
    },
    /**
     * @override
     */
    init: function (parent, state, options) {
        this._super(parent);

        this.fields = state.fields;
        this.fieldAttrs = state.fieldAttrs;
        this.modelName = state.model;

        this.options = options;
        this.editable = options.editable;
        this.deletable = options.deletable;
        this.draggable = options.draggable;
        this.read_only_mode = options.read_only_mode;
        this.qweb = options.qweb;
        this.subWidgets = {};

        this._setState(state);
    },
    start: function () {
        return this._super.apply(this, arguments).then(this._render.bind(this));
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Re-renders the record with a new state
     *
     * @param {Object} state
     */
    update: function (state) {
        // detach the widgets because the record will empty its $el, which will
        // remove all event handlers on its descendants, and we want to keep
        // those handlers alive as we will re-use these widgets
        _.invoke(_.pluck(this.subWidgets, '$el'), 'detach');
        this._setState(state);
        this._render();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Processes each 'field' tag and replaces it by the specified widget, if
     * any, or directly by the formatted value
     *
     * @private
     */
    _processFields: function () {
        var self = this;
        this.$("field").each(function () {
            var $field = $(this);
            var field_name = $field.attr("name");
            var field_widget = $field.attr("widget");
            if (field_widget) {
                // a widget is specified for that field
                var widget = self.subWidgets[field_name];
                if (!widget) {
                    // the widget doesn't exist yet, so instanciate it
                    var Widget = self.fieldAttrs[field_name].Widget;
                    if (Widget) {
                        // some field's attrs might be record dependent (they start with
                        // 't-att-') and should thus be evaluated, which is done by qweb
                        // we here replace those attrs in the dict of attrs of the state
                        // by their evaluted value, to make it transparent from the
                        // field's widgets point of view
                        // that dict being shared between records, we don't modify it
                        // in place
                        var attrs = Object.create(null);
                        _.each(self.fieldAttrs[field_name], function (value, key) {
                            if (_.str.startsWith(key, 't-att-')) {
                                key = key.slice(6);
                                value = $field.attr(key);
                            }
                            attrs[key] = value;
                        });
                        self.fieldAttrs[field_name] = attrs;

                        widget = new Widget(self, field_name, self.state, self.options);
                        self.subWidgets[field_name] = widget;
                        self._setFieldDisplay(widget, field_name);
                        widget.replace($field);
                    } else if (core.debug) {
                        // the widget is not implemented
                        $field.replaceWith($('<span>', {
                            text: _.str.sprintf(_t('[No widget %s]'), field_widget),
                        }));
                    }
                } else {
                    // a widget already exists for that field, so reset it with the new state
                    widget.reset(self.state);
                    $field.replaceWith(widget.$el);
                }
            } else {
                // no widget specified for that field, so simply use a formatter
                // note: we could have used the widget corresponding to the field's type, but
                // it is much more efficient to use a formatter
                var field = self.fields[field_name];
                var value = self.recordData[field_name];
                var options = { data: self.recordData };
                var formatted_value = field_utils.format[field.type](value, field, options);
                $field.replaceWith(formatted_value);
            }
        });
    },
    /**
     * @private
     */
    _attachTooltip: function () {
        var self = this;
        this.$('[tooltip]').each(function () {
            var $el = $(this);
            var tooltip = $el.attr('tooltip');
            if (tooltip) {
                $el.tooltip({
                    'html': true,
                    'title': self.qweb.render(tooltip, self.qweb_context)
                });
            }
        });
    },
    /**
     * @private
     * @param {string} d a stringified domain
     * @returns {boolean} the domain evaluted with the current values
     */
    _computeDomain: function (d) {
        return new Domain(d).compute(this.recordData);
    },
    /**
     * Generates the color classname from a given variable
     *
     * @private
     * @param {number || string} variable
     * @return {string} the classname
     */
    _getColorClassname: function (variable) {
        var color = this._getColorID(variable);
        return 'oe_kanban_color_' + color;
    },
    /**
     * Computes a color id between 0 and 10 from a given value
     *
     * @private
     * @param {number || string} variable
     * @returns {integer} the color id
     */
    _getColorID: function (variable) {
        if (typeof(variable) === 'number') {
            return Math.round(variable) % 10;
        }
        if (typeof(variable) === 'string') {
            var index = 0;
            for (var i=0; i<variable.length; i++) {
                index += variable.charCodeAt(i);
            }
            return index % 10;
        }
        return 0;
    },
    /**
     * @private
     * @param {string} model the name of the model
     * @param {string} field the name of the field
     * @param {integer} id the id of the resource
     * @param {integer} cache the cache duration, in seconds
     * @param {Object} options
     * @returns {string} the url of the image
     */
    _getImageURL: function (model, field, id, cache, options) {
        options = options || {};
        var url;
        if (this.record[field] && this.record[field].value && !utils.is_bin_size(this.record[field].value)) {
            url = 'data:image/png;base64,' + this.record[field].value;
        } else if (this.record[field] && ! this.record[field].value) {
            url = "/web/static/src/img/placeholder.png";
        } else {
            if (_.isArray(id)) { id = id[0]; }
            if (!id) { id = undefined; }
            if (options.preview_image)
                field = options.preview_image;
            var unique = this.record.__last_update && this.record.__last_update.value.replace(/[^0-9]/g, '');
            var session = this.getSession();
            url = session.url('/web/image', {model: model, field: field, id: id, unique: unique});
            if (cache !== undefined) {
                // Set the cache duration in seconds.
                url += '&cache=' + parseInt(cache, 10);
            }
        }
        return url;
    },
    /**
     * Triggers up an event to open the record
     *
     * @private
     */
    _openRecord: function () {
        var editMode = this.$el.hasClass('oe_kanban_global_click_edit');
        this.trigger_up('open_record', {
            id: this.db_id,
            mode: editMode ? 'edit' : 'readonly',
        });
    },
    /**
     * Renders the record
     */
    _render: function () {
        this.replaceElement(this.qweb.render('kanban-box', this.qweb_context));
        this.$el.addClass('o_kanban_record');
        this.$el.data('record', this);
        if (this.$el.hasClass('oe_kanban_global_click') ||
            this.$el.hasClass('oe_kanban_global_click_edit')) {
            this.$el.on('click', this._onGlobalClick.bind(this));
        }
        this._processFields();
        this._setupColor();
        this._setupColorPicker();
        this._renderM2MTags();
        this._attachTooltip();
    },
    /**
     * @private
     */
    _renderM2MTags: function () {
        var self = this;
        _.each(this.recordData, function (values, field_name) {
            if (self.fields[field_name].type !== 'many2many') { return; }
            var rel_ids = self.record[field_name].raw_value;
            var $m2m_tags = self.$('.o_form_field_many2manytags[name=' + field_name + ']');
            _.each(rel_ids, function (id) {
                var m2m = _.findWhere(values.data, {res_id: id}).data;
                if (typeof m2m.color !== 'undefined' && m2m.color !== 10) { // 10th color is invisible
                    $('<span>')
                        .addClass('o_tag o_tag_color_' + m2m.color)
                        .attr('title', _.str.escapeHTML(m2m.display_name))
                        .appendTo($m2m_tags);
                }
            });
        });
        // We use boostrap tooltips for better and faster display
        this.$('span.o_tag').tooltip({delay: {'show': 50}});
    },
    /**
     * Sets particular classnames on a field widget's $el according to the
     * field's attrs (display or bold attributes)
     *
     * @private
     * @param {Widget} widget a field widget
     * @param {string} fieldName
     */
    _setFieldDisplay: function (widget, fieldName) {
        // attribute display
        if (this.fieldAttrs[fieldName].display === 'right') {
            widget.$el.addClass('pull-right');
        } else if (this.fieldAttrs[fieldName].display === 'full') {
            widget.$el.addClass('o_text_block');
        }

        // attribute bold
        if (this.fieldAttrs[fieldName].bold) {
            widget.$el.addClass('o_text_bold');
        }
    },
    /**
     * Sets internal values of the kanban record according to the given state
     *
     * @private
     * @param {Object} recordState
     */
    _setState: function (recordState) {
        this.state = recordState;
        this.id = recordState.res_id;
        this.db_id = recordState.id;
        this.recordData = recordState.data;
        this.record = this._transformRecord(recordState.data);
        this.qweb_context = {
            kanban_image: this._getImageURL.bind(this),
            kanban_color: this._getColorClassname.bind(this),
            kanban_getcolor: this._getColorID.bind(this),
            kanban_compute_domain: this._computeDomain.bind(this),
            read_only_mode: this.read_only_mode,
            record: this.record,
            user_context: this.getSession().user_context,
            widget: this,
        };
    },
    /**
     * If an attribute `color` is set on the kanban record, adds the
     * corresponding color classname.
     *
     * @private
     */
    _setupColor: function () {
        var color_field = this.$el.attr('color');
        if (color_field && color_field in this.fields) {
            var colorClass = this._getColorClassname(this.recordData[color_field]);
            this.$el.addClass(colorClass);
        }
    },
    /**
     * Renders the color picker in the kanban record, and binds the event handler
     *
     * @private
     */
    _setupColorPicker: function () {
        var $colorpicker = this.$('ul.oe_kanban_colorpicker');
        if (!$colorpicker.length) {
            return;
        }
        $colorpicker.html(QWeb.render('KanbanColorPicker'));
        $colorpicker.on('click', 'a', this._onColorChanged.bind(this));
    },
    /**
     * Builds an object containing the formatted record data used in the
     * template
     *
     * @private
     * @param {Object} recordData
     * @returns {Object} transformed record data
     */
    _transformRecord: function (recordData) {
        var self = this;
        var new_record = {};
        _.each(this.state.fieldNames, function (name) {
            var value = recordData[name];
            var r = _.clone(self.fields[name] || {});

            if ((r.type === 'date' || r.type === 'datetime') && value) {
                r.raw_value = value.toDate();
            } else if (r.type === 'one2many' || r.type === 'many2many') {
                r.raw_value = value.count ? value.res_ids : false;
            } else if (r.type === 'many2one' ) {
                r.raw_value = value && value.res_id || false;
            } else {
                r.raw_value = value;
            }

            if (r.type) {
                var formatter = field_utils.format[r.type];
                r.value = formatter(value, self.fields[name], recordData, self.state);
            } else {
                r.value = value;
            }

            new_record[name] = r;
        });
        return new_record;
    },
    /**
     * Notifies the controller that the record has changed
     *
     * @private
     * @param {Object} data the new values
     */
    _updateRecord: function (data) {
        this.trigger_up('kanban_record_update', data);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onColorChanged: function (event) {
        event.preventDefault();
        var data = {};
        var color_field = $(event.delegateTarget).data('field') || 'color';
        data[color_field] = $(event.currentTarget).data('color');
        this.trigger_up('kanban_record_update', data);
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onGlobalClick: function (event) {
        if ($(event.target).parents('.o_dropdown_kanban').length) {
            return;
        }
        var trigger = true;
        var elem = event.target;
        var ischild = true;
        var children = [];
        while (elem) {
            var events = $._data(elem, 'events');
            if (elem === event.currentTarget) {
                ischild = false;
            }
            var test_event = events && events.click && (events.click.length > 1 || events.click[0].namespace !== "tooltip");
            if (ischild) {
                children.push(elem);
                if (test_event) {
                    // do not trigger global click if one child has a click event registered
                    trigger = false;
                }
            }
            if (trigger && test_event) {
                _.each(events.click, function (click_event) {
                    if (click_event.selector) {
                        // For each parent of original target, check if a
                        // delegated click is bound to any previously found children
                        _.each(children, function (child) {
                            if ($(child).is(click_event.selector)) {
                                trigger = false;
                            }
                        });
                    }
                });
            }
            elem = elem.parentElement;
        }
        if (trigger) {
            this._openRecord();
        }
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onKanbanActionClicked: function (event) {
        event.preventDefault();

        var $action = $(event.currentTarget);
        var type = $action.data('type') || 'button';

        switch (type) {
            case 'edit':
                this.trigger_up('open_record', {id: this.db_id, mode: 'edit'});
                break;
            case 'open':
                this.trigger_up('open_record', {id: this.db_id});
                break;
            case 'delete':
                this.trigger_up('kanban_record_delete', {id: this.db_id, record: this});
                break;
            case 'action':
            case 'object':
                this.trigger_up('button_clicked', {
                    attrs: $action.data(),
                    record: this.state,
                });
                break;
            default:
                this.do_warn("Kanban: no action for type : " + type);
        }
    },
    /**
     * Toggles the configuration panel of the record
     *
     * @private
     * @param {MouseEvent} event
     */
    _onManageTogglerClicked: function (event) {
        event.preventDefault();
        this.$('.o_kanban_card_content').toggleClass('o_visible o_invisible');
        this.$('.o_kanban_card_manage_pane').toggleClass('o_visible o_invisible');
        var colorClass = this._getColorClassname(this.recordData.color || 0);
        this.$('.o_kanban_manage_button_section').toggleClass(colorClass);
    },
});

return KanbanRecord;

});
