import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { useComponent } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { DynamicPlaceholderPopover } from "./dynamic_placeholder_popover";

export function useDynamicPlaceholder(elementRef) {
    const TRIGGER_KEY = "#";
    const ownerField = useComponent();
    const triggerKeyReplaceRegex = new RegExp(`${TRIGGER_KEY}$`);
    let closeCallback;
    let positionCallback;
    const popover = usePopover(DynamicPlaceholderPopover, {
        onClose: () => closeCallback?.(),
        onPositioned: (popper, position) => positionCallback?.(popper, position),
    });
    const notification = useService("notification");

    let model = null;

    const onDynamicPlaceholderValidate = function (path, defaultValue) {
        const element = elementRef?.el;
        if (!element) {
            return;
        }
        let rangeIndex = parseInt(element.getAttribute("data-oe-dynamic-placeholder-range-index"));
        // When the user cancel/close the popover, the path is empty.
        if (path) {
            defaultValue = defaultValue.replace("|||", "");
            const dynamicPlaceholder = ` {{object.${path}${
                defaultValue?.length ? ` ||| ${defaultValue}` : ""
            }}}`;
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
     * @param {Object} opts
     * @param {function} opts.validateCallback
     * @param {function} opts.closeCallback
     * @param {function} [opts.positionCallback]
     */
    async function open(opts) {
        if (!model) {
            return notification.add(
                _t("You need to select a model before opening the dynamic placeholder selector."),
                { type: "danger" }
            );
        }
        closeCallback = opts.closeCallback;
        positionCallback = opts.positionCallback;
        popover.open(elementRef?.el, {
            resModel: model,
            validate: opts.validateCallback,
        });
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
