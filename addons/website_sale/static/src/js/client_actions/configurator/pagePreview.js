import { onMounted, proxy, useListener } from "@odoo/owl";

import { useStore } from "@website/client_actions/configurator/configurator";
import {
    getConfiguratorPreviewUrl,
    getPreviewIframeDocument,
    replacePreviewIframeLogo,
    scalePreviewIframe,
} from "@website/client_actions/configurator/preview_iframe";

export function usePagePreviews() {
    const state = useStore();
    const failedPreviews = proxy(new Set());
    const scalePreviewIframes = () => {
        for (const iframe of document.querySelectorAll(
            ".o_wsale_configurator_screen .o_configurator_theme_preview_iframe"
        )) {
            scalePreviewIframe(iframe);
        }
    };
    onMounted(scalePreviewIframes);
    useListener(window, "resize", scalePreviewIframes);

    return {
        getUrl(previewUrl) {
            return getConfiguratorPreviewUrl(state, state.selectedThemeName, previewUrl);
        },
        hasFailed(previewUrl) {
            return failedPreviews.has(previewUrl);
        },
        onLoad(ev, previewUrl) {
            const iframe = ev.currentTarget;
            if (
                !getPreviewIframeDocument(iframe)?.getElementById(
                    "o_configurator_theme_preview_overrides"
                )
            ) {
                failedPreviews.add(previewUrl);
                return;
            }
            replacePreviewIframeLogo(iframe, state.logo);
            iframe.parentElement.classList.add("o_preview_loaded");
            scalePreviewIframe(iframe);
        },
    };
}
