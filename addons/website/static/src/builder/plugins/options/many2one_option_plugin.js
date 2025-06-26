import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { Many2OneOption } from "./many2one_option";
import { BuilderAction } from "@html_builder/core/builder_action";

export class Many2OneOptionPlugin extends Plugin {
    static id = "many2OneOption";
    resources = {
        builder_options: [
            {
                OptionComponent: Many2OneOption,
                selector: "[data-oe-many2one-model]:not([data-oe-readonly])",
                editableOnly: false,
            },
        ],
        builder_actions: {
            Many2OneAction,
        },
    };
}

export class Many2OneAction extends BuilderAction {
    static id = "many2One";
    async load({ editingElement, value }) {
        const { id } = JSON.parse(value);
        const { oeModel, oeId, oeField } = editingElement.dataset;
        const allContactOptions = new Set(
            this.editable
                .querySelectorAll(
                    `[data-oe-model="${oeModel}"][data-oe-id="${oeId}"][data-oe-field="${oeField}"][data-oe-type="contact"]`
                )
                .values()
                .map((el) => el.dataset.oeContactOptions)
        );
        return Object.fromEntries(
            await Promise.all(
                allContactOptions
                    .values()
                    .map(async (contactOptions) => [
                        contactOptions,
                        await this.services.orm.call(
                            "ir.qweb.field.contact",
                            "get_record_to_html",
                            [[id]],
                            { options: JSON.parse(contactOptions) }
                        ),
                    ])
            )
        );
    }
    apply({ editingElement, value, loadResult }) {
        const { id, name } = JSON.parse(value);
        const { oeModel, oeId, oeField, oeContactOptions } = editingElement.dataset;

        for (const el of [
            ...this.editable.querySelectorAll(
                `[data-oe-model="${oeModel}"][data-oe-id="${oeId}"][data-oe-field="${oeField}"]:not([data-oe-contact-options='${oeContactOptions}'])`
            ),
            editingElement,
        ]) {
            el.dataset.oeMany2oneId = id;
            if (el.dataset.oeType === "contact") {
                el.replaceChildren(
                    ...new DOMParser().parseFromString(
                        loadResult[el.dataset.oeContactOptions],
                        "text/html"
                    ).body.childNodes
                );
            } else {
                el.textContent = name;
            }
        }
    }
    getValue({ editingElement }) {
        return JSON.stringify({ id: parseInt(editingElement.dataset.oeMany2oneId) });
    }
}

registry.category("website-plugins").add(Many2OneOptionPlugin.id, Many2OneOptionPlugin);
