import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import { useService } from "@web/core/utils/hooks";
import { FieldSelectorDialog } from "@web_studio/client_action/view_editor/editors/components/field_selector_dialog";
import { SidebarPropertiesToolbox } from "@web_studio/client_action/view_editor/interactive_editor/properties/sidebar_properties_toolbox/sidebar_properties_toolbox";

export class KanbanCoverProperties extends Component {
    static template = "web_studio.ViewEditor.InteractiveEditorProperties.KanbanCoverProperties";
    static props = {
        node: { type: Object },
    };
    static components = { Property, SidebarPropertiesToolbox };

    setup() {
        this.dialog = useService("dialog");
        // We don't want to display t in the sidebar.
        this.env.viewEditorModel.activeNode.humanName = _t("Dropdown");
    }

    get coverNode() {
        return this.env.viewEditorModel.xmlDoc.querySelector(
            "a[data-type='set_cover'],a[type='set_cover']"
        );
    }

    get coverValue() {
        return !!this.coverNode;
    }

    setCover(value, name) {
        const fields = [];

        for (const field of Object.values(this.env.viewEditorModel.fields)) {
            if (field.type === "many2one" && field.relation === "ir.attachment") {
                fields.push(field);
            }
        }

        this.dialog.add(FieldSelectorDialog, {
            fields: fields,
            showNew: true,
            onConfirm: (field) => {
                const operation = {
                    type: "kanban_set_cover",
                    field: field,
                };
                this.env.viewEditorModel.doOperation(operation);
            },
        });
    }

    onChangeCover(value, name) {
        if (!value) {
            const vem = this.env.viewEditorModel;
            const fieldToRemove = Object.entries(vem.controllerProps.archInfo.fieldNodes).filter(
                ([fName, fInfo]) => {
                    return fInfo.widget === "attachment_image";
                }
            );
            if (fieldToRemove.length !== 1) {
                return;
            }

            const extraNode = this.coverNode;
            const relevantAttr = ["type", "data-type"].filter((att) => {
                return extraNode.hasAttribute(att) && extraNode.getAttribute(att) === "set_cover";
            })[0];
            const operation = {
                target: {
                    attrs: { name: fieldToRemove[0][1].name },
                    tag: "field",
                    extra_nodes: [
                        {
                            tag: extraNode.tagName,
                            attrs: {
                                [relevantAttr]: "set_cover",
                            },
                        },
                    ],
                },
                type: "remove",
            };
            vem.doOperation(operation);
        } else {
            this.setCover(value, name);
        }
    }
}
