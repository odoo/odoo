/** @odoo-module **/

import { registry } from "@web/core/registry";
import { sprintf } from "@web/core/utils/strings";
import { Domain } from "web.Domain";
import legacyFieldRegistry from "web.field_registry";
import { ComponentAdapter } from "web.OwlCompatibility";
import viewUtils from "web.viewUtils";

const { Component, useEffect, xml } = owl;
const fieldRegistry = registry.category("fields");

const legacyFieldTemplate = xml`
    <FieldAdapter Component="FieldWidget" fieldParams="fieldParams" update.bind="update"/>`;

// -----------------------------------------------------------------------------
// FieldAdapter
// -----------------------------------------------------------------------------

class FieldAdapter extends ComponentAdapter {
    setup() {
        super.setup();
        this.wowlEnv = this.env;
        this.env = Component.env;
        useEffect(() => {
            this.widgetEl.parentElement.classList.remove("o_text_overflow");
            this.widgetEl.classList.add("o_legacy_field_widget");
        });
        this.lastFieldChangedEvent = null;
    }
    /**
     * @override
     */
    get widgetArgs() {
        const { name, record, options } = this.props.fieldParams;
        return [name, record, options];
    }

    updateWidget(nextProps) {
        const { name, record, options } = nextProps.fieldParams;
        if (this.widget.mode !== options.mode) {
            // the mode changed, we need to instantiate a new FieldWidget
            if (this.oldWidget) {
                this.widget.destroy(); // we were already updating -> abort, and start over
            } else {
                this.oldWidget = this.widget;
            }
            this.widget = new this.props.Component(this, name, record, options);
            return this.widget._widgetRenderAndInsert(() => {});
        } else {
            // the mode is the same, simply reset the FieldWidget with the new record
            this.widget.reset(record, this.lastFieldChangedEvent);
        }
    }
    renderWidget() {
        if (this.oldWidget) {
            const parentEl = this.oldWidget.el.parentElement;
            parentEl.replaceChild(this.widget.el, this.oldWidget.el);
            this.widgetEl = this.widget.el;
            if (this.widget.on_attach_callback) {
                this.widget.on_attach_callback();
            }
            this.oldWidget.destroy();
            this.oldWidget = null;
        }
    }

    async _trigger_up(ev) {
        const evType = ev.name;
        const payload = ev.data;
        if (evType === "set_dirty") {
            // TODO (not yet handled in the Record datapoint)
        } else if (evType === "field_changed") {
            const { name, record } = this.props.fieldParams;
            const proms = [];
            for (const fieldName in payload.changes) {
                let value = payload.changes[fieldName];
                const fieldType = record.fields[name].type;
                if (fieldType === "many2one" && value) {
                    value = [value.id, value.display_name];
                } else if (fieldType === "one2many" || fieldType === "many2many") {
                    // TODO map all operations
                    if (value.operation === "ADD_M2M") {
                        value = {
                            // FIXME value.ids could be a lot of stuff :/
                            resIds: [...record.data[name].res_ids, value.ids.id],
                            operation: "REPLACE_WITH",
                        };
                    }
                } else if (fieldType === "date" || fieldType === "datetime") {
                    // from moment to luxon
                    value = value ? luxon.DateTime.fromISO(value.toISOString()) : false;
                }
                proms.push(this.props.update(fieldName, value));
            }
            this.lastFieldChangedEvent = ev;
            await Promise.all(proms);
            if (payload.onSuccess) {
                payload.onSuccess();
            }
            // TODO: handle onFailure?
        }
        super._trigger_up(...arguments);
    }
}

// -----------------------------------------------------------------------------
// Helpers to map wowl datapoints to basic model datapoints
// -----------------------------------------------------------------------------

let nextId = 1;
function createMany2OneDatapoint([resId, displayName]) {
    return {
        id: `m2o_${nextId++}`,
        data: { id: resId, display_name: displayName },
        fields: {
            display_name: { type: "char" },
            id: { type: "integer" },
        },
        res_id: resId,
        ref: resId,
    };
}

function mapDatapoint(datapoint) {
    return {
        id: datapoint.id,
        model: datapoint.resModel,
        fields: datapoint.fields,
        fieldsInfo: {
            default: datapoint.activeFields, // TODO: how to handle viewTypes?
        },
        getContext: () => [], // TODO: not yet handled in wowl
        getDomain: () => [], // TODO: not yet handled in wowl
        getFieldNames: () => datapoint.fieldNames,
    };
}

