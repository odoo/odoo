/** @odoo-module **/


const { onMounted, useEffect } = owl;

/**
 * Fit input size attribute to its content, respecting lower and upper limits.
 * In case the content is empty, use the placeholder length.
 */
export function useFitContent({ component }) {
    const listeners = [];
    const { minSize, maxSize, placeholder } = {
        minSize: 5,
        maxSize: 80,
        ...component.props
    };

    const resizeElement = function (inputElement) {
        const contentSize = inputElement.value.toString().length;
        let toSize;
        if (!contentSize) {
            toSize = placeholder ? placeholder.length() : minSize;
        } else {
            toSize = Math.max(minSize, Math.min(maxSize, contentSize - 1));
        }
        inputElement.setAttribute('size', toSize);
    };

    const onInputHandler = (ev) => {
        resizeElement(ev.target);
    };

    // As we cannot know the parents' classes at this point, we have to add
    // the effect even if it won't do anything later on
    useEffect(
        (el) => {
            if (el) {
                const inputs = el.nodeName === "INPUT" ? [el] : el.querySelectorAll("input");
                inputs.forEach((input) => {
                    if (input.parentElement.classList.contains('oe_inline')) {
                        listeners.push(input);
                        input.addEventListener("input", onInputHandler);
                    }
                });
            }
            return () => {
                listeners.forEach((input) => input.removeEventListener("input", onInputHandler));
            };
        },
        () => [component.inputRef.el]
    );

    // Call resize for the first time + warn if wrong usage of options.
    onMounted(() => {
        if (!component.inputRef.el.parentElement.classList.contains('oe_inline')) {
            if (component.props.sizesDefined) {
                console.warn('Min/Max size options discarded for non-inline element');
            }
            return;
        }
        resizeElement(component.inputRef.el);
    });
}
