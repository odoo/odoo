import { CookiesBar } from "@website/interactions/cookies/cookies_bar";
import { patch } from "@web/core/utils/patch";
import { patchDynamicContent } from "@web/public/utils";

patch(CookiesBar.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            // When user resizes the window, we need to adjust the position of
            // the compare button to improve the user experience.
            _window: {
                "t-on-resize": this.handleCompareOverlap.bind(this),
            },
        });
        // Listen for the custom event to handle the overlap of the compare
        // button with the cookies bar modal.
        this._onCookiesBarShown = this.handleCompareOverlap.bind(this);
        this.el.addEventListener("COOKIES_BAR_SHOWN", this._onCookiesBarShown);
    },
    /**
     * @override
     */
    destroy() {
        super.destroy();
        this.el.removeEventListener("COOKIES_BAR_SHOWN", this._onCookiesBarShown);
    },
    /**
     * @override
     */
    showPopup() {
        super.showPopup();
        // Initially when the modal is shown, its height is 0, so we need to
        // wait for the modal to be fully rendered before adjusting the position
        // of the compare button. Through the `--move-cookie-over-modal` CSS
        // variable, we can dynamically adjust the position of elements based on
        // modal changes.
        this.waitForTimeout(() => {
            this.handleCompareOverlap();
        }, 0);
    },
    /**
     * @override
     *
     * Remove the custom css for `--move-cookie-over-modal`, to position the
     * compare button at the bottom.
     */
    onHideModal() {
        super.onHideModal();
        document
            .querySelector("[name='product_comparison_button']")
            ?.style.removeProperty("--move-cookie-over-modal");
    },
    /**
     * Resolved the issue where the compare button was hidden due to the modal
     * appearing over it. Added CSS `--move-cookie-over-modal` to dynamically
     * adjust the position of elements based on modal changes.
     */
    handleCompareOverlap() {
        const productCompareButtonEl = document.querySelector("[name='product_comparison_button']");
        if (!productCompareButtonEl) {
            return;
        }

        const cookieModelEl = this.el.querySelector(".modal");
        if (
            !cookieModelEl ||
            cookieModelEl.style.display === "none" ||
            cookieModelEl.classList.contains("o_cookies_popup") ||
            !cookieModelEl.classList.contains("s_popup_no_backdrop")
        ) {
            return;
        }
        const cookieModalDialogEl = cookieModelEl.querySelector(".modal-dialog");
        const isCookiebarLarge =
            (cookieModalDialogEl.getBoundingClientRect().width -
                productCompareButtonEl.getBoundingClientRect().width / 2) /
                window.innerWidth >
            0.5;

        if (isCookiebarLarge) {
            const bottom = cookieModalDialogEl.querySelector(".modal-content").offsetHeight
                ? `${cookieModalDialogEl.querySelector(".modal-content").offsetHeight}px`
                : "";
            const padding = getComputedStyle(cookieModalDialogEl).paddingBottom;
            productCompareButtonEl.style.setProperty(
                "--move-cookie-over-modal",
                parseInt(bottom) + parseInt(padding) + "px"
            );
        } else {
            productCompareButtonEl.style.removeProperty("--move-cookie-over-modal");
        }
    },
});
