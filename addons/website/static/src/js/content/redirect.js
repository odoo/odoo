import { session } from "@web/session";

/**
 * This script, served with frontend pages, displays buttons in the top left
 * corner to provide the authenticated user an access to his odoo backend.
 * In the case of the page being viewed in the website_preview client action,
 * it will forward some events to its parent.
 */
document.addEventListener("DOMContentLoaded", () => {
    if (session.is_website_user) {
        return;
    }

    if (!window.frameElement) {
        const frontendToBackendNavEl = document.querySelector(".o_frontend_to_backend_nav");
        if (frontendToBackendNavEl) {
            frontendToBackendNavEl.classList.add("d-flex");
            frontendToBackendNavEl.classList.remove("d-none");
        }
        // Auto redirect to frontend if edit/translation mode is requested
        const currentUrl = new URL(window.location.href);
        currentUrl.pathname = `/@${currentUrl.pathname}`;
        if (
            currentUrl.searchParams.get("enable_editor") ||
            currentUrl.searchParams.get("edit_translations")
        ) {
            document.body.innerHTML = "";
            window.location.replace(currentUrl.href);
            return;
        }
        const backendEditBtnEl = document.querySelector(".o_frontend_to_backend_edit_btn");
        if (backendEditBtnEl) {
            backendEditBtnEl.href = currentUrl.href;
            document.addEventListener(
                "keydown",
                (ev) => {
                    if (ev.key === "a" && ev.altKey) {
                        currentUrl.searchParams.set("enable_editor", 1);
                        currentUrl.searchParams.set("edit_translations", 1);
                        window.location.replace(currentUrl.href);
                    }
                },
                true
            );
        }
    } else {
        const backendUserDropdownLinkEl = document.getElementById("o_backend_user_dropdown_link");
        if (backendUserDropdownLinkEl) {
            backendUserDropdownLinkEl.classList.add("d-none");
            backendUserDropdownLinkEl.classList.remove("d-flex");
        }
        // Multiple reasons to do this:
        // - It seems like DOMContentLoaded doesn't always trigger when
        //   listened from the parent window
        // - Having an event that's fire only when the page is from Odoo avoids
        //   weird behaviours. (e.g. if we want to clear out the iframe, it might
        //   fire an DOMContentLoaded on a non odoo page)
        window.frameElement.dispatchEvent(new CustomEvent("OdooFrameContentLoaded"));
    }
});
