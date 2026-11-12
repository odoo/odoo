import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * Applies the background blur of the age verification popup in edit mode. The
 * blur overlay is drawn on `#wrapwrap`, which cannot read the value set on the
 * popup. On the website, `age_verification_content_blur.js` does it on load.
 */
export class AgeVerificationPopupBlurEdit extends Interaction {
    static selector = ".s_age_verification_popup .modal";
    dynamicContent = {
        _body: {
            "t-att-style": () => {
                const { blurBackground } = this.el.dataset;
                return {
                    // "true" (popups saved before the blur became a slider)
                    // uses the default blur of the stylesheet.
                    "--o-age-popup-background-blur":
                        blurBackground && blurBackground !== "true"
                            ? `${blurBackground}px`
                            : undefined,
                };
            },
        },
    };

    getConfigurationSnapshot() {
        // Only restart when the blur changes.
        return this.el.dataset.blurBackground;
    }
}

registry.category("public.interactions.edit").add("website.age_verification_popup_blur", {
    Interaction: AgeVerificationPopupBlurEdit,
});
