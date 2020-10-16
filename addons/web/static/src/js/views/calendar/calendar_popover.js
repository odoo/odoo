odoo.define('web.CalendarPopover', function (require) {
"use strict";

var fieldRegistry = require('web.field_registry');
const fieldRegistryOwl = require('web.field_registry_owl');
const FieldWrapper = require('web.FieldWrapper');
var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
var Widget = require('web.Widget');
const { WidgetAdapterMixin } = require('web.OwlCompatibility');

var CalendarPopover = Widget.extend(WidgetAdapterMixin, StandaloneFieldManagerMixin, {
    template: 'CalendarView.event.popover',
    events: {
        'click .o_cw_popover_edit': '_onClickPopoverEdit',
        'click .o_cw_popover_delete': '_onClickPopoverDelete',
    },
    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} eventInfo
     */
    init: function (parent, eventInfo) {
        this._super.apply(this, arguments);
        StandaloneFieldManagerMixin.init.call(this);
        this.hideDate = eventInfo.hideDate;
        this.hideTime = eventInfo.hideTime;
        this.eventTime = eventInfo.eventTime;
        this.eventDate = eventInfo.eventDate;
        this.displayFields = eventInfo.displayFields;
        this.fields = eventInfo.fields;
        this.event = eventInfo.event;
        this.modelName = eventInfo.modelName;
        this._canDelete = eventInfo.canDelete;
    },
    /**
     * @override
     */
    willStart: function () {
        return Promise.all([this._super.apply(this, arguments), this._processFields()]);
    },
    /**
     * @override
     */
    start: function () {
        var self = this;
        _.each(this.$fieldsList, function ($field) {
            $field.appendTo(self.$('.o_cw_popover_fields_secondary'));
        });
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        WidgetAdapterMixin.destroy.call(this);
    },
    /**
     * Called each time the widget is attached into the DOM.
     */
    on_attach_callback: function () {
        WidgetAdapterMixin.on_attach_callback.call(this);
    },
    /**
     * Called each time the widget is detached from the DOM.
     */
    on_detach_callback: function () {
        WidgetAdapterMixin.on_detach_callback.call(this);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @return {boolean}
     */
    isEventDeletable() {
        return this._canDelete;;
    },
    /**
     * @return {boolean}
     */
    isEventDetailsVisible() {
        return true;
    },
    /**
     * @return {boolean}
     */
    isEventEditable() {
        return true;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Generate fields to render into popover
     *
     * @private
     * @returns {Promise}
     */
    _processFields: function () {
        var self = this;
        var fieldsToGenerate = [];
        var fields = _.keys(this.displayFields);
        for (var i=0; i<fields.length; i++) {
            var fieldName = fields[i];
            var displayFieldInfo = self.displayFields[fieldName] || {attrs: {invisible: 1}};
            var fieldInfo = self.fields[fieldName];
            var field = {
                name: fieldName,
                string: displayFieldInfo.attrs.string || fieldInfo.string,
                value: self.event.extendedProps.record[fieldName],
                type: fieldInfo.type,
            };
            if (field.type === 'selection') {
                field.selection = fieldInfo.selection;
            }
            if (field.type === 'monetary') {
                var currencyField = field.currency_field || 'currency_id';
                if (!fields.includes(currencyField) && _.has(self.event.record, currencyField)) {
                    fields.push(currencyField);
                }
            }
            if (fieldInfo.relation) {
                field.relation = fieldInfo.relation;
            }
            if (displayFieldInfo.attrs.widget) {
                field.widget = displayFieldInfo.attrs.widget;
            } else if (_.contains(['many2many', 'one2many'], field.type)) {
                field.widget = 'many2many_tags';
            }
            if (_.contains(['many2many', 'one2many'], field.type)) {
                field.fields = [{
                    name: 'id',
                    type: 'integer',
                }, {
                    name: 'display_name',
                    type: 'char',
                }];
            }
            fieldsToGenerate.push(field);
        };

        this.$fieldsList = [];
        return this.model.makeRecord(this.modelName, fieldsToGenerate).then(function (recordID) {
            var defs = [];

            var record = self.model.get(recordID);
            _.each(fieldsToGenerate, function (field) {
                if (field.invisible) return;
                let isLegacy = true;
                let fieldWidget;
                let FieldClass = fieldRegistryOwl.getAny([field.widget, field.type]);
                if (FieldClass) {
                    isLegacy = false;
                    fieldWidget = new FieldWrapper(this, FieldClass, {
                        fieldName: field.name,
                        record,
                        options: self.displayFields[field.name],
                    });
                } else {
                    FieldClass = fieldRegistry.getAny([field.widget, field.type]);
                    fieldWidget = new FieldClass(self, field.name, record, self.displayFields[field.name]);
                }
                if (fieldWidget.attrs && !_.isObject(fieldWidget.attrs.modifiers)) {
                    fieldWidget.attrs.modifiers = fieldWidget.attrs.modifiers ? JSON.parse(fieldWidget.attrs.modifiers) : {};
                }
                self._registerWidget(recordID, field.name, fieldWidget);

                var $field = $('<li>', {class: 'list-group-item flex-shrink-0 d-flex flex-wrap'});
                var $fieldLabel = $('<strong>', {class: 'mr-2', text: _.str.sprintf('%s : ', field.string)});
                $fieldLabel.appendTo($field);
                var $fieldContainer = $('<div>', {class: 'flex-grow-1'});
                $fieldContainer.appendTo($field);

                let def;
                if (isLegacy) {
                    def = fieldWidget.appendTo($fieldContainer);
                } else {
                    def = fieldWidget.mount($fieldContainer[0]);
                }
                defs.push(def.then(function () {
                    self.$fieldsList.push($field);
                }));
            });
            return Promise.all(defs);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {jQueryEvent} ev
     */
    _onClickPopoverEdit: function (ev) {
        ev.preventDefault();
        this.trigger_up('edit_event', {
            id: this.event.id,
            title: this.event.extendedProps.record.display_name,
        });
    },
    /**
     * @private
     * @param {jQueryEvent} ev
     */
    _onClickPopoverDelete: function (ev) {
        ev.preventDefault();
        this.trigger_up('delete_event', {id: this.event.id});
    },
});

return CalendarPopover;

});
