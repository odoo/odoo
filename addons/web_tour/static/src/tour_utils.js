import { _t } from "@web/core/l10n/translation";

export const stepUtils = {
    editSelectMenuInput(trigger, value) {
        return [
            {
                content: "Make sure a SelectMenu has been opened",
                trigger: `.o_select_menu_menu`,
            },
            {
                trigger,
                run: `edit ${value}`,
            },
        ];
    },

    showAppsMenuItem() {
        return {
            isActive: ["auto", "community", "desktop"],
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
                    const node = queryFirst(".o_statusbar_buttons button:has(.oi-ellipsis-v)");
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

    mobileKanbanSearchMany2X(modalTitle, valueSearched) {
        return [
            {
                isActive: ["mobile"],
                trigger: `.modal:not(.o_inactive_modal) .o_control_panel_navigation .btn .fa-search`,
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
                trigger: `.o_kanban_record:contains('${valueSearched}')`,
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
                isActive: ["auto"],
                content: "save form",
                trigger: ".o_form_button_save:enabled",
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

    waitIframeIsReady() {
        return {
            content: "Wait until the iframe is ready",
            trigger: `:iframe body[is-ready=true]`,
        };
    },

    goToUrl(url) {
        return {
            isActive: ["auto"],
            content: `Navigate to ${url}`,
            trigger: "body",
            run: `goToUrl ${url}`,
            expectUnloadPage: true,
        };
    },
};
