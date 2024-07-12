import { _t } from "@web/core/l10n/translation";
import { Plugin } from "@html_editor/plugin";
import { Component, xml } from "@odoo/owl";
import { DynamicPlaceholderPopover } from "@web/views/fields/dynamic_placeholder_popover";

class EditorDynamicPlaceholder extends Component {
    static template = xml`<div class="popover" t-on-pointerdown.stop="() => {}">
            <DynamicPlaceholderPopover t-props="props"/>
        </div>`;
    static components = { DynamicPlaceholderPopover };
    static props = {
        close: Function,
        validate: Function,
        resModel: String,
    };
}

export class DynamicPlaceholderPlugin extends Plugin {
    static name = "dynamic_placeholder";
    static dependencies = ["overlay", "selection", "history", "dom", "qweb"];
    static shared = ["updateDphDefaultModel"];
    /** @type { (p: DynamicPlaceholderPlugin) => Record<string, any> } */
    static resources = (p) => ({
        powerboxCategory: { id: "marketing_tools", name: _t("Marketing Tools"), sequence: 60 },
        powerboxCommands: {
            name: _t("Dynamic Placeholder"),
            description: _t("Insert personalized content"),
            category: "marketing_tools",
            fontawesome: "fa-magic",
            action(dispatch) {
                dispatch("OPEN_DYNAMIC_PLACEHOLDER");
            },
        },
    });
    setup() {
        this.defaultResModel = this.config.dynamicPlaceholderResModel;

        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.overlay = this.shared.createOverlay(EditorDynamicPlaceholder, {
            position: "bottom-start",
        });

        this.addDomListener(this.document, "pointerdown", (e) => {
            if (this.overlay.isOpen) {
                this.overlay.close();
            }
        });
    }

    handleCommand(command, payload) {
        switch (command) {
            case "OPEN_DYNAMIC_PLACEHOLDER": {
                this.open(payload.resModel || this.defaultResModel);
                break;
            }
        }
    }

    /**
     * @param {string} resModel
     */
    updateDphDefaultModel(resModel) {
        this.defaultResModel = resModel;
    }

    /**
     * @param {string} resModel
     */
    open(resModel) {
        if (!resModel) {
            return this.services.notification.add(
                _t("You need to select a model before opening the dynamic placeholder selector."),
                { type: "danger" }
            );
        }
        this.preservedSelection = this.shared.preserveSelection();
        this.overlay.open({
            props: {
                close: this.onClose.bind(this),
                validate: this.onValidate.bind(this),
                resModel: resModel,
            },
        });
    }

    /**
     * @param {string} chain
     * @param {string} defaultValue
     */
    onValidate(chain, defaultValue) {
        if (!chain) {
            return;
        }

        let dynamicPlaceholder = "object." + chain;
        dynamicPlaceholder +=
            defaultValue && defaultValue !== "" ? ` or '''${defaultValue}'''` : "";
        const t = document.createElement("T");
        t.setAttribute("t-out", dynamicPlaceholder);

        this.shared.domInsert(t);
        this.editable.focus();
        this.dispatch("ADD_STEP");
    }
    onClose() {
        this.preservedSelection?.restore();
        delete this.preservedSelection;

        this.overlay.close();
    }
}
