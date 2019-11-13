odoo.define('web.CalendarPopover', function (require) {
    "use strict";

    const { Component } = owl;

    var { ComponentAdapter } = require('web.OwlCompatibility');
    const fieldRegistry = require('web.field_registry');
    const StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');

    class FieldWidgetAdapter extends ComponentAdapter {
        constructor(parent, props) {
            props.Component = props.widget;
            super(...arguments);
        }

        get widgetArgs() {
            return [this.props.name, this.props.record, this.props.options];
        }

        patched() {
            this.widget._reset(this.props.record);
        }
    }

    class CalendarPopover extends Component {

        /**
         * @constructor
         * @param {Widget} parent
         * @param {Object} eventInfo
         */
        constructor(parent, eventInfo) {
            super(...arguments);
            StandaloneFieldManagerMixin.init.call(this);
            this.hideDate = eventInfo.hideDate;
            this.hideTime = eventInfo.hideTime;
            this.eventTime = eventInfo.eventTime;
            this.eventDate = eventInfo.eventDate;
            this.displayFields = eventInfo.displayFields;
            this.fields = eventInfo.fields;
            this.event = eventInfo.event;
            this.modelName = eventInfo.modelName;
            this.canDelete = eventInfo.canDelete;
        }
        /**
         * @override
         */
        willStart() {
            return Promise.all([super.willStart(...arguments), this._processFields()]);
        }
        /**
         * @override
         */
        mounted() {
            const fieldTarget = this.el.querySelectorAll('.o_cw_popover_fields_secondary')[0];
            this.fieldsList.forEach((field) => {
                fieldTarget.appendChild(field);
            });
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Generate fields to render into popover
         *
         * @private
         * @returns {Promise}
         */
        _processFields() {
            const self = this;
            const fieldsToGenerate = [];
            for (const [fieldName, displayFieldInfo] of Object.entries(this.displayFields)) {
                const fieldInfo = this.fields[fieldName];
                const field = {
                    name: fieldName,
                    string: displayFieldInfo.attrs.string || fieldInfo.string,
                    value: this.event.record[fieldName],
                    type: fieldInfo.type,
                };
                if (field.type === 'selection') {
                    field.selection = fieldInfo.selection;
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

            this.fieldsList = [];
            return this.model.makeRecord(this.modelName, fieldsToGenerate).then(function (recordID) {
                const defs = [];

                const record = self.model.get(recordID);
                fieldsToGenerate.forEach(field => {
                    const FieldClass = fieldRegistry.getAny([field.widget, field.type]);
                    const fieldWidgetAdapter = new FieldWidgetAdapter(this, {
                        name: field.name,
                        record: record,
                        options: self.displayFields[field.name],
                        widget: FieldClass,
                    });

                    const fieldLI = document.createElement('li');
                    fieldLI.classList.add('list-group-item', 'flex-shrink-0', 'd-flex', 'flex-wrap');
                    const fieldLabel = document.createElement('strong');
                    fieldLabel.classList.add('mr-2');
                    fieldLabel.innerHTML = `${field.string} : `;
                    fieldLI.appendChild(fieldLabel);
                    const fieldContainer = document.createElement('div');
                    fieldContainer.classList.add('flex-grow-1');
                    fieldLI.appendChild(fieldContainer);

                    defs.push(fieldWidgetAdapter.mount(fieldContainer).then(function () {
                        self._registerWidget(recordID, field.name, fieldWidgetAdapter.widget);
                        self.fieldsList.push(fieldLI);
                    }));
                });
                return Promise.all(defs);
            });
        }

        /**
         * Mocks _trigger_up to redirect Odoo legacy events to OWL events.
         * TODO: MSH: Maybe remove when basic_model converts all rpc calls
         *
         * @private
         * @param {OdooEvent} ev
         */
        _trigger_up(ev) {
            const evType = ev.name;
            const payload = ev.data;
            if (evType === 'call_service') {
                let args = payload.args || [];
                if (payload.service === 'ajax' && payload.method === 'rpc') {
                    // ajax service uses an extra 'target' argument for rpc
                    args = args.concat(ev.target);
                }
                const service = this.env.services[payload.service];
                const result = service[payload.method].apply(service, args);
                payload.callback(result);
            } else if (evType === 'get_session') {
                if (payload.callback) {
                    payload.callback(this.env.session);
                }
            } else if (evType === 'load_views') {
                const params = {
                    model: payload.modelName,
                    context: payload.context,
                    views_descr: payload.views,
                };
                this.env.dataManager
                    .load_views(params, payload.options || {})
                    .then(payload.on_success);
            } else if (evType === 'load_filters') {
                return this.env.dataManager
                    .load_filters(payload)
                    .then(payload.on_success);
            } else {
                payload.__targetWidget = ev.target;
                this.trigger(evType.replace(/_/g, '-'), payload);
            }
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {jQueryEvent} ev
         */
        _onClickPopoverEdit(ev) {
            this.trigger('edit-event', {
                id: this.event.id,
                title: this.event.record.display_name,
            });
        }
        /**
         * @private
         * @param {jQueryEvent} ev
         */
        _onClickPopoverDelete(ev) {
            this.trigger('delete-event', {id: this.event.id});
        }
    }

    CalendarPopover.template = 'CalendarView.event.popover';
    _.defaults(CalendarPopover.prototype, StandaloneFieldManagerMixin);

    return CalendarPopover;

});
