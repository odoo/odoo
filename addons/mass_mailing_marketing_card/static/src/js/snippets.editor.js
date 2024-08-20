// import { patch } from "@web/core/utils/patch";

// import { MassMailingSnippetsMenu } from "@mass_mailing/fields/mass_mailing_html_field/mass_mailing_snippet_menu";

// patch(MassMailingSnippetsMenu.prototype, {
//     setup() {
//         this._massMailingDefaultCampaignId = this.props.options.originalDefaultCampaignId || 0;
//         super.setup(...arguments);
//         const wysiwyg = this.props.options.wysiwyg;
//         this._massMailingDefaultCampaignUnsub = wysiwyg._subscribeUpdateDefaultCardCampaign(
//             this._replaceCardSnippetDefaultCampaign.bind(this),
//         );
//     },
//     /**
//      * Go into the snippet data mapping and edit the base body of the snippet
//      * to reflect the default campaign id for the current mass mailing model
//      * @param {number} defaultCampaignId
//      */
//     _replaceCardSnippetDefaultCampaign(defaultCampaignId) {
//         this._massMailingDefaultCampaignId = defaultCampaignId;
//         const cardSnippet = [...this.snippets.entries()].filter(
//             (snippetEntry) => snippetEntry[1].name === "s_call_to_share_card",
//         )?.[0]?.[1];
//         if (!cardSnippet) {
//             return;
//         }
//         const anchor = cardSnippet.baseBody.querySelector("a");
//         const img = cardSnippet.baseBody.querySelector("img");
//         cardSnippet.baseBody.dataset.campaignId = defaultCampaignId;
//         img.src = img.src.replace(
//             /\/web\/image\/card.campaign\/([0-9]+)\/image_preview/,
//             `/web/image/card.campaign/${defaultCampaignId}/image_preview`,
//         );
//         anchor.href = anchor.href.replace(
//             /\/cards\/([0-9]+)\/preview/,
//             `/cards/${defaultCampaignId}/preview`,
//         );
//     },
//     /**
//      * update the snippets with the right default campaign at set up
//      * and whenever they need to be re-built
//      * @override
//      */
//     _makeSnippetDraggable() {
//         const res = super._makeSnippetDraggable(...arguments);
//         this._replaceCardSnippetDefaultCampaign(this._massMailingDefaultCampaignId);
//         return res;
//     },
//     /**
//      * unsubscribe from model change notifier
//      * @override
//      */
//     destroy() {
//         this._massMailingDefaultCampaignUnsub();
//         return super.destroy(...arguments);
//     },
// });
