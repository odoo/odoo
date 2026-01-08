/** @odoo-module **/


const { onMounted, useEffect, useRef } = owl;

/**
 * Fit input size attribute to its content, respecting lower and upper limits.
 * Size limits and placeholder will be taken from
 *   1/ arguments passed to useFitContent
 *   2/ calling component props
 *   3/ Default values
 * In case the content is empty, use the placeholder length.
 */
export function useFitContent({ component, ...args }) {
    const listeners = [];
    const { minSize, maxSize, placeholder } = {
        minSize: 5,
        maxSize: 20,  // default input size
        ...component.props,
        ...args
    };
    const inputRef = useRef(args.refName);

    const resizeElement = function (inputElement) {
        const contentSize = inputElement.value.toString().length;
        let toSize;
        if (!contentSize) {
            toSize = placeholder ? placeholder.length() : minSize;
        } else {
            toSize = Math.max(minSize, Math.min(maxSize, contentSize));
        }
        inputElement.style.setProperty('width', (toSize + 1) + 'ch', 'important');
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
        () => [inputRef.el]
    );

    // Call resize for the first time + warn if wrong usage of options.
    onMounted(() => {
        if (!inputRef.el.parentElement.classList.contains('oe_inline')) {
            if (component.props.sizesDefined) {
                console.warn('Min/Max size options discarded for non-inline element');
            }
            return;
        }
        resizeElement(inputRef.el);
    });
}
