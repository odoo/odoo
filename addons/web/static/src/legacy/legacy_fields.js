/** @odoo-module **/

import { registry } from "@web/core/registry";
import { sprintf } from "@web/core/utils/strings";
import { Domain } from "web.Domain";
import legacyFieldRegistry from "web.field_registry";
import { ComponentAdapter } from "web.OwlCompatibility";
import { useWowlService } from "@web/legacy/utils";
import { RPCError } from "@web/core/network/rpc_service";
import { useTranslationDialog } from "@web/views/fields/translation_button";

const { Component, useEffect, xml } = owl;
const fieldRegistry = registry.category("fields");

const legacyFieldTemplate = xml`
    <FieldAdapter Component="FieldWidget" fieldParams="fieldParams" update.bind="update" record="props.record" id="props.id"/>`;

// -----------------------------------------------------------------------------
// FieldAdapter
// -----------------------------------------------------------------------------

class FieldAdapter extends ComponentAdapter {
    setup() {
        super.setup();
        this.translationDialog = useTranslationDialog();
        this.wowlEnv = this.env;
        this.env = Component.env;
        this.orm = useWowlService("orm");
        useEffect(() => {
            if (!this.widgetEl || !this.widgetEl.parentElement) {
                return;
            }

            const fieldId = this.props.id;
            if (!this.widgetEl.querySelector(`#${fieldId}`)) {
                const $el = this.widget.getFocusableElement();
                if ($el && $el[0]) {
                    $el[0].setAttribute("id", fieldId);
                }
            }

            // if classNames are given to the field, we only want
            // to add those classes to the legacy field without
            // the parent element affecting the style of the field
            const fieldClassnames =
                this.props.fieldParams.options &&
                this.props.fieldParams.options.attrs &&
                this.props.fieldParams.options.attrs.class;
            if (fieldClassnames) {
                for (const className of fieldClassnames.split(" ")) {
                    this.widgetEl.parentElement.classList.remove(className);
                    this.widgetEl.classList.add(className);
                }
                this.widgetEl.parentElement.style.display = "contents";
            }
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

    async updateWidget(nextProps) {
        const { name, record, options } = nextProps.fieldParams;
        if (this.widget.mode !== options.mode) {
            // the mode changed, we need to instantiate a new FieldWidget
            if (this.oldWidget) {
                this.widget.destroy(); // we were already updating -> abort, and start over
            } else {
                this.oldWidget = this.widget;
            }
            this.widget = new this.props.Component(this, name, record, options);
            this.widgetProm = this.widget._widgetRenderAndInsert(() => {});
            return this.widgetProm;
        } else {
            // the mode is the same, simply reset the FieldWidget with the new record
            await this.widgetProm;
            return this.widget.reset(record, this.lastFieldChangedEvent, true);
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
                const fieldType = record.fields[fieldName].type;
                if (fieldType === "many2one" && value) {
                    value = [value.id, value.display_name];
                } else if (fieldType === "one2many" || fieldType === "many2many") {
                    // TODO map all operations
                    if (value.operation === "ADD_M2M") {
                        const valueIds = value.ids; // can be a lot of stuff
                        let newIds = [];
                        if (Array.isArray(valueIds)) {
                            if (typeof valueIds[0] === "number") {
                                newIds = valueIds; // not sure if it is a real case: a list of ids
                            } else if (valueIds.length && "id" in valueIds[0]) {
                                newIds = valueIds.map((r) => r.id);
                            }
                        } else if ("id" in valueIds && valueIds.id) {
                            newIds = [valueIds.id];
                        } else if ("id" in valueIds) {
                            const fieldName = this.props.fieldParams.name;
                            let newId;
                            try {
                                [newId] = await this.orm.call(
                                    this.props.record.fields[fieldName].relation,
                                    "name_create",
                                    [valueIds.display_name],
                                    {
                                        context: this.props.record.getFieldContext(fieldName),
                                    }
                                );
                            } catch (e) {
                                if (!(e instanceof RPCError)) {
                                    throw e;
                                }
                                if (payload.onFailure) {
                                    // wrap error for guardedCatch compatibility in legacy code
                                    payload.onFailure({
                                        message: e,
                                        event: $.Event(),
                                        legacy: true,
                                    });
                                }
                                return;
                            }
                            newIds = [newId];
                        }
                        value = {
                            resIds: [...record.data[name].res_ids, ...newIds],
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
        } else if (evType === "reload") {
            const record = this.props.record;
            if (payload.db_id === record.id) {
                await record.model.reloadRecords(record);
            } else {
                await record.model.root.load();
                record.model.notify();
            }
            if (payload.onSuccess) {
                payload.onSuccess();
            }
        } else if (evType === "history_back") {
            return this.wowlEnv.config.historyBack();
        } else if (evType === "translate") {
            const { fieldParams, record, update } = this.props;
            return this.translationDialog({
                fieldName: fieldParams.name,
                record,
                updateField: update,
            });
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
        res_ids: staticList.currentIds,
        data: staticList.records.map(mapRecordDatapoint),
        groupedBy: [],
        orderedBy: staticList.orderBy,
        count: staticList.count,
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
    data.id = record.resId;
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
            let legacyRecord;
            const fieldInfo = record.activeFields[name];
            let views = {};
            const modifiers = JSON.parse(fieldInfo.rawAttrs.modifiers || "{}");
            const hasReadonlyModifier = record.isReadonly(name);
            if (record.model.__bm__) {
                legacyRecord = record.model.__bm__.get(record.__bm_handle__);
                const form = legacyRecord.fieldsInfo.form;
                views = form && form[name].views;
            } else {
                legacyRecord = mapRecordDatapoint(record);
            }
            const options = {
                attrs: {
                    ...fieldInfo.rawAttrs,
                    modifiers,
                    options: fieldInfo.options,
                    widget: fieldInfo.widget,
                    views,
                    mode: fieldInfo.viewMode,
                },
                viewType: legacyRecord.viewType,
                mode: this.props.readonly || hasReadonlyModifier ? "readonly" : record.mode,
                hasReadonlyModifier,
            };
            return { name, record: legacyRecord, options };
        }

        update(fieldName, value) {
            if (fieldName === this.props.name) {
                const record = this.props.record;
                const fieldType = record.fields[fieldName].type;
                if (["one2many", "many2many"].includes(fieldType) && !record.model.__bm__) {
                    const staticList = this.props.value;
                    switch (value.operation) {
                        case "REPLACE_WITH": {
                            return staticList.replaceWith(value.resIds);
                        }
                        case "FORGET": {
                            return staticList.delete(value.ids);
                        }
                    }
                }
                return this.props.update(value);
            } else {
                return this.props.record.update({ [fieldName]: value });
            }
        }
    }
    LegacyField.template = legacyFieldTemplate;
    LegacyField.components = { FieldAdapter };
    LegacyField.legacySpecialData = LegacyFieldWidget.prototype.specialData;
    LegacyField.fieldsToFetch = LegacyFieldWidget.prototype.fieldsToFetch || {};
    LegacyField.fieldDependencies = LegacyFieldWidget.prototype.fieldDependencies || {};
    LegacyField.useSubView = LegacyFieldWidget.prototype.useSubview;
    LegacyField.noLabel = LegacyFieldWidget.prototype.noLabel || false;
    if (!fieldRegistry.contains(name)) {
        if (odoo.debug) {
            console.log(`Fields: using legacy ${name} FieldWidget`);
        }
        fieldRegistry.add(name, LegacyField);
    }
}

// register fields already in the legacy registry, and listens to future registrations
for (const [name, FieldWidget] of Object.entries(legacyFieldRegistry.entries())) {
    registerField(name, FieldWidget);
}
legacyFieldRegistry.onAdd(registerField);
