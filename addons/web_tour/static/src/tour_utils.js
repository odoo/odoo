import { _t } from "@web/core/l10n/translation";

export const stepUtils = {
    showAppsMenuItem() {
        return {
            isActive: ["community", "desktop"],
            trigger: ".o_navbar_apps_menu button:enabled",
            tooltipPosition: "bottom",
            run: "click",
        };
    },

    toggleHomeMenu() {
        return [
            {
                isActive: [".o_main_navbar .o_menu_toggle"],
                trigger: ".o_main_navbar .o_menu_toggle",
                content: _t("Click the top left corner to navigate across apps."),
                run: "click",
            },
            {
                isActive: ["mobile"],
                trigger: ".o_sidebar_topbar a.btn-primary",
                tooltipPosition: "right",
                run: "click",
            },
        ];
    },

    autoExpandMoreButtons(isActiveMobile = false) {
        const isActive = ["auto"];
        if (isActiveMobile) {
            isActive.push("mobile");
        }
        return {
            isActive,
            content: `autoExpandMoreButtons`,
            trigger: ".o-form-buttonbox",
            async run({ queryFirst, click }) {
                const more = queryFirst(".o-form-buttonbox .o_button_more");
                if (more) {
                    await click(more);
                }
            },
        };
    },

    goToAppSteps(dataMenuXmlid, description) {
        return [
            this.showAppsMenuItem(),
            {
                isActive: ["community"],
                trigger: `.o_app[data-menu-xmlid="${dataMenuXmlid}"]`,
                content: description,
                tooltipPosition: "right",
                run: "click",
            },
            {
                isActive: ["enterprise"],
                trigger: `.o_app[data-menu-xmlid="${dataMenuXmlid}"]`,
                content: description,
                tooltipPosition: "bottom",
                run: "click",
            },
        ];
    },

    statusbarButtonsSteps(innerTextButton, description, trigger) {
        const steps = [];
        if (trigger) {
            steps.push({
                isActive: ["auto", "mobile"],
                trigger,
            });
        }
        steps.push(
            {
                isActive: ["auto", "mobile"],
                trigger: ".o_statusbar_buttons",
                async run({ queryFirst, click }) {
                    const buttonOutSideDropdownMenu = queryFirst(
                        `.o_statusbar_buttons button:enabled:contains('${innerTextButton}')`
                    );
                    const node = queryFirst(
                        ".o_statusbar_buttons button:has([data-icon='more_vert'])"
                    );
                    if (!buttonOutSideDropdownMenu && node) {
                        await click(node);
                    }
                },
            },
            {
                trigger: `.o_statusbar_buttons button:enabled:contains('${innerTextButton}'), .dropdown-item button:enabled:contains('${innerTextButton}')`,
                content: description,
                run: "click",
            }
        );
        return steps;
    },

    /**
     * Steps to search a many2one field, then either select the matching
     * existing record or create the typed value on the fly - both on desktop
     * (dropdown suggestion, or inline "Create and edit" option) and mobile
     * (the "Search: <label>" dialog, listing matching records and needing an
     * explicit tap on "Create" before the creation form opens).
     *
     * @param {string} trigger - CSS selector of the many2one input
     * @param {string} label - human-readable name of the record (e.g.
     *      "customer", "product"), used to match the mobile dialog titles
     *      and in the steps' tooltip content
     * @param {string} searchText - text to type in the many2one input
     * @param {Object<string, string>} fields - values to fill in the
     *      creation dialog, keyed by field name, in fill order (e.g.
     *      { name: "Agrolait", email: "agrolait@example.com" }); ignored
     *      when selectExisting is true
     * @param {boolean} [selectExisting=false] - select the matching existing
     *      record instead of creating a new one
     */
    searchOrCreateMany2X(trigger, label, searchText, fields, selectExisting = false) {
        const dialogSearch = `.o_dialog:has(.modal-title:contains('search: ${label}'))`;
        const steps = [
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
        ];
        if (selectExisting) {
            steps.push(
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
                }
            );
            return steps;
        }
        const dialogCreate = `.o_dialog:has(.modal-title:contains('create ${label}'))`;
        steps.push(
            {
                isActive: ["desktop"],
                trigger: ".o_m2o_dropdown_option_create_edit",
                content: _t("Create and edit the %s.", label),
                tooltipPosition: "right",
                run: "click",
            },
            {
                isActive: ["mobile"],
                trigger: `${dialogSearch} .o_create_button`,
                content: _t("Create the %s.", label),
                run: "click",
            }
        );
        for (const [fieldName, value] of Object.entries(fields)) {
            steps.push({
                trigger: `${dialogCreate} .o_field_widget[name='${fieldName}'] input, ${dialogCreate} .o_field_widget[name='${fieldName}'] textarea`,
                content: _t("Enter the %s.", fieldName),
                run: `edit ${value}`,
            });
        }
        steps.push({
            trigger: `${dialogCreate} .o_form_button_save`,
            content: _t("Save the %s.", label),
            run: "click",
        });
        return steps;
    },

    mobileKanbanSearchMany2X(modalTitle, valueSearched) {
        return [
            {
                isActive: ["mobile"],
                trigger: `.modal:not(.o_inactive_modal) .o_control_panel_navigation .btn [data-icon='search']`,
                run: "click",
            },
            {
                isActive: ["mobile"],
                trigger: ".o_searchview_input",
                run: `edit ${valueSearched}`,
            },
            {
                isActive: ["mobile"],
                trigger: ".dropdown-menu.o_searchview_autocomplete",
            },
            {
                isActive: ["mobile"],
                trigger: ".o_searchview_input",
                run: "press Enter",
            },
            {
                isActive: ["mobile"],
                trigger: `.modal:not(.o_inactive_modal) .o_kanban_record:contains('${valueSearched}')`,
                run: "click",
            },
        ];
    },
    /**
     * Utility steps to save a form and wait for the save to complete
     */
    saveForm() {
        return [
            {
                content: "save form",
                trigger: ".o_form_button_save",
                run: "click",
            },
            {
                content: "wait for save completion",
                trigger: ".o_form_readonly, .o_form_saved",
            },
        ];
    },
    /**
     * Utility steps to cancel a form creation or edition.
     *
     * Supports creation/edition from either a form or a list view (so checks
     * for both states).
     */
    discardForm() {
        return [
            {
                isActive: ["auto"],
                content: "discard the form",
                trigger: ".o_form_button_cancel",
                run: "click",
            },
            {
                content: "wait for cancellation to complete",
                trigger:
                    ".o_view_controller.o_list_view, .o_form_view > div > main > .o_form_readonly, .o_form_view > div > main > .o_form_saved",
            },
        ];
    },
};
