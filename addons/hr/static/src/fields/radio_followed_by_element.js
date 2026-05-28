import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { RadioField, radioField } from "@web/views/fields/radio/radio_field";
import {onMounted, onPatched} from "@odoo/owl";
import { evaluateBooleanExpr } from "@web/core/py_js/py";

export class RadioFollowedByElement extends RadioField {
    static props = {
        ...RadioField.props,
        links: { type: Object },
        observe: { type: String },
        invisible_items: { type: Object, optional: true },
    };
    setup() {
        super.setup(...arguments);

        onPatched(() => {
            this.moveElement();
        });
        onMounted(() => {
            this.moveElement();
        });
    }

    moveElement() {
        for (const [key, value] of Object.entries(this.props.links)) {
            const escapedKey = CSS.escape(key);
            const option = document.querySelectorAll(`[data-value="${escapedKey}"]`)[0];
            const elementToAppend = document.getElementById(value);
            if (!option || !elementToAppend || elementToAppend.parentElement === option.parentElement)
                continue;
            option.parentElement.appendChild(elementToAppend);
        }
    }

    /**
     * @override
     */

    get items() {
        const allItems = super.items || [];
        const safeInvisibleItems = this.props.invisible_items || {};
        const validKeysSet = new Set(allItems.map(item => item?.[0]));
        const allKeysPresent = Object.keys(safeInvisibleItems).every(key => validKeysSet.has(key));
        if (!allKeysPresent) {
            throw new EvalError(`Some of the items provided  in invisible_items are not valid keys of the selection. Valid keys are: ${Array.from(validKeysSet).join(", ")}`);
        }
        let visibleItems = [];
        for (const item of allItems) {
            const itemKey = item[0];
            const invisibilityCondition = safeInvisibleItems[itemKey];
            if (invisibilityCondition) {
                const isInvisible = evaluateBooleanExpr(invisibilityCondition, this.props.record.evalContextWithVirtualIds);
                if (!isInvisible) {
                    visibleItems.push(item);
                }
            } else {
                visibleItems.push(item);
            }
        }
        return visibleItems;
    }
}

export const radioFollowedByElement = {
    ...radioField,
    component: RadioFollowedByElement,
    displayName: _t("Radio followed by element"),
    supportedOptions: [
        {
            label: _t("Element association"),
            name: "links",
            type: "Object",
            help: _t("An object to link select options and element id to move"),
        },
        {
            label: _t("Element to observe"),
            name: "observe",
            type: "String",
            help: _t("An element name parent of the radio to observe updates"),
        },
        {
            label: _t("Item to hide"),
            name: "invisible_items",
            type: "Object",
            help: _t("An object to ")
        }
    ],
    extractProps({ options }, dynamicInfo) {
        return {
            readonly: dynamicInfo.readonly,
            links: options.links,
            observe: options.observe,
            invisible_items: options.invisible_items,
        };
    },
};

registry.category("fields").add("radio_followed_by_element", radioFollowedByElement);
