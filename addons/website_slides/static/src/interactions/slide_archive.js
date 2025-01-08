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

    _openDialog: function ($slideTarget) {
        const slideId = $slideTarget.data("slideId");
        this.call("dialog", "add", ConfirmationDialog, {
            title: _t("Archive Content"),
            body: _t("Are you sure you want to archive this content?"),
            confirmLabel: _t("Archive"),
            confirm: async () => {
                /**
                 * Calls 'archive' on slide controller and then visually removes the slide dom element
                 */
                const isArchived = await rpc("/slides/slide/archive", {
                    slide_id: slideId,
                });
                if (isArchived) {
                    $slideTarget.closest(".o_wslides_slides_list_slide").remove();
                    $(".o_wslides_slide_list_category").each(function () {
                        var $categoryHeader = $(this).find(".o_wslides_slide_list_category_header");
                        var categorySlideCount = $(this).find(
                            ".o_wslides_slides_list_slide:not(.o_not_editable)"
                        ).length;
                        var $emptyFlagContainer = $categoryHeader
                            .find(".o_wslides_slides_list_drag")
                            .first();
                        var $emptyFlag = $emptyFlagContainer.find("small");
                        if (categorySlideCount === 0 && $emptyFlag.length === 0) {
                            $emptyFlagContainer.append(
                                $("<small>", {
                                    class: "ms-1 text-muted fw-bold",
                                    text: _t("(empty)"),
                                })
                            );
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
        var $slideTarget = $(ev.currentTarget);
        this._openDialog($slideTarget);
    },
});

export default {
    websiteSlidesSlideArchive: publicWidget.registry.websiteSlidesSlideArchive,
};
