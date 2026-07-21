/** @odoo-module **/

document.addEventListener("click", (ev) => {
    const btn = ev.target.closest(".mv_cancel_deal");
    if (!btn) {
        return;
    }

    ev.preventDefault();
    ev.stopPropagation();

    window.history.back();
});
