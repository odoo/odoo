/** @odoo-module **/

import { Domain } from "../../core/domain";
import { useService } from "../../core/service_hook";
import { Field } from "../../fields/field";
import { FormCompiler } from "../../views/form/form_compiler";
import { ViewButton } from "../view_button/view_button";
import { url } from "../../core/utils/urls";
import { FieldColorPicker, fileTypeMagicWordMap } from "../../fields/basic_fields";

const { Component } = owl;
const { useState, useSubEnv } = owl.hooks;

const { RECORD_COLORS } = FieldColorPicker;

const templateIds = {};
let nextKanbanCardId = 1;

const isBinSize = (value) => /^\d+(\.\d*)? [^0-9]+$/.test(value);

export class KanbanRenderer extends Component {
    setup() {
        let templateId = templateIds[this.props.info.arch];
        if (!templateId) {
            const formCompiler = new FormCompiler(this.env.qweb, this.props.info.fields);
            const xmldoc = formCompiler.compile(this.props.info.xmlDoc);
            console.group("Compiled template:");
            console.dirxml(xmldoc);
            console.groupEnd();
            templateId = `__kanban_card__${nextKanbanCardId++}`;
            this.env.qweb.addTemplate(templateId, xmldoc.outerHTML);
            templateIds[this.props.info.arch] = templateId;
        }
        this.record = this.props.record || this.props.model.root;
        this.cardTemplate = templateId;
        this.cards = this.props.info.cards;
        this.className = this.props.info.className;
        this.state = useState({});
        this.action = useService("action");
        useSubEnv({ model: this.props.model });
    }

    openRecord(record) {
        const resIds = this.props.model.root.data.map((datapoint) => datapoint.resId);
        this.action.switchView("form", { resId: record.resId, resIds });
    }

    evalDomain(record, expr) {
        const domain = new Domain(expr);
        return domain.contains(record.data);
    }

    isFieldEmpty(record, fieldName, widgetName) {
        const cls = Field.getTangibleField(record, widgetName, fieldName);
        if ("isEmpty" in cls) {
            return cls.isEmpty(record, fieldName);
        }
        return !record.data[fieldName];
    }

    getWidget(widgetName) {
        class toImplement extends Component {}
        toImplement.template = owl.tags.xml`<div>${widgetName}</div>`;
        return toImplement;
    }

    getColumnTitle(group) {
        const { groupData } = group;
        const [groupByField] = this.props.model.root.groupBy;
        const value = groupData[groupByField];
        return Array.isArray(value) ? value[1] : value;
    }

    //-------------------------------------------------------------------------
    // KANBAN SPECIAL FUNCTIONS
    //
    // Note: these are snake_cased with a not-so-self-explanatory name for the
    // sake of compatibility.
    //-------------------------------------------------------------------------

    /**
     * Returns the image URL of a given record.
     * @param {string} model model name
     * @param {string} field field name
     * @param {number | number[]} idOrIds
     * @param {string} placeholder
     * @returns {string}
     */
    kanban_image(model, field, idOrIds, placeholder) {
        const id = (Array.isArray(idOrIds) ? idOrIds[0] : idOrIds) || null;
        const record = this.props.model.get({ resId: id }) || { data: {} };
        const value = record.data[field];
        if (value && !isBinSize(value)) {
            // Use magic-word technique for detecting image type
            const type = fileTypeMagicWordMap[value[0]];
            return `data:image/${type};base64,${value}`;
        } else if (placeholder && (!model || !field || !id || !value)) {
            // Placeholder if either the model, field, id or value is missing or null.
            return placeholder;
        } else {
            // Else: fetches the image related to the given id.
            return url("/web/image", { model, field, id });
        }
    }

    /**
     * Returns the class name of a record according to its color.
     */
    kanban_color(value) {
        return `oe_kanban_color_${this.kanban_getcolor(value)}`;
    }

    /**
     * Returns the index of a color determined by a given record.
     */
    kanban_getcolor(value) {
        if (typeof value === "number") {
            return Math.round(value) % RECORD_COLORS.length;
        } else if (typeof value === "string") {
            const charCodeSum = [...value].reduce((acc, _, i) => acc + value.charCodeAt(i), 0);
            return charCodeSum % RECORD_COLORS.length;
        } else {
            return 0;
        }
    }

    /**
     * Returns the proper translated name of a record color.
     */
    kanban_getcolorname(value) {
        return RECORD_COLORS[this.kanban_getcolor(value)];
    }

    /**
     * Computes a given domain.
     */
    kanban_compute_domain(domain) {
        return new Domain(domain).compute(this.props.domain);
    }
}

KanbanRenderer.template = "web.KanbanRenderer";
KanbanRenderer.components = { Field, ViewButton };