function mapStaticListDatapoint(staticList) {
    return {
        ...mapDatapoint(staticList),
        res_ids: staticList.resIds,
        data: staticList.records.map(mapRecordDatapoint),
        groupedBy: [],
        orderedBy: staticList.orderBy,
    };
}

export function mapRecordDatapoint(record) {
    const data = Object.assign({}, record.data);
    for (const fieldName of record.fieldNames) {
        const fieldType = record.fields[fieldName].type;
        switch (fieldType) {
            case "one2many":
            case "many2many":
                data[fieldName] = mapStaticListDatapoint(data[fieldName]);
                break;
            case "many2one":
                data[fieldName] = data[fieldName] && createMany2OneDatapoint(data[fieldName]);
                break;
            case "date":
            case "datetime":
                // from luxon to moment
                data[fieldName] = data[fieldName] ? moment(data[fieldName].toISO()) : false;
        }
    }
    const basicModelRecord = {
        ...mapDatapoint(record),
        res_id: record.resId,
        data,
    };
    Object.defineProperty(basicModelRecord, "evalContext", {
        get: () => record.evalContext,
    });
    Object.defineProperty(basicModelRecord, "isDirty", {
        get: () => record.isDirty,
    });
    Object.defineProperty(basicModelRecord, "isNew", {
        get: () => record.isDirty,
    });
    basicModelRecord.evalModifiers = (modifiers) => {
        let evalContext = null;
        const evaluated = {};
        for (const k of ["invisible", "column_invisible", "readonly", "required"]) {
            const mod = modifiers[k];
            if (mod === undefined || mod === false || mod === true) {
                if (k in modifiers) {
                    evaluated[k] = !!mod;
                }
                continue;
            }
            try {
                evalContext = evalContext || basicModelRecord.evalContext;
                evaluated[k] = new Domain(mod, evalContext).compute(evalContext);
            } catch (e) {
                throw new Error(sprintf('for modifier "%s": %s', k, e.message));
            }
        }
        return evaluated;
    };
    return basicModelRecord;
}

// -----------------------------------------------------------------------------
// Register legacy field widgets to the wowl field registry (wrapped in a Component)
// -----------------------------------------------------------------------------

function registerField(name, LegacyFieldWidget) {
    class LegacyField extends Component {
        setup() {
            this.FieldWidget = LegacyFieldWidget;
        }
        get fieldParams() {
            const { name, record } = this.props;
            if (record.model.__bm__) {
                const legacyRecord = record.model.__bm__.get(record.__bm_handle__);
                const options = {
                    viewType: legacyRecord.viewType,
                    hasReadonlyModifier: record.isReadonly(name),
                    mode: record.mode,
                };
                return { name, record: legacyRecord, options };
            } else {
                const legacyRecord = mapRecordDatapoint(record);
                const fieldInfo = record.activeFields[name];
                const views = {};
                for (const viewType in fieldInfo.views || {}) {
                    let arch = fieldInfo.views[viewType].arch;
                    if (viewType === "list") {
                        const editable = fieldInfo.views.list.editable;
                        arch = `<tree editable='${editable}'></tree>`;
                    }
                    // FIXME: need the legacy fieldInfo here
                    views[viewType] = {
                        ...fieldInfo.views[viewType],
                        arch: viewUtils.parseArch(arch),
                    };
                }
                const options = {
                    attrs: {
                        ...fieldInfo.attrs,
                        modifiers: JSON.parse(fieldInfo.attrs.modifiers || "{}"),
                        options: fieldInfo.options,
                        widget: fieldInfo.widget,
                        views,
                        mode: fieldInfo.viewMode,
                    },
                    mode: record.mode,
                };
                return { name, record: legacyRecord, options };
            }
        }
        update(fieldName, value) {
            if (fieldName === this.props.name) {
                return this.props.update(value);
            } else {
                return this.props.record.update({ [fieldName]: value });
            }
        }
    }
    LegacyField.template = legacyFieldTemplate;
    LegacyField.components = { FieldAdapter };
    LegacyField.fieldsToFetch = LegacyFieldWidget.prototype.fieldsToFetch || {};
    if (!fieldRegistry.contains(name)) {
        console.log(`Fields: using legacy ${name} FieldWidget`);
        fieldRegistry.add(name, LegacyField);
    }
}

// register fields already in the legacy registry, and listens to future registrations
for (const [name, FieldWidget] of Object.entries(legacyFieldRegistry.entries())) {
    registerField(name, FieldWidget);
}
legacyFieldRegistry.onAdd(registerField);
