import { registry } from "@web/core/registry";

/**
 * Tours for the "role reverts / regular-user marker missing" investigation
 * (res.users `role` <-> `group_ids` sync). They drive the actual widgets
 * (the "Role" radio and the "Extra Rights" group_ids sub-widget, only
 * visible in debug mode) instead of Form()/onchange() simulation, since
 * the suspected desync is in how the real web client tracks/saves fields,
 * not in the Python onchange logic itself (already covered by backend
 * tests in base/tests/test_res_users.py).
 *
 * Each tour is a single atomic step (set a value, save, or reload); the
 * Python side (web/tests/test_res_users.py) chains them with backend
 * assertions in between, and composes the different "with/without
 * intermediate reload" combinations by choosing which atomic tours to run
 * in one browser session (no reload in between) versus separate
 * start_tour() calls (each one a fresh page load, i.e. a reload).
 */

function waitForRoleRadio() {
    return {
        content: "wait for the user form (Role field) to be loaded",
        trigger: '.o_field_widget[name="role"] div[role="radiogroup"]',
    };
}

function setRole(value) {
    return {
        content: `set role to '${value}'`,
        trigger: `.o_field_widget[name="role"] input[data-value="${value}"]`,
        run: "click",
    };
}

function saveForm() {
    // Clicking Save only *starts* the onchange+web_save round-trip; it's
    // async, so the tour must not end (and the harness's post-tour dirty
    // check must not run) until it actually completes -- otherwise the
    // save is caught mid-flight and the harness reports a false "dirty
    // form" failure. The Save button only renders while the form is
    // dirty, so waiting for it to disappear is the signal that the save
    // (and its onchange-triggered recompute) has really landed.
    return [
        {
            content: "save the form",
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            content: "wait for the save to actually complete (Save button gone = clean)",
            trigger: ".o_form_button_save:not(:visible)",
        },
    ];
}

function reloadPage() {
    return [
        {
            content: "reload the page (F5)",
            trigger: "body",
            run: () => location.reload(),
            expectUnloadPage: true,
        },
        waitForRoleRadio(),
    ];
}

function toggleExtraGroup(groupName, { checked }) {
    const stateSelector = checked ? ":not(:checked)" : ":checked";
    return {
        content: `${checked ? "check" : "uncheck"} the 'Extra Rights' group "${groupName}"`,
        trigger:
            `.o_field_widget[name="group_ids"] .o_extra_rights_group ` +
            `.o_cell:has(label:contains("${groupName}")) + .o_cell input[type="checkbox"]${stateSelector}`,
        run: "click",
    };
}

// -- atomic building blocks, composed from Python between backend checks --

registry.category("web_tour.tours").add("role_sync_set_light_and_save", {
    steps: () => [waitForRoleRadio(), setRole("light_user"), ...saveForm()],
});

registry.category("web_tour.tours").add("role_sync_set_regular_and_save", {
    steps: () => [waitForRoleRadio(), setRole("regular_user"), ...saveForm()],
});

registry.category("web_tour.tours").add("role_sync_reload_only", {
    steps: () => [waitForRoleRadio(), ...reloadPage()],
});

// "sans reload intermédiaire": both toggles + saves in ONE browser session
registry.category("web_tour.tours").add("role_sync_light_save_regular_save_no_reload", {
    steps: () => [
        waitForRoleRadio(),
        setRole("light_user"),
        ...saveForm(),
        setRole("regular_user"),
        ...saveForm(),
    ],
});

// Same idea, but starting from 'regular' (the test user is 'light_user' by
// default, so a tour that starts with setRole("light_user") would find the
// radio already selected -- a no-op, form never becomes dirty, no Save
// button appears). Three toggles, all saved, no reload in between, ending
// back on 'regular_user' so the post-reload assertion is meaningful.
registry.category("web_tour.tours").add("role_sync_regular_save_light_save_regular_save_no_reload", {
    steps: () => [
        waitForRoleRadio(),
        setRole("regular_user"),
        ...saveForm(),
        setRole("light_user"),
        ...saveForm(),
        setRole("regular_user"),
        ...saveForm(),
    ],
});

// set the role but never click Save: reload right away and see whether
// anything at all was persisted (Odoo's edit-discard-on-navigate path,
// as opposed to an explicit Save click)
registry.category("web_tour.tours").add("role_sync_set_light_no_save_then_reload", {
    steps: () => [waitForRoleRadio(), setRole("light_user"), ...reloadPage()],
});

registry.category("web_tour.tours").add("role_sync_set_regular_no_save_then_reload", {
    steps: () => [waitForRoleRadio(), setRole("regular_user"), ...reloadPage()],
});

// group_ids -> role direction (the reverse of the above): toggling a plain
// group with no privilege_id (only shown in the "Extra Rights" section,
// itself only rendered in debug mode) must make `role` compute to
// 'regular_user' via _compute_role.
registry.category("web_tour.tours").add("role_sync_check_extra_group_and_save", {
    steps: () => [
        waitForRoleRadio(),
        toggleExtraGroup("Test Role Sync Extra Group", { checked: true }),
        ...saveForm(),
    ],
});

registry.category("web_tour.tours").add("role_sync_uncheck_extra_group_and_save", {
    steps: () => [
        waitForRoleRadio(),
        toggleExtraGroup("Test Role Sync Extra Group", { checked: false }),
        ...saveForm(),
    ],
});
