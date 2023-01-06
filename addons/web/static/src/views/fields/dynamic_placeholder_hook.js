/** @odoo-module **/

import { useUniquePopover } from "@web/core/model_field_selector/unique_popover_hook";
import { useModelField } from "@web/core/model_field_selector/model_field_hook";
import { useService } from "@web/core/utils/hooks";
import { ModelFieldSelectorPopover } from "@web/core/model_field_selector/model_field_selector_popover";
import { useComponent } from "@odoo/owl";

export function useDynamicPlaceholder(elementRef) {
    const TRIGGER_KEY = "#";
    const ownerField = useComponent();
    const triggerKeyReplaceRegex = new RegExp(`${TRIGGER_KEY}$`);
    const popover = useUniquePopover();
    const modelField = useModelField();
    const notification = useService("notification");

    let model = null;
    let dynamicPlaceholderChain = [];

    const onDynamicPlaceholderValidate = function (chain, defaultValue) {
        const element = elementRef?.el;
        if (!element) {
            return;
        }
        let rangeIndex = parseInt(element.getAttribute("data-oe-dynamic-placeholder-range-index"));
        // When the user cancel/close the popover, the chain is empty.
        if (chain) {
            let dynamicPlaceholder = "{{object." + chain.join(".");
            dynamicPlaceholder +=
                defaultValue && defaultValue !== "" ? ` or '''${defaultValue}'''}}` : "}}";

            const baseValue = element.value;
            const splitedValue = [baseValue.slice(0, rangeIndex), baseValue.slice(rangeIndex)];
            const newValue =
                splitedValue[0].replace(triggerKeyReplaceRegex, "") +
                dynamicPlaceholder +
                splitedValue[1];
            const changes = { [ownerField.props.name]: newValue };
            ownerField.props.record.update(changes);
            element.value = newValue;

            // -1 to take the removal of the trigger key char into account
            rangeIndex += dynamicPlaceholder.length - 1;
            element.setSelectionRange(rangeIndex, rangeIndex);
            element.removeAttribute("data-oe-dynamic-placeholder-range-index");
        }
    };
    const onDynamicPlaceholderClose = function () {
        elementRef?.el.focus();
    };

    /**
     * Open a Model Field Selector which can select fields to create a dynamic
     * placeholder string in the Input with or without a default text value.
     *
     * @public
     * @param {Object} options
     * @param {function} options.validateCallback
     * @param {function} options.closeCallback
     * @param {function} [options.positionCallback]
     */
    async function open(options) {
        if (!model) {
            return notification.add(
                ownerField.env._t(
                    "You need to select a model before opening the dynamic placeholder selector."
                ),
                { type: "danger" }
            );
        }

        dynamicPlaceholderChain = await modelField.loadChain(model, "");
        popover.add(
            elementRef?.el,
            ModelFieldSelectorPopover,
            {
                chain: dynamicPlaceholderChain,
                update: (chain) => { dynamicPlaceholderChain = chain; },
                validate: options.validateCallback,
                showSearchInput: true,
                isDebugMode: true,
                needDefaultValue: true,
                loadChain: modelField.loadChain,
                filter: (model) => !["one2many", "boolean", "many2many"].includes(model.type),
            },
            {
                closeOnClickAway: true,
                onClose: options.closeCallback,
                onPositioned: options.positionCallback,
            }
        );
    }
    async function onKeydown(ev) {
        const element = elementRef?.el;
        if (ev.target === element && ev.key === TRIGGER_KEY) {
            const currentRangeIndex = element.selectionStart;
            // +1 to take the trigger key char into account
            element.setAttribute("data-oe-dynamic-placeholder-range-index", currentRangeIndex + 1);
            await open({
                validateCallback: onDynamicPlaceholderValidate,
                closeCallback: onDynamicPlaceholderClose,
            });
        }
    }
    function updateModel(model_name_location) {
        const recordData = ownerField.props.record.data;
        model = recordData[model_name_location] || recordData.model;
    }

    return {
        updateModel: updateModel,
        onKeydown: onKeydown,
        setElementRef: (er) => (elementRef = er),
        open: open,
    };
}
