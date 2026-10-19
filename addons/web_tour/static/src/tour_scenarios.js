import { _t } from "@web/core/l10n/translation";

/**
 * Steps to type a value into a many2one input and open its "Create and
 * edit..." dialog. In robot mode this is forced deterministically (the
 * dialog is guaranteed to open, onboarding starts from a blank database so
 * there's nothing else to pick). In manual mode nothing is forced: a real
 * user is free to either open the dialog or pick a suggestion instead - the
 * "edit" step is already consumed by either action, and the fields/save
 * steps added by searchOrCreateMany2X only activate if the dialog actually
 * opened (see its own isActive there).
 *
 * @param {string} trigger - CSS selector of the many2one input
 * @param {string} label - human-readable name of the record (e.g.
 *      "customer", "product"), used to match the mobile "Search: <label>"
 *      dialog and in the steps' tooltip content
 * @param {string} value - text to type in the many2one input
 */
function editMany2oneAndCreate({ trigger, label, value }) {
    const dialogSearch = `.o_dialog:has(.modal-title:contains('search: ${label}'))`;
    return [
        {
            isActive: ["desktop"],
            trigger,
            content: _t("Create a new %s.", label),
            tooltipPosition: "right",
            run: `edit ${value}`,
        },
        {
            isActive: ["mobile"],
            trigger,
            content: _t("Create a new %s.", label),
            run: `click`,
        },
        {
            isActive: ["robot", "desktop"],
            trigger: ".o_m2o_dropdown_option_create_edit",
            content: _t("Create and edit the %s.", label),
            tooltipPosition: "right",
            run: "click",
        },
        {
            isActive: ["robot", "mobile"],
            trigger: `${dialogSearch} .o_create_button`,
            content: _t("Create the %s.", label),
            run: "click",
        },
    ];
}

/**
 * Steps to search a many2one field, then either select the matching
 * existing record or create the typed value on the fly - both on desktop
 * (dropdown suggestion, or inline "Create and edit" option) and mobile
 * (the "Search: <label>" dialog, listing matching records and needing an
 * explicit tap on "Create" before the creation form opens).
 *
 * @param {Object} params
 * @param {string} params.trigger - CSS selector of the many2one input
 * @param {string} params.label - human-readable name of the record (e.g.
 *      "customer", "product"), used to match the mobile dialog titles
 *      and in the steps' tooltip content
 * @param {string} params.searchText - text to type in the many2one input
 * @param {Object<string, string>} [params.fields] - values to fill in the
 *      creation dialog, keyed by field name, in fill order (e.g.
 *      { name: "Agrolait", email: "agrolait@example.com" }); ignored
 *      when selectExisting is true
 * @param {boolean} [params.selectExisting=false] - the searched text is
 *      reference/system data guaranteed to already exist (e.g. a default
 *      mailing list, the current user) rather than business data the tour
 *      is meant to create - select it instead of creating a new record,
 *      deterministically, in both robot and manual mode.
 */
export function searchOrCreateMany2X({
    trigger,
    label,
    searchText,
    fields = {},
    selectExisting = false,
}) {
    if (selectExisting) {
        const dialogSearch = `.o_dialog:has(.modal-title:contains('search: ${label}'))`;
        return [
            {
                isActive: ["desktop"],
                trigger,
                content: _t("Search or create %s.", label),
                tooltipPosition: "right",
                run: `edit ${searchText}`,
            },
            {
                isActive: ["mobile"],
                trigger,
                content: _t("Search or create %s.", label),
                run: `click`,
            },
            {
                isActive: ["desktop"],
                trigger: `.o-autocomplete--dropdown-item:contains('${searchText}')`,
                content: _t("Select this %s.", label),
                run: "click",
            },
            {
                isActive: ["mobile"],
                trigger: `${dialogSearch} .o_kanban_record:contains('${searchText}')`,
                content: _t("Select this %s.", label),
                run: "click",
            },
        ];
    }
    const dialogCreate = `.o_dialog:has(.modal-title:contains('create ${label}'))`;
    const steps = editMany2oneAndCreate({ trigger, label, value: searchText });
    for (const [fieldName, value] of Object.entries(fields)) {
        steps.push({
            isActive: ["robot"],
            trigger: `${dialogCreate} .o_field_widget[name='${fieldName}'] input, ${dialogCreate} .o_field_widget[name='${fieldName}'] textarea`,
            content: _t("Enter the %s.", fieldName),
            run: `edit ${value}`,
        });
    }
    steps.push({
        isActive: ["robot"],
        trigger: `${dialogCreate} .o_form_button_save`,
        content: _t("Save the %s.", label),
        run: "click",
    });
    return steps;
}
