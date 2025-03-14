import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { generateHTMLId } from "@html_builder/utils/utils_css";

/**
 * Returns the parsed data coming from the data-for element for the given form.
 * TODO Note that we should rely on the same util as the website form interaction.
 * Maybe this will need to be deleted.
 *
 * @param {string} formId
 * @param {HTMLElement} parentEl
 * @returns {Object|undefined} the parsed data
 */
export function getParsedDataFor(formId, parentEl) {
    const dataForEl = parentEl.querySelector(`[data-for='${formId}']`);
    if (!dataForEl) {
        return;
    }
    return JSON.parse(
        dataForEl.dataset.values
            // replaces `True` by `true` if they are after `,` or `:` or `[`
            .replace(/([,:[]\s*)True/g, "$1true")
            // replaces `False` and `None` by `""` if they are after `,` or `:` or `[`
            .replace(/([,:[]\s*)(False|None)/g, '$1""')
            // replaces the `'` by `"` if they are before `,` or `:` or `]` or `}`
            .replace(/'(\s*[,:\]}])/g, '"$1')
            // replaces the `'` by `"` if they are after `{` or `[` or `,` or `:`
            .replace(/([{[:,]\s*)'/g, '$1"')
    );
}

/**
 * Returns a field object
 *
 * @param {string} type the type of the field
 * @param {string} name The name of the field used also as label
 * @returns {Object}
 */
export function getCustomField(type, name) {
    return {
        name: name,
        string: name,
        custom: true,
        type: type,
        // Default values for x2many fields and selection
        records: [
            {
                id: _t("Option 1"),
                display_name: _t("Option 1"),
            },
            {
                id: _t("Option 2"),
                display_name: _t("Option 2"),
            },
            {
                id: _t("Option 3"),
                display_name: _t("Option 3"),
            },
        ],
    };
}

export const getMark = (el) => el.dataset.mark;
export const isOptionalMark = (el) => el.classList.contains("o_mark_optional");
export const isRequiredMark = (el) => el.classList.contains("o_mark_required");
/**
 * Returns the default formatInfos of a field.
 *
 * @param {HTMLElement} el
 * @returns {Object}
 */
export function getDefaultFormat(el) {
    return {
        labelWidth: el.querySelector(".s_website_form_label").style.width,
        labelPosition: "left",
        multiPosition: "horizontal",
        requiredMark: isRequiredMark(el),
        optionalMark: isOptionalMark(el),
        mark: getMark(el),
    };
}

/**
 * Replace all `"` character by `&quot;`.
 *
 * @param {string} name
 * @returns {string}
 */
export function getQuotesEncodedName(name) {
    // Browsers seem to be encoding the double quotation mark character as
    // `%22` (URI encoded version) when used inside an input's name. It is
    // actually quite weird as a sent `<input name='Hello "world" %22'/>`
    // will actually be received as `Hello %22world%22 %22` on the server,
    // making it impossible to know which is actually a real double
    // quotation mark and not the "%22" string. Values do not have this
    // problem: `Hello "world" %22` would be received as-is on the server.
    // In the future, we should consider not using label values as input
    // names anyway; the idea was bad in the first place. We should probably
    // assign random field names (as we do for IDs) and send a mapping
    // with the labels, as values (TODO ?).
    return name.replaceAll(/"/g, (character) => `&quot;`);
}

/**
 * Renders a field of the form based on its description
 *
 * @param {Object} field
 * @returns {HTMLElement}
 */
export function renderField(field, resetId = false) {
    if (!field.id) {
        field.id = generateHTMLId();
    }
    const params = { field: { ...field } };
    if (["url", "email", "tel"].includes(field.type)) {
        params.field.inputType = field.type;
    }
    if (["boolean", "selection", "binary"].includes(field.type)) {
        params.field.isCheck = true;
    }
    if (field.type === "one2many" && field.relation !== "ir.attachment") {
        params.field.isCheck = true;
    }
    if (field.custom && !field.string) {
        params.field.string = field.name;
    }
    if (field.description) {
        params.default_description = _t("Describe your field here.");
    } else if (["email_cc", "email_to"].includes(field.name)) {
        params.default_description = _t("Separate email addresses with a comma.");
    }
    const template = document.createElement("template");
    const renderType = field.type === "tags" ? "many2many" : field.type;
    template.content.append(renderToElement("website.form_field_" + renderType, params));
    if (field.description && field.description !== true) {
        $(template.content.querySelector(".s_website_form_field_description")).replaceWith(
            field.description
        );
    }
    template.content
        .querySelectorAll("input.datetimepicker-input")
        .forEach((el) => (el.value = field.propertyValue));
    template.content.querySelectorAll("[name]").forEach((el) => {
        el.name = getQuotesEncodedName(el.name);
    });
    template.content.querySelectorAll("[data-name]").forEach((el) => {
        el.dataset.name = getQuotesEncodedName(el.dataset.name);
    });
    return template.content.firstElementChild;
}

/**
 * Returns true if the field is required by the model or by the user.
 *
 * @param {HTMLElement} fieldEl
 * @returns {boolean}
 */
export function isFieldRequired(fieldEl) {
    const classList = fieldEl.classList;
    return (
        classList.contains("s_website_form_required") ||
        classList.contains("s_website_form_model_required")
    );
}

/**
 * Returns the multiple checkbox/radio element if it exist else null
 *
 * @param {HTMLElement} fieldEl
 * @returns {HTMLElement}
 */
export function getMultipleInputs(fieldEl) {
    return fieldEl.querySelector(".s_website_form_multiple");
}

export function getLabelPosition(fieldEl) {
    const label = fieldEl.querySelector(".s_website_form_label");
    if (fieldEl.querySelector(".row:not(.s_website_form_multiple)")) {
        return label.classList.contains("text-end") ? "right" : "left";
    } else {
        return label.classList.contains("d-none") ? "none" : "top";
    }
}

/**
 * Returns the format object of a field containing
 * the position, labelWidth and bootstrap col class
 *
 * @param {HTMLElement} fieldEl
 * @returns {Object}
 */
export function getFieldFormat(fieldEl) {
    let requiredMark, optionalMark;
    const mark = fieldEl.querySelector(".s_website_form_mark");
    if (mark) {
        requiredMark = isFieldRequired(fieldEl);
        optionalMark = !requiredMark;
    }
    const multipleInputEl = getMultipleInputs(fieldEl);
    const format = {
        labelPosition: getLabelPosition(fieldEl),
        labelWidth: fieldEl.querySelector(".s_website_form_label").style.width,
        multiPosition: (multipleInputEl && multipleInputEl.dataset.display) || "horizontal",
        col: [...fieldEl.classList].filter((el) => el.match(/^col-/g)).join(" "),
        requiredMark: requiredMark,
        optionalMark: optionalMark,
        mark: mark && mark.textContent,
    };
    return format;
}
