import { onMounted, useListener } from "@odoo/owl";

import { useStore } from "@website/client_actions/configurator/configurator";
import {
    getConfiguratorPreviewUrl,
    replacePreviewIframeLogo,
    scalePreviewIframe,
} from "@website/client_actions/configurator/preview_iframe";

const PREVIEW_IFRAME_SELECTOR = ".o_wsale_configurator_screen .o_configurator_theme_preview_iframe";

export function usePagePreviews() {
    const state = useStore();
    const scalePreviewIframes = () => {
        for (const iframe of document.querySelectorAll(PREVIEW_IFRAME_SELECTOR)) {
            scalePreviewIframe(iframe);
        }
    };
    onMounted(scalePreviewIframes);
    useListener(window, "resize", scalePreviewIframes);

    return {
        getUrl(previewUrl) {
            return getConfiguratorPreviewUrl(state, previewUrl, state.selectedThemeName);
        },
        onLoad(ev) {
            const iframe = ev.currentTarget;
            replacePreviewIframeLogo(iframe, state.logo);
            iframe.parentElement.classList.add("o_preview_loaded");
            scalePreviewIframe(iframe);
        },
    };
}
