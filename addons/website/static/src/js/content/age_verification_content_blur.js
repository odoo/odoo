import { cookie } from "@web/core/browser/cookie";

// Blur page content immediately if age verification is pending to prevent
// restricted content from being visible before the popup interaction loads.
document.addEventListener("DOMContentLoaded", () => {
    const ageVerificationPopupEl = document.querySelector(
        ".s_age_verification_popup:has([data-blur-background])"
    );
    if (ageVerificationPopupEl) {
        const { blurBackground } =
            ageVerificationPopupEl.querySelector("[data-blur-background]").dataset;
        document.documentElement.style.setProperty(
            "--o-age-popup-background-blur",
            `${blurBackground === "true" ? 16 : blurBackground}px`
        );
        const isAgeVerified = cookie.get(ageVerificationPopupEl.id);
        ageVerificationPopupEl.dataset.ageVerificationPending = !isAgeVerified;
    }
});
