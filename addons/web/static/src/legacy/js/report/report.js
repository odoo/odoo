/** @odoo-module */

// Essentially keeps the CSS for legacy HTML reports (full width,...).
// Can be removed once the reports are fully converted.
owl.whenReady(() => {
    if (window.self === window.top) {
        return;
    }
    document.body.classList.add("o_in_iframe", "container-fluid");
    document.body.classList.remove("container");
});
