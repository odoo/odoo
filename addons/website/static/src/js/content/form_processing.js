/** @odoo-module */

// Contains the modifiers used to adapt the input label position.
const _formLabelPositionConfig = {
    hide: (options) => {
        resetWebsiteLabel(options);
        options.labelEl.classList.add("d-none");
        cleanWebsiteLabel(options);
    },
    top: (options) => {
        resetWebsiteLabel(options);
        cleanWebsiteLabel(options);
    },
    left: (options) => {
        resetWebsiteLabel(options);
        inlineWebsiteLabel(options);
        cleanWebsiteLabel(options);
    },
    right: (options) => {
        resetWebsiteLabel(options);
        inlineWebsiteLabel(options);
        options.labelEl.classList.add("text-end");
        cleanWebsiteLabel(options);
    },
    floating: (options) => {
        const setFloatingLabel = options.websiteFormField
            ? canSetFloatingLabel(options.websiteFormField.dataset.type)
            : options.contentEls[0].matches("input, select, textarea");
        if (!setFloatingLabel) {
            return;
        }
        resetWebsiteLabel(options);
        if (!options.contentEls[0].hasAttribute("placeholder")) {
            options.contentEls[0].setAttribute("placeholder", "");
        }
        const containerEl = document.createElement("div");
        containerEl.className = "form-floating";
        options.labelEl.before(containerEl);
        containerEl.append(
            ...[
                options.contentEls[0],
                options.labelEl,
                ...(options.descriptionEl ? [options.descriptionEl] : []),
            ]
        );
        cleanWebsiteLabel(options);
    },
};

/**
 * Check if a "floating label" design can be applied on a website form field.
 *
 * @param {String} type
 * @returns {Boolean}
 */
export function canSetFloatingLabel(type) {
    return !["boolean", "one2many", "selection", "date", "datetime", "binary"].includes(type);
}

/**
 * Check if a label can be added after the input in a form field.
 *
 * @param {String} type
 * @returns {Boolean}
 */
export function canSetLabelAfterCheckbox(type) {
    return type === "boolean";
}

/**
 * Check if we can set a default label width.
 *
 * @param {String} position The current label position.
 * @returns {Boolean}
 */
function canSetLabelWidth(position) {
    return ["left", "right"].includes(position);
}

/**
 * Returns a field content except label & description (single input, input
 * group, radio, etc.)
 *
 * @param {Object} options
 * @returns {HTMLElement[]}
 */
export function getInputContent(options) {
    switch (options.oldPosition) {
        case "left":
        case "right":
            return [
                ...options.websiteFormField.querySelectorAll(
                    ".col-sm > :not(.s_website_form_field_description)"
                ),
            ];
        default:
            return [
                ...options.websiteFormField.querySelectorAll(
                    ":scope > :not(label, .s_website_form_field_description)"
                ),
            ];
    }
}

/**
 * Returns the current position of an input label element.
 *
 * @param {HTMLElement} labelEl
 * @returns {String}
 */
export function getWebsiteLabelPosition(labelEl) {
    if (!labelEl) {
        return "";
    }
    const labelClassList = labelEl.classList;
    if (labelClassList.contains("col-sm-auto")) {
        return labelClassList.contains("text-end") ? "right" : "left";
    } else if (labelEl.previousElementSibling?.matches(".form-check > input[type='checkbox']")) {
        return "after-checkbox";
    } else if (labelEl.closest(".form-floating")) {
        return "floating";
    } else {
        return labelClassList.contains("d-none") ? "none" : "top";
    }
}

/**
 * Removes elements wrapping a form input / label (mainly used for "inline" &
 * "floating" positions) to be able to apply the new position correctly.
 *
 * @param {Object} options
 */
