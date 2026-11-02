import { _t } from "@web/core/l10n/translation";
import { stepUtils as coreStepUtils } from "@web_tour/tour_utils";

/**
 * Manual-mode friendly `stepUtils` for the OD19 user guide tours.
 *
 * Core `stepUtils.showAppsMenuItem()` declares
 * `isActive: ["auto", "community", "desktop"]`. Because that list contains
 * "auto", `TourStep.active` (web_tour/static/src/js/tour_step.js) turns the
 * step OFF as soon as the tour runs in manual mode. The "open the app
 * switcher" step is therefore silently skipped, and the following
 * `.o_app[...]` step waits for an element that is not on screen yet (starting
 * a tour redirects to `/odoo`, which lands on the first app, not on the app
 * grid). Users clicking "Onboarding" end up seeing nothing happen.
 *
 * Overriding `goToAppSteps` keeps every other core helper untouched while
 * making the app-switcher step depend on what is actually displayed instead of
 * on the tour mode.
 */
/**
 * Exact-label selector for a **top-level section** of the current app navbar.
 *
 * Odoo 19 renders the app sections inside `.o_menu_sections`:
 *  - a section that owns children becomes a `<button class="dropdown-toggle">
 *    <span>NAME</span></button>`;
 *  - a childless section becomes a `<a class="o_nav_entry">NAME</a>`.
 *
 * `:text()` performs a **strict equality** match on the element text, while
 * `:contains()` matches any substring. The old `:contains()` selectors used to
 * match the wrapping dropdown group (which contains every label) and therefore
 * clicked nothing at all.
 */
export function navSection(label) {
    return (
        `.o_menu_sections .dropdown-toggle:text('${label}'), ` +
        `.o_menu_sections .o_nav_entry:text('${label}')`
    );
}

/**
 * Exact-label selector for an entry **inside an opened dropdown menu**.
 *
 * `web.NavBar.SectionsMenu.Dropdown.MenuSlot` renders the whole sub-tree of a
 * section inside a single dropdown, so every descendant — whatever its depth —
 * is a `.dropdown-item`. Group headers (`<div class="dropdown-menu_group
 * dropdown-header">`) are *not* clickable: target the child item instead.
 *
 * Always click `navSection(parentSection)` in a previous step to open the
 * dropdown before using this selector.
 */
export function navItem(label) {
    return `.dropdown-menu .dropdown-item:text('${label}')`;
}

/**
 * Wait until the action opened by the previous `navItem()` is really on screen.
 *
 * Clicking a menu entry switches the action asynchronously: the previous view
 * stays mounted for a few frames. A following generic step such as
 * `.o_list_button_add` would then click the *previous* list's "New" button and
 * create a record in the wrong model (e.g. an invoice instead of a petty-cash
 * fund). Waiting for the expected action name in the control-panel breadcrumb
 * guarantees the new view is displayed before the tour continues.
 */
export function waitForAction(name) {
    return {
        trigger: `.o_last_breadcrumb_item:contains('${name}')`,
    };
}

export const stepUtils = {
    ...coreStepUtils,

    showAppsMenuItem() {
        return {
            isActive: ["body:not(:has(.o_app))"],
            trigger: ".o_navbar_apps_menu button:enabled",
            tooltipPosition: "bottom",
            run: "click",
        };
    },

    goToAppSteps(dataMenuXmlid, description) {
        return [
            {
                isActive: ["body:not(:has(.o_app))"],
                trigger: ".o_navbar_apps_menu button:enabled",
                content: description,
                tooltipPosition: "bottom",
                run: "click",
            },
            {
                trigger: `.o_app[data-menu-xmlid="${dataMenuXmlid}"]`,
                content: description,
                tooltipPosition: "right",
                run: "click",
            },
            {
                // Switching apps is asynchronous: the previous app stays
                // mounted for a few frames. A following `navSection()` would
                // then click the *old* app's menu — several apps expose a
                // section literally named "Configuration" — and the tour would
                // open the wrong dropdown and fail to find its entry.
                //
                // `.o_menu_brand` carries `data-menu-xmlid` = the xmlid of the
                // app that is really current (see web navbar.xml), so waiting
                // for it guarantees the new app navbar is mounted before the
                // tour continues.
                trigger: `.o_menu_brand[data-menu-xmlid="${dataMenuXmlid}"]`,
            },
        ].map((step) =>
            this.addDebugHelp(this._getHelpMessage("goToApp", dataMenuXmlid, description), step)
        );
    },

    /**
     * Manual-mode friendly `saveForm()`. Core gates the click behind
     * `isActive: ["auto"]`, so the step is inactive in manual mode: the record
     * is never saved and the following steps wait for a state that never comes.
     */
    saveForm() {
        return [
            {
                isActive: [".o_control_panel .o_form_button_save:visible"],
                content: _t("Save the record."),
                trigger: ".o_control_panel .o_form_button_save:visible",
                tooltipPosition: "bottom",
                run: "click",
            },
            {
                // Saving can either leave the form open in readonly mode
                // (`.o_form_readonly` / `.o_form_saved`) or — when the form was
                // opened from a list — close it and fall back to the list view.
                // Accept both outcomes so tours that save-and-return do not
                // hang waiting for a form that is already gone.
                trigger: ".o_form_readonly, .o_form_saved, .o_list_view, .o_list_renderer, .o_kanban_view",
            },
        ];
    },

    /**
     * Manual-mode friendly `discardForm()`. Same `isActive: ["auto"]` problem
     * as `saveForm()`: without the fix the form is never left, and the next
     * `goToAppSteps()` gets stuck behind the dirty form.
     *
     * The `:visible` guard matters because Odoo keeps `.o_form_button_cancel`
     * in the DOM even on a saved (readonly) form, where it is hidden. Without
     * it the step stayed "active" and then timed out on an invisible trigger.
     * When there is nothing left to discard we fall back to the control-panel
     * back arrow so the tour still returns to the list view.
     */
    discardForm() {
        return [
            {
                isActive: [".o_control_panel .o_form_button_cancel:visible"],
                content: _t("Discard the form to leave it."),
                trigger: ".o_control_panel .o_form_button_cancel:visible",
                tooltipPosition: "bottom",
                run: "click",
            },
            {
                isActive: [".o_control_panel .o_back_button:visible"],
                content: _t("Go back to the list."),
                trigger: ".o_control_panel .o_back_button:visible",
                tooltipPosition: "bottom",
                run: "click",
            },
            {
                trigger: ".o_list_view, .o_kanban_view",
            },
        ];
    },
};
