document.addEventListener("DOMContentLoaded", () => {
    for (const el of document.querySelectorAll(".o_rental_lease_note")) {
        el.innerHTML = el.dataset.note || "";
    }
});
