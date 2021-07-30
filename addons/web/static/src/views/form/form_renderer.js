/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { useService } from "@web/core/service_hook";
import { evaluateExpr } from "@web/core/py_js/py";

import { FormCompiler } from "@web/views/form/form_compiler";
import { Field } from "@web/fields/field";
import { ButtonBox } from "./button_box/button_box";
import { ViewButton } from "@web/views/view_button/view_button";

const { Component } = owl;
const { useSubEnv, useState } = owl.hooks;

const templateIds = Object.create(null);
let nextId = 1;

export class FormRenderer extends Component {
    static template = owl.tags.xml`<t t-call="{{ owlifiedArch }}" />`;

    setup() {
        let templateId = templateIds[this.props.info.arch];
        if (!templateId) {
            const formCompiler = new FormCompiler(this.env.qweb, this.props.info.fields);
            const xmldoc = formCompiler.compile(this.props.info.xmlDoc);
            console.group("Compiled template:");
            console.dirxml(xmldoc);
            console.groupEnd();
            templateId = `__form__${nextId++}`;
            this.env.qweb.addTemplate(templateId, xmldoc.outerHTML);
            templateIds[this.props.info.arch] = templateId;
        }
        this.owlifiedArch = templateId;
        this.state = useState({});
        useSubEnv({ model: this.props.model });
        this.action = useService("action");
    }

    get record() {
        return this.props.model.root;
    }

    evalDomain(record, expr) {
        const domain = new Domain(expr);
        return domain.contains(record.data);
    }

    getActivePage(invisibleDomains) {
        for (const page in invisibleDomains) {
            if (!invisibleDomains[page] || !this.evalDomain(invisibleDomains[page])) {
                return page;
            }
        }
    }

    async buttonClicked(params) {
        const { resModel, resId, resIds } = this.props.model;

        const valuesForEval = Object.assign({}, this.record.data, {
            active_id: resId,
            active_ids: resIds,
        });
        const buttonContext = evaluateExpr(params.context, valuesForEval);
        const envContext = null; //LPE FIXME record.context ?? new Context(payload.env.context).eval();

        const doActionParams = Object.assign({}, params, {
            resModel,
            resId,
            resIds,
            context: envContext,
            buttonContext,
            onclose: () => this.props.model.load(),
        });

        // LPE TODO: disable all buttons
        this.action.doActionButton(doActionParams);
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
}

FormRenderer.components = { Field, ButtonBox, ViewButton };
