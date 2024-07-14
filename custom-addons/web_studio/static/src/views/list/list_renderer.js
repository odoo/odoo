/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useService } from "@web/core/utils/hooks";

import "@web_enterprise/views/list/list_renderer_desktop";

export const patchListRendererStudio = () => ({
    setup() {
        super.setup(...arguments);
        this.studioService = useService("studio");
    },
    /**
     * This function opens the studio mode with current view
     *
     * @override
     */
    onSelectedAddCustomField() {
        this.studioService.open();
    },

    isStudioEditable() {
        return !this.studioService.mode && super.isStudioEditable();
    },
});

export const unpatchListRendererStudio = patch(ListRenderer.prototype, patchListRendererStudio());
