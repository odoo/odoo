import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { DynamicPlaceholderPopover } from "@web/views/fields/dynamic_placeholder_popover";
import { withSequence } from "@html_editor/utils/resource";

export class DynamicPlaceholderPlugin extends Plugin {
    static name = "dynamic_placeholder";
    static dependencies = ["overlay", "selection", "history", "dom", "qweb"];
    static shared = ["updateDphDefaultModel"];
    resources = {
        powerboxCategory: withSequence(60, { id: "marketing_tools", name: _t("Marketing Tools") }),
        powerboxItems: {
            id: "dynamic_placeholder",
            name: _t("Dynamic Placeholder"),
            description: _t("Insert a field"),
            category: "marketing_tools",
            fontawesome: "fa-hashtag",
            action(dispatch) {
                dispatch("OPEN_DYNAMIC_PLACEHOLDER");
            },
        },
        powerButtons: ["dynamic_placeholder"],
    };
    setup() {
        this.defaultResModel = this.config.dynamicPlaceholderResModel;

        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.overlay = this.shared.createOverlay(DynamicPlaceholderPopover, {
            hasAutofocus: true,
            className: "popover",
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

        const t = document.createElement("T");
        t.setAttribute("t-out", `object.${chain}`);
        if (defaultValue?.length) {
            t.innerText = defaultValue;
        }

        this.shared.domInsert(t);
        this.dispatch("ADD_STEP");
    }

    onClose() {
        this.overlay.close();
        this.shared.focusEditable();
    }
}
