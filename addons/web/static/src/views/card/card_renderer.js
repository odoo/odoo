import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Field } from "@web/views/fields/field";
import { ViewButton } from "@web/views/view_button/view_button";
import { useViewCompiler } from "@web/views/view_compiler";
import { Widget } from "@web/views/widgets/widget";
import { getFormattedValue } from "../utils";
import { CARD_ATTRIBUTE } from "./card_arch_parser";
import { CardCompiler } from "./card_compiler";

import { Component, computed, onWillUpdateProps, plugin, proxy } from "@odoo/owl";
import { OfflinePlugin } from "@web/core/offline/offline_plugin";

const formatters = registry.category("formatters");

/**
 * Returns a "raw" version of the field value on a given record.
 *
 * @param {Record} record
 * @param {string} fieldName
 * @returns {any}
 */
export function getRawValue(record, fieldName) {
    const field = record.fields[fieldName];
    const value = record.data[fieldName];
    switch (field.type) {
        case "one2many":
        case "many2many": {
            return value.count ? value.currentIds : [];
        }
        case "many2one": {
            return (value && value.id) || false;
        }
        case "date":
        case "datetime": {
            return value && value.toISO();
        }
        default: {
            return value;
        }
    }
}

/**
 * Returns a formatted version of the field value on a given record.
 *
 * @param {Record} record
 * @param {string} fieldName
 * @returns {string}
 */
function getValue(record, fieldName) {
    const field = record.fields[fieldName];
    const value = record.data[fieldName];
    const formatter = formatters.get(field.type, String);
    return formatter(value, { field, data: record.data });
}

export function getFormattedRecord(record) {
    const formattedRecord = {
        id: {
            value: record.resId,
            raw_value: record.resId,
        },
    };

    for (const fieldName of record.fieldNames) {
        formattedRecord[fieldName] = {
            value: getValue(record, fieldName),
            raw_value: getRawValue(record, fieldName),
        };
    }
    return formattedRecord;
}

export class CardRenderer extends Component {
    static components = {
        Field,
        ViewButton,
        Widget,
    };
    static props = ["archInfo", "Compiler?", "readonly?", "record"];
    static CARD_ATTRIBUTE = CARD_ATTRIBUTE;
    static template = "web.CardRenderer";
    static Compiler = CardCompiler;

    _record = computed(() => getFormattedRecord(this.props.record));

    setup() {
        this.evaluateBooleanExpr = evaluateBooleanExpr;
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.offlinePlugin = plugin(OfflinePlugin);

        const { Compiler, archInfo } = this.props;
        const ViewCompiler = Compiler || this.constructor.Compiler;
        const { templateDocs: templates } = archInfo;

        this.templates = useViewCompiler(ViewCompiler, templates);

        this.dataState = proxy({ widget: {} });
        this.createWidget(this.props);
        onWillUpdateProps(this.createWidget);
    }

    get record() {
        return this._record();
    }

    getFormattedValue(fieldId) {
        const { archInfo, record } = this.props;
        const { name } = archInfo.fieldNodes[fieldId];
        return getFormattedValue(record, name, archInfo.fieldNodes[fieldId]);
    }

    /**
     * Assigns "widget" properties on the card record.
     *
     * @param {Object} props
     */
    createWidget(props) {
        this.dataState.widget = {
            deletable: props.archInfo.activeActions.delete && !props.readonly,
            editable: props.archInfo.activeActions.edit && !props.readonly,
        };
    }

    getCardClasses() {
        const { archInfo } = this.props;
        const classes = ["o_card_record d-flex"];
        classes.push(archInfo.cardClassName);
        return classes.join(" ");
    }

    /**
     * Returns the card template's rendering context.
     *
     * Note: the keys answer to outdated standards but should not be altered for
     * the sake of compatibility.
     *
     * @returns {Object}
     */
    get renderingContext() {
        const renderingContext = {
            context: this.props.record.context,
            JSON,
            luxon,
            record: this.record,
            selection_mode: false,
            widget: this.dataState.widget,
            __comp__: Object.assign(Object.create(this), { this: this }),
        };
        return renderingContext;
    }
}
