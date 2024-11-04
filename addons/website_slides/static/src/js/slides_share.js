import publicWidget from '@web/legacy/js/public/public_widget';
import { SlideShareDialog } from './public/components/slide_share_dialog/slide_share_dialog';
import { browser } from '@web/core/browser/browser';


publicWidget.registry.websiteSlidesShare = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    events: {
        'click .o_wslides_share': '_onClickShareSlide',
    },

    getDocumentMaxPage() {
        const iframe = document.querySelector("iframe.o_wslides_iframe_viewer");
        const iframeDocument = iframe.contentWindow.document;
        return parseInt(iframeDocument.querySelector("#page_count").innerText);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickShareSlide: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        const data = ev.currentTarget.dataset;
        this.call("dialog", "add", SlideShareDialog, {
            category: data.category,
            documentMaxPage: data.category == 'document' && this.getDocumentMaxPage(),
            emailSharing: data.emailSharing === 'True',
            embedCode: data.embedCode,
            id: parseInt(data.id),
            isChannel: data.isChannel === 'True',
            name: data.name,
            url: data.url,
        });
    },
});

publicWidget.registry.websiteSlidesEmbedShare = publicWidget.Widget.extend({
    selector: '.oe_slide_js_embed_code_widget',
    events: {
        'click .o_embed_clipboard_button': '_onShareLinkCopy',
    },

    _onShareLinkCopy: async function (ev) {
        ev.preventDefault();
        const $clipboardBtn = $(ev.currentTarget);
        $clipboardBtn.tooltip({title: "Copied!", trigger: "manual", placement: "bottom"});
        var share_embed_el = this.$('#wslides_share_embed_id_' + $clipboardBtn[0].id.split('id_')[1]);
        await browser.navigator.clipboard.writeText(share_embed_el.val() || '');
        $clipboardBtn.tooltip('show');
        setTimeout(function () {
            $clipboardBtn.tooltip("hide");
        }, 800);
    },
});

export const WebsiteSlidesShare = publicWidget.registry.websiteSlidesShare;
export const WebsiteSlidesEmbedShare = publicWidget.registry.websiteSlidesEmbedShare;
