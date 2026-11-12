import { cookie } from "@web/core/browser/cookie";

// Blur page content immediately if age verification is pending to prevent
// restricted content from being visible before the popup interaction loads.
document.addEventListener("DOMContentLoaded", () => {
    const modalEl = document.querySelector(".s_age_verification_popup [data-blur-background]");
    if (modalEl) {
        const { blurBackground } = modalEl.dataset;
        // "true" is the value of popups saved before the blur became a slider:
        // the default blur of the stylesheet applies to them.
        // The custom property is set on the root, so only the first popup of
        // the page defines the blur.
        if (blurBackground !== "true") {
            document.documentElement.style.setProperty(
                "--o-age-popup-background-blur",
                `${blurBackground}px`
            );
        }
        const ageVerificationPopupEl = modalEl.closest(".s_age_verification_popup");
        const isAgeVerified = cookie.get(ageVerificationPopupEl.id);
        ageVerificationPopupEl.dataset.ageVerificationPending = !isAgeVerified;
    }
});
