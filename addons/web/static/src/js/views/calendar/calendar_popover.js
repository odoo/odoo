odoo.define('web.CalendarPopover', function (require) {
    "use strict";

    const fieldRegistry = require('web.field_registry');
    const fieldRegistryOwl = require('web.field_registry_owl');
    const FieldWrapper = require('web.FieldWrapper');
    const StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
    const Widget = require('web.Widget');
    const { ComponentAdapter, WidgetAdapterMixin } = require('web.OwlCompatibility');


    const CalendarPopoverFields = Widget.extend(WidgetAdapterMixin, StandaloneFieldManagerMixin, {
        tagName: 'ul',
        className: 'list-group list-group-flush o_cw_popover_fields_secondary',

        /**
         * @constructor
         */
        init(parent, props) {
            this._super(...arguments);
            StandaloneFieldManagerMixin.init.call(this);

            this.props = props;
        },
        /**
         * @override
         */
        async willStart() {
            await this._super(...arguments);
            await this._processFields();
        },
        /**
         * @override
         */
        start() {
            this._super(...arguments);
            this.render();
        },
        render() {
            this.renderElement();
            for (const $field of this.$fieldsList) {
                $field.appendTo(this.$el);
            }
        },
        async update(nextProps) {
            this.props = nextProps;
            await this._processFields();
        },
        /**
         * @override
         */
        destroy() {
            this._super(...arguments);
            WidgetAdapterMixin.destroy.call(this);
        },
        /**
         * Called each time the widget is attached into the DOM.
         */
        on_attach_callback() {
            WidgetAdapterMixin.on_attach_callback.call(this);
        },
        /**
         * Called each time the widget is detached from the DOM.
         */
        on_detach_callback() {
            WidgetAdapterMixin.on_detach_callback.call(this);
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Returns the AbstractField specialization that should be used for the
         * given field informations. If there is no mentioned specific widget to
         * use, determines one according the field type.
         *
         * @private
         * @param {Object} field
         * @param {Object} attrs
         * @returns {function|null} AbstractField specialization Class
         */
        _getFieldWidgetClass(field, attrs) {
            let FieldWidget;
            if (attrs.widget) {
                FieldWidget = fieldRegistry.getAny([
                    'form' + '.' + attrs.widget,
                    attrs.widget
                ]);
                if (!FieldWidget) {
                    console.warn('Missing widget: ', attrs.widget, ' for field',
                        attrs.name, 'of type', field.type);
                }
            }
            return FieldWidget || fieldRegistry.getAny([
                'form' + '.' + field.type,
                field.type,
                'abstract'
            ]);
        },
        /**
         * Generate fields to render into popover
         *
         * @private
         * @returns {Promise}
         */
        async _processFields() {
            const fieldsToGenerate = [];
            const fieldInformation = {};
            const fields = Object.keys(this.props.displayFields);
            for (const fieldName of fields) {
                const displayFieldInfo = this.props.displayFields[fieldName] ||
                    {attrs: {invisible: 1}};
                const fieldInfo = this.props.fields[fieldName];
                fieldInformation[fieldName] = {
                    Widget: this._getFieldWidgetClass(fieldInfo, displayFieldInfo.attrs),
                };
                const field = {
                    name: fieldName,
                    string: displayFieldInfo.attrs.string || fieldInfo.string,
                    value: this.props.record[fieldName],
                    type: fieldInfo.type,
                };
                if (field.type === 'selection') {
                    field.selection = fieldInfo.selection;
                }
                if (field.type === 'monetary') {
                    let currencyField = field.currency_field || 'currency_id';
                    if (!fields.includes(currencyField) &&
                        _.has(this.props.record, currencyField)
                    ) {
                        fields.push(currencyField);
                    }
                }
                if (fieldInfo.relation) {
                    field.relation = fieldInfo.relation;
                }
                if (displayFieldInfo.attrs.widget) {
                    field.widget = displayFieldInfo.attrs.widget;
                } else if (['many2many', 'one2many'].includes(field.type)) {
                    field.widget = 'many2many_tags';
                }
                if (['many2many', 'one2many'].includes(field.type)) {
                    field.fields = [{
                        name: 'id',
                        type: 'integer',
                    }, {
                        name: 'display_name',
                        type: 'char',
                    }];
                }
                fieldsToGenerate.push(field);
            }

            this.$fieldsList = [];
            const recordId = await this.model.makeRecord(
                this.props.modelName, fieldsToGenerate, fieldInformation);
            const defs = [];

            const recordDataPoint = Object.assign({},
                this.model.localData[recordId],
                {res_id: this.props.record.id},
            );
            await this.model._fetchSpecialData(recordDataPoint);
            const record = this.model.get(recordId);

            for (const field of fieldsToGenerate) {
                if (field.invisible) {
                    return;
                }
                let isLegacy = true;
                let fieldWidget;
                let FieldClass = fieldRegistryOwl.getAny([field.widget, field.type]);

                const options = Object.assign({}, this.props.displayFields[field.name]);
                options.attrs = Object.assign({}, options.attrs, {
                    modifiers: typeof options.attrs.modifiers === 'string' ?
                        JSON.parse(options.attrs.modifiers) :
                        options.attrs.modifiers || {},
                    // Remove proxy because "one2many"s write on it
                    options: Object.assign({}, options.attrs.options),
                });

                if (FieldClass) {
                    isLegacy = false;
                    fieldWidget = new FieldWrapper(this, FieldClass, {
                        fieldName: field.name,
                        record,
                        options,
                    });
                } else {
                    FieldClass = fieldRegistry.getAny([field.widget, field.type]);
                    fieldWidget = new FieldClass(this, field.name, record, options);
                }
                this._registerWidget(recordId, field.name, fieldWidget);

                const $field = $('<li>', {
                    class: 'list-group-item flex-shrink-0 d-flex flex-wrap'
                });
                const $fieldLabel = $('<strong>', {
                    class: 'mr-2',
                    text: `${field.string} : `,
                });
                $fieldLabel.appendTo($field);
                const $fieldContainer = $('<div>', {
                    class: 'flex-grow-1'
                });
                $fieldContainer.appendTo($field);

                let def;
                if (isLegacy) {
                    def = fieldWidget.appendTo($fieldContainer);
                } else {
                    def = fieldWidget.mount($fieldContainer[0]);
                }
                defs.push(def.then(() => {
                    this.$fieldsList.push($field);
                }));
            }
            await Promise.all(defs);
        },
    });

    class CalendarPopoverFieldsAdapter extends ComponentAdapter {
        constructor(_, props) {
            props.Component = CalendarPopoverFields;
            super(...arguments);
        }
        get widgetArgs() {
            return [this.props];
        }
        renderWidget() {
            this.widget.render();
        }
        async updateWidget(nextProps) {
            await this.widget.update(nextProps);
        }
    }

    class CalendarPopover extends owl.Component {
        /**
         * @returns {boolean}
         */
        get displayControls() {
            return true;
        }
        /**
         * @returns {boolean}
         */
        get displayEventDetails() {
            return true;
        }
        /**
         * @returns {Object}
         */
        get displayedFields() {
            return this.props.displayFields;
        }
        /**
         * @returns {boolean}
         */
        get isEventDeletable() {
            return this.props.deletable;
        }
        /**
         * @returns {boolean}
         */
        get isEventEditable() {
            return true;
        }
    }
    CalendarPopover.components = {
        CalendarPopoverFieldsAdapter,
    };
    /*
    CalendarPopover.props = {
        date: {
            type: [Object,Proxy],
            shape: {
                duration: { type: String, optional: true, },
                hide: Boolean,
                value: { type: String, optional: true, },
            },
        },
        deletable: Boolean,
        eventId: [String, Number],
        headerColorClass: String,
        target: String,
        time: {
            type: [Object,Proxy],
            shape: {
                duration: { type: String, optional: true, },
                hide: Boolean,
                value: { type: String, optional: true, },
            },
        },
        title: String,

        modelName: String,
        displayFields: [Object, Proxy],
        fields: [Object, Proxy],
        record: [Object, Proxy],
    };
    */
    CalendarPopover.template = 'web.CalendarPopover';

    class CalendarYearPopover extends owl.Component {
        /**
         * @returns {Boolean}
         */
        get isEventCreateable() {
            return this.props.createable;
        }
    }
    /*
    CalendarYearPopover.props = {
        createable: Boolean,
        date: Date,
        groupedEvents: Object,
        groupKeys: {
            type: Array,
            element: String,
        },
        target: String,
    };
    */
    CalendarYearPopover.template = 'web.CalendarYearPopover';

    return {
        CalendarPopover,
        CalendarYearPopover,
    };

});
