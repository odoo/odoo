/** @odoo-module native */

// evaluated before DOMContentLoaded, as every module in the minimal bundle is
document.addEventListener("DOMContentLoaded", () => {
    for (const textarea of document.querySelectorAll("textarea.o_wysiwyg_loader")) {
        const wrapper = document.createElement("div");
        wrapper.classList.add("position-relative", "o_wysiwyg_textarea_wrapper");

        const loadingElement = document.createElement("div");
        loadingElement.classList.add("o_wysiwyg_loading");
        const loadingIcon = document.createElement("i");
        loadingIcon.classList.add(
            "text-600",
            "text-center",
            "fa-solid",
            "fa-circle-notch",
            "fa-spin",
            "fa-2x",
        );
        loadingElement.appendChild(loadingIcon);
        wrapper.appendChild(loadingElement);

        textarea.parentNode.insertBefore(wrapper, textarea);
        wrapper.insertBefore(textarea, loadingElement);
    }
});
