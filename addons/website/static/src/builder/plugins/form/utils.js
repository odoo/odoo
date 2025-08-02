import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { generateHTMLId } from "@html_builder/utils/utils_css";

export const VISIBILITY_DATASET = [
    "visibilityDependency",
    "visibilityCondition",
    "visibilityComparator",
    "visibilityBetween",
];

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
 * @param {string} label The label of the field. Also used as the field's
 *                       name if no `name` is provided.
 * @param {string} [name] The name of the field. Falls back to `label` if
 *                        not specified
 * @returns {Object}
 */
export function getCustomField(type, label, name = "") {
    return {
        name: name || label,
        string: label,
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
        const descriptionEl = template.content.querySelector(".s_website_form_field_description");
        descriptionEl.replaceWith(field.description);
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

/**
 * Returns true if the field is a custom field, false if it is an existing field
 *
 * @param {HTMLElement} fieldEl
 * @returns {boolean}
 */
export function isFieldCustom(fieldEl) {
    return !!fieldEl.classList.contains("s_website_form_custom");
}

/**
 * Returns the name of the field
 *
 * @param {HTMLElement} fieldEl
 * @returns {string}
 */
export function getFieldName(fieldEl = this.$target[0]) {
    const multipleName = fieldEl.querySelector(".s_website_form_multiple");
    return multipleName
        ? multipleName.dataset.name
        : fieldEl.querySelector(".s_website_form_input").name;
}
/**
 * Returns the type of the  field, can be used for both custom and existing fields
 *
 * @param {HTMLElement} fieldEl
 * @returns {string}
 */
export function getFieldType(fieldEl) {
    return fieldEl.dataset.type;
}

/**
 * Set the active field properties on the field Object
 *
 * @param {HTMLElement} fieldEl
 * @param {Object} field Field to complete with the active field info
 */
export function setActiveProperties(fieldEl, field) {
    const classList = fieldEl.classList;
    const textarea = fieldEl.querySelector("textarea");
    const input = fieldEl.querySelector(
        'input[type="text"], input[type="email"], input[type="number"], input[type="tel"], input[type="url"], textarea'
    );
    const fileInputEl = fieldEl.querySelector("input[type=file]");
    const description = fieldEl.querySelector(".s_website_form_field_description");
    field.placeholder = input && input.placeholder;
    if (input) {
        // textarea value has no attribute,  date/datetime timestamp property is formated
        field.value = input.getAttribute("value") || input.value;
    } else if (field.type === "boolean") {
        field.value = !!fieldEl.querySelector('input[type="checkbox"][checked]');
    } else if (fileInputEl) {
        field.maxFilesNumber = fileInputEl.dataset.maxFilesNumber;
        field.maxFileSize = fileInputEl.dataset.maxFileSize;
    }
    // property value is needed for date/datetime (formated date).
    field.propertyValue = input && input.value;
    field.description = description;
    field.rows = textarea && textarea.rows;
    field.required = classList.contains("s_website_form_required");
    field.modelRequired = classList.contains("s_website_form_model_required");
    field.hidden = classList.contains("s_website_form_field_hidden");
    field.formatInfo = getFieldFormat(fieldEl);
}

/**
 * Replaces the target with provided field.
 *
 * @param {HTMLElement} oldFieldEl
 * @param {HTMLElement} fieldEl
 */
export function replaceFieldElement(oldFieldEl, fieldEl) {
    const inputEl = oldFieldEl.querySelector("input");
    const dataFillWith = inputEl ? inputEl.dataset.fillWith : undefined;
    const hasConditionalVisibility = oldFieldEl.classList.contains(
        "s_website_form_field_hidden_if"
    );
    const previousInputEl = oldFieldEl.querySelector(".s_website_form_input");
    const previousName = previousInputEl.name;
    const previousType = previousInputEl.type;
    [...oldFieldEl.childNodes].forEach((node) => node.remove());
    [...fieldEl.childNodes].forEach((node) => oldFieldEl.appendChild(node));
    [...fieldEl.attributes].forEach((el) => oldFieldEl.removeAttribute(el.nodeName));
    [...fieldEl.attributes].forEach((el) => oldFieldEl.setAttribute(el.nodeName, el.nodeValue));
    if (hasConditionalVisibility) {
        oldFieldEl.classList.add("s_website_form_field_hidden_if", "d-none");
    }
    const dependentFieldEls = oldFieldEl
        .closest("form")
        .querySelectorAll(
            `.s_website_form_field[data-visibility-dependency="${CSS.escape(previousName)}"]`
        );
    const newFormInputEl = oldFieldEl.querySelector(".s_website_form_input");
    const newName = newFormInputEl.name;
    const newType = newFormInputEl.type;
    if ((previousName !== newName || previousType !== newType) && dependentFieldEls) {
        // In order to keep the visibility conditions consistent,
        // when the name has changed, it means that the type has changed so
        // all fields whose visibility depends on this field must be updated so that
        // they no longer have conditional visibility
        for (const fieldEl of dependentFieldEls) {
            deleteConditionalVisibility(fieldEl);
        }
    }
    const newInputEl = oldFieldEl.querySelector("input");
    if (newInputEl) {
        newInputEl.dataset.fillWith = dataFillWith;
    }
}

/**
 * Returns the target as a field Object
 *
 * @param {HTMLElement} fieldEl
 * @param {boolean} noRecords
 * @returns {Object}
 */
export function getActiveField(fieldEl, { noRecords, fields } = {}) {
    let field;
    const labelText = fieldEl.querySelector(".s_website_form_label_content")?.innerText || "";
    if (isFieldCustom(fieldEl)) {
        const inputName = fieldEl.querySelector(".s_website_form_input").getAttribute("name");
        field = getCustomField(fieldEl.dataset.type, labelText, inputName);
    } else {
        field = Object.assign({}, fields[getFieldName(fieldEl)]);
        field.string = labelText;
        field.type = getFieldType(fieldEl);
    }
    if (!noRecords) {
        field.records = getListItems(fieldEl);
    }
    setActiveProperties(fieldEl, field);
    return field;
}

/**
 * Deletes all attributes related to conditional visibility.
 *
 * @param {HTMLElement} fieldEl
 */
export function deleteConditionalVisibility(fieldEl) {
    for (const name of VISIBILITY_DATASET) {
        delete fieldEl.dataset[name];
    }
    fieldEl.classList.remove("s_website_form_field_hidden_if", "d-none");
}

/**
 * Returns the select element if it exist else null
 *
 * @param {HTMLElement} fieldEl
 * @returns {HTMLElement}
 */
export function getSelect(fieldEl) {
    return fieldEl.querySelector("select");
}

/**
 * Returns the next new record id.
 *
 * @param {HTMLElement} fieldEl
 */
export function getNewRecordId(fieldEl) {
    const selectEl = getSelect(fieldEl);
    const multipleInputsEl = getMultipleInputs(fieldEl);
    let options = [];
    if (selectEl) {
        options = [...selectEl.querySelectorAll("option")];
    } else if (multipleInputsEl) {
        options = [...multipleInputsEl.querySelectorAll(".checkbox input, .radio input")];
    }
    // TODO: @owl-option factorize code above
    const targetEl = fieldEl.querySelector(".s_website_form_input");
    let id;
    if (["checkbox", "radio"].includes(targetEl.getAttribute("type"))) {
        // Remove first checkbox/radio's id's final '0'.
        id = targetEl.id.slice(0, -1);
    } else {
        id = targetEl.id;
    }
    return id + options.length;
}

/**
 * @param {HTMLElement} fieldEl
 * @returns {HTMLElement} The visibility dependency of the field
 */
export function getDependencyEl(fieldEl) {
    const dependencyName = fieldEl.dataset.visibilityDependency;
    return fieldEl
        .closest("form")
        ?.querySelector(`.s_website_form_input[name="${CSS.escape(dependencyName)}"]`);
}

/**
 * @param {HTMLElement} fieldEl
 * @returns {HTMLElement} The current field input
 */
export function getCurrentFieldInputEl(fieldEl) {
    return fieldEl.querySelector(".s_website_form_input");
}

/**
 * @param {HTMLElement} dependentFieldEl
 * @param {HTMLElement} targetFieldEl
 * @returns {boolean} "true" if adding "dependentFieldEl" or any other field
 * with the same label in the conditional visibility of "targetFieldEl"
 * would create a circular dependency involving "targetFieldEl".
 */
export function findCircular(dependentFieldEl, targetFieldEl) {
    const formEl = targetFieldEl.closest("form");
    // Keep a register of the already visited fields to not enter an
    // infinite check loop.
    const visitedFields = new Set();
    const recursiveFindCircular = (dependentFieldEl, targetFieldEl) => {
        const dependentFieldName = getFieldName(dependentFieldEl);
        // Get all the fields that have the same label as the dependent
        // field.
        let dependentFieldEls = Array.from(
            formEl.querySelectorAll(
                `.s_website_form_input[name="${CSS.escape(dependentFieldName)}"]`
            )
        ).map((el) => el.closest(".s_website_form_field"));
        // Remove the duplicated fields. This could happen if the field has
        // multiple inputs ("Multiple Checkboxes" for example.)
        dependentFieldEls = new Set(dependentFieldEls);
        const fieldName = getFieldName(targetFieldEl);
        for (const dependentFieldEl of dependentFieldEls) {
            // Only check for circular dependencies on fields that do not
            // already have been checked.
            if (!visitedFields.has(dependentFieldEl)) {
                // Add the dependentFieldEl in the set of checked field.
                visitedFields.add(dependentFieldEl);
                if (dependentFieldEl.dataset.visibilityDependency === fieldName) {
                    return true;
                }
                const dependencyInputEl = getDependencyEl(dependentFieldEl);
                if (
                    dependencyInputEl &&
                    recursiveFindCircular(
                        dependencyInputEl.closest(".s_website_form_field"),
                        targetFieldEl
                    )
                ) {
                    return true;
                }
            }
        }
        return false;
    };
    return recursiveFindCircular(dependentFieldEl, targetFieldEl);
}

/**
 * Returns the domain of a field.
 *
 * @param {HTMLElement} formEl
 * @param {String} name
 * @param {String} type
 * @param {String} relation
 * @returns {Object|false}
 */
// TODO Solve this variable differently
const allFormsInfo = new Map();
export function getDomain(formEl, name, type, relation) {
    // We need this because the field domain is in formInfo in the
    // WebsiteFormEditor but we need it in the WebsiteFieldEditor.
    if (!allFormsInfo.get(formEl) || !name || !type || !relation) {
        return false;
    }
    const field = allFormsInfo
        .get(formEl)
        .fields.find((el) => el.name === name && el.type === type && el.relation === relation);
    return field && field.domain;
}

export function getModelName(formEl) {
    return formEl.dataset.model_name || "mail.mail";
}

export function getListItems(fieldEl) {
    const selectEl = getSelect(fieldEl);
    const multipleInputsEl = getMultipleInputs(fieldEl);
    let options = [];
    if (selectEl) {
        options = [...selectEl.querySelectorAll("option")];
    } else if (multipleInputsEl) {
        options = [...multipleInputsEl.querySelectorAll(".checkbox input, .radio input")];
    }
    const isFieldElCustom = isFieldCustom(fieldEl);
    return options.map((opt) => {
        const name = selectEl ? opt : opt.nextElementSibling;
        return {
            id: isFieldElCustom
                ? opt.id
                : /^-?[0-9]{1,15}$/.test(opt.value)
                ? parseInt(opt.value)
                : opt.value,
            display_name: name.textContent.trim(),
            selected: selectEl ? opt.selected : opt.checked,
        };
    });
}

/**
 * Sets the visibility dependency of the field.
 *
 * @param {HTMLElement} fieldEl
 * @param {string} value name of the dependency input
 */
export function setVisibilityDependency(fieldEl, value) {
    delete fieldEl.dataset.visibilityCondition;
    delete fieldEl.dataset.visibilityComparator;
    fieldEl.dataset.visibilityDependency = value;
}

/**
 * Re-renders a form field in the DOM.
 *
 * @param {HTMLElement} fieldEl - The original field element to be re-rendered.
 * @param {Object<string, Object>} fields - A map of all fields in the form.
 */
export function rerenderField(fieldEl, fields) {
    const field = getActiveField(fieldEl, { fields });
    delete field.id;
    const newFieldEl = renderField(field);
    replaceFieldElement(fieldEl, newFieldEl);
}
