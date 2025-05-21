import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { DynamicPlaceholderPopover } from "@web/views/fields/dynamic_placeholder_popover";
import { withSequence } from "@html_editor/utils/resource";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

/**
 * @typedef {Object} DynamicPlaceholderShared
 * @property {DynamicPlaceholderPlugin['updateDphDefaultModel']} updateDphDefaultModel
 */

export class DynamicPlaceholderPlugin extends Plugin {
    static id = "dynamicPlaceholder";
    static dependencies = ["overlay", "selection", "history", "dom"];
    static shared = ["updateDphDefaultModel"];
    resources = {
        user_commands: [
            {
                id: "openDynamicPlaceholder",
                title: _t("Dynamic Placeholder"),
                description: _t("Insert a field"),
                icon: "fa-hashtag",
                run: (params = {}) => this.open(params.resModel || this.defaultResModel),
                isAvailable: isHtmlContentSupported,
            },
        ],
        powerbox_categories: withSequence(60, {
            id: "marketing_tools",
            name: _t("Marketing Tools"),
        }),
        powerbox_items: {
            categoryId: "marketing_tools",
            commandId: "openDynamicPlaceholder",
        },
        power_buttons: { commandId: "openDynamicPlaceholder" },
    };
    setup() {
        this.defaultResModel = this.config.dynamicPlaceholderResModel;

        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.overlay = this.dependencies.overlay.createOverlay(DynamicPlaceholderPopover, {
            hasAutofocus: true,
            className: "popover",
        });
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
     * @param {string} fieldType
     */
    async onValidate(chain, defaultValue, fieldType) {
        if (!chain) {
            return;
        }

        const dynamicPlaceholder =
            fieldType === "datetime"
                ? await this._onValidateDatetime(chain, defaultValue)
                : `object.${chain}`;

        const t = document.createElement("T");
        t.setAttribute("t-out", dynamicPlaceholder);
        if (defaultValue?.length) {
            t.innerText = defaultValue;
        }

        this.dependencies.dom.insert(t);
        this.dependencies.history.addStep();
    }

    async _onValidateDatetime(chain, defaultValue) {
        const partnerFields = await this.services.orm.call(
            `${this.defaultResModel}`,
            "mail_get_partner_fields",
            [[]]
        );

        let dynamicPlaceholder = partnerFields.length
            ? `format_datetime(object.${chain}, tz=object.${partnerFields[0]}.tz)`
            : `format_datetime(object.${chain})`;

        if (defaultValue) {
            const safeDefaultValue = defaultValue.replace(/'/g, "\\'");
            dynamicPlaceholder += ` or '${safeDefaultValue}'`;
        }

        return dynamicPlaceholder;
    }

    onClose() {
        this.overlay.close();
        this.dependencies.selection.focusEditable();
    }
}