function resetWebsiteLabel(options) {
    if (options.websiteFormField) {
        for (const wrapEl of options.websiteFormField.querySelectorAll(
            ":scope > .row:not(.s_website_form_multiple), .col-sm, :scope > .form-floating, :scope > .form-check"
        )) {
            wrapEl.after(...wrapEl.childNodes);
            wrapEl.remove();
        }
        // Ensure that the label is before the input content.
        options.labelEl.parentElement.insertBefore(options.labelEl, ...options.contentEls);
    }
}

/**
 * Cleans the DOM and removes unwanted CSS from the old design.
 *
 * @param {Object} options
 */
function cleanWebsiteLabel(options) {
    const classesToRemove = [
        ...(!["right", "left"].includes(options.newPosition) ? ["col-sm-auto"] : []),
        ...(options.oldPosition === "right" ? ["text-end"] : []),
        ...(options.oldPosition === "hide" ? ["d-none"] : []),
    ];
    options.labelEl.classList.remove(...classesToRemove);
}

/**
 * Used to apply an inline label position (left or right).
 *
 * @param {Object} options
 */
function inlineWebsiteLabel(options) {
    const rowEl = document.createElement("div");
    rowEl.className = "row s_col_no_resize s_col_no_bgcolor";
    const colEl = document.createElement("div");
    colEl.className = "col-sm";
    options.labelEl.classList.add("col-sm-auto");
    colEl.append(
        ...[...options.contentEls, ...(options.descriptionEl ? [options.descriptionEl] : [])]
    );
    options.labelEl.before(rowEl);
    rowEl.append(options.labelEl, colEl);
}

/**
 * Applies the default label width.
 *
 * @param {Object} options
 */
function adaptLabelWidth(options) {
    if (options.width && options.labelEl) {
        options.labelEl.style.width = canSetLabelWidth(options.position) ? options.width : "";
    }
}

/**
 * Applies the provided label width and position design to a form (for every
 * field that supports it).
 *
 * @param {HTMLElement} formEl
 * @param {String} newPosition
 * @param {String} width
 */
export function adaptFormLabel(formEl, newPosition, width) {
    for (const inputEl of formEl.querySelectorAll(
        ".form-control:not([type=hidden]), .form-select:not([type=hidden]), .form-check-input"
    )) {
        const websiteFormField = inputEl.closest(".s_website_form_field");
        const labelEl = (websiteFormField || inputEl.parentElement).querySelector("label");
        const descriptionEl = websiteFormField?.querySelector(".s_website_form_field_description");
        const oldPosition = getWebsiteLabelPosition(labelEl);
        if (websiteFormField?.classList.contains("o_custom_label_position")) {
            adaptLabelWidth({ position: oldPosition, labelEl, width });
            continue;
        }
        if (oldPosition && oldPosition !== newPosition) {
            _formLabelPositionConfig[newPosition]({
                websiteFormField,
                oldPosition,
                newPosition,
                descriptionEl,
                contentEls: websiteFormField
                    ? getInputContent({ websiteFormField, oldPosition, inputEl })
                    : [inputEl],
                labelEl,
            });
        }
        adaptLabelWidth({ position: newPosition, labelEl, width });
    }
}

/**
 * Set the default label position and width on all forms on a page (website and
 * bootstrap forms):
 * The label position can always be customized in the website editor (for every
 * label element).
 * The label width can also be edited (on a form level) since it's a form option
 */
document.addEventListener("DOMContentLoaded", () => {
    const style = window.getComputedStyle(document.documentElement);
    const defaultLabelPosition = style.getPropertyValue("--input-label-position").replace(/'/g, "");
    const defaultLabelWidth = style.getPropertyValue("--input-label-width");

    if (defaultLabelPosition) {
        for (const formEl of document.querySelectorAll(
            `main form:not(.o_custom_label_position, .o_custom_label_position_${defaultLabelPosition})`
        )) {
            adaptFormLabel(
                formEl,
                defaultLabelPosition,
                !formEl.closest(".o_custom_label_width") && defaultLabelWidth
            );
        }
    }
});
