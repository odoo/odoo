import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.websiteSlidesSlideArchive = publicWidget.Widget.extend({
    selector: ".o_wslides_js_slide_archive",
    events: {
        click: "_onArchiveSlideClick",
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _openDialog(slideTarget) {
        const slideId = slideTarget.dataset.slideId;
        this.call("dialog", "add", ConfirmationDialog, {
            title: _t("Archive Content"),
            body: _t("Are you sure you want to archive this content?"),
            confirmLabel: _t("Archive"),
            confirm: async () => {
                /**
                 * Calls 'archive' on slide controller and then visually removes the slide dom element
                 */
                const isArchived = await rpc("/slides/slide/archive", {
                    slide_id: parseInt(slideId),
                });
                if (isArchived) {
                    slideTarget.closest(".o_wslides_slides_list_slide").remove();
                    this.el.querySelectorAll(".o_wslides_slide_list_category").forEach((el) => {
                        const categoryHeaderEl = el.querySelector(
                            ".o_wslides_slide_list_category_header"
                        );
                        const categorySlideCount = el.querySelectorAll(
                            ".o_wslides_slides_list_slide:not(.o_not_editable)"
                        ).length;
                        const emptyFlagContainerEl = categoryHeaderEl.querySelector(
                            ".o_wslides_slides_list_drag"
                        );
                        const emptyFlagEl = emptyFlagContainerEl.querySelector("small");
                        if (categorySlideCount === 0 && !emptyFlagEl) {
                            const smallEl = document.createElement("small");
                            smallEl.className = "ms-1 text-muted fw-bold";
                            smallEl.textContent = _t("(empty)");
                            emptyFlagContainerEl.appendChild(smallEl);
                        }
                    });
                }
            },
            cancel: () => {},
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onArchiveSlideClick: function (ev) {
        ev.preventDefault();
        const slideTarget = ev.currentTarget;
        this._openDialog(slideTarget);
    },
});

export default {
    websiteSlidesSlideArchive: publicWidget.registry.websiteSlidesSlideArchive,
};
