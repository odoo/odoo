/** @odoo-module **/

import { useUniquePopover } from "@web/core/model_field_selector/unique_popover_hook";
import { useModelField } from "@web/core/model_field_selector/model_field_hook";
import { ModelFieldSelectorPopover } from "@web/core/model_field_selector/model_field_selector_popover";

export function useDynamicPlaceholder() {
    const popover = useUniquePopover();
    const modelField = useModelField();

    let dynamicPlaceholderChain = [];

    function update(chain) {
        dynamicPlaceholderChain = chain;
    }

    return {
        TRIGGER_KEY: '#',
        /**
         * Open a Model Field Selector which can select fields to create a dynamic
         * placeholder string in the Input with or without a default text value.
         *
         * @public
         * @param {HTMLElement} element
         * @param {String} baseModel
         * @param {Object} options
         * @param {function} options.validateCallback
         * @param {function} options.closeCallback
         * @param {function} [options.positionCallback]
         */
         async open(
             element,
             baseModel,
             options = {}
        ) {
            dynamicPlaceholderChain = await modelField.loadChain(baseModel, "");

            popover.add(
                element,
                ModelFieldSelectorPopover,
                {
                    chain: dynamicPlaceholderChain,
                    update: update,
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
    };
}


