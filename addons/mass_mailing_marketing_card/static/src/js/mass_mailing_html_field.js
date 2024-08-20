// import { MassMailingHtmlField } from "@mass_mailing/js/mass_mailing_html_field";
// import { patch } from "@web/core/utils/patch";

// patch(MassMailingHtmlField.prototype, {
//     setup() {
//         super.setup();
//         this.defaultCardCampaignId = 0;
//         this.previousModel = this.props.record.data.mailing_model_real;
//     },
//     commitChanges() {
//         const editor = this.wysiwyg?.odooEditor;
//         if (editor) {
//             const cards = editor.editable.querySelectorAll(".s_call_to_share_card");
//             for (const card of cards) {
//                 if (!card.dataset.campaignId || !parseInt(card.dataset.campaignId)) {
//                     card.remove();
//                 }
//             }
//             editor.historyStep();
//         }
//         return super.commitChanges(...arguments);
//     },
//     _onModelChange(record) {
//         this.orm
//             .searchRead(
//                 "card.campaign",
//                 [["res_model", "=", record.data.mailing_model_real]],
//                 ["id"],
//                 { limit: 1 },
//             )
//             .then((campaignResult) => {
//                 let defaultCardCampaignId = 0;
//                 if (campaignResult && campaignResult.length) {
//                     defaultCardCampaignId = campaignResult[0]["id"];
//                 }
//                 this.defaultCardCampaignId = defaultCardCampaignId;
//                 this.wysiwyg?._notifyUpdateDefaultCardCampaign(defaultCardCampaignId);
//                 const newModel = record.data.mailing_model_real;
//                 if (!defaultCardCampaignId) {
//                     this._removeMarketingCards(newModel);
//                 } else {
//                     this._updateMarketingCards(newModel, defaultCardCampaignId);
//                 }
//                 this.previousModel = newModel;
//             });
//         super._onModelChange(record);
//     },
//     /**
//      * Clean up all cards when they have an invalid campaign.
//      */
//     _removeMarketingCards(newModel) {
//         if (!this.wysiwyg?.odooEditor?.editable || newModel === this.previousModel) {
//             return;
//         }
//         const cards = this.wysiwyg.odooEditor.editable.querySelectorAll(".s_call_to_share_card");
//         for (const card of cards) {
//             card.remove();
//         }
//         if (cards && cards.length) {
//             this.wysiwyg.odooEditor.historyStep();
//         }
//     },
//     /**
//      * Update the cards to use the default card campaign for the new model
//      */
//     _updateMarketingCards(newModel, defaultCampaignId) {
//         if (!this.wysiwyg?.odooEditor?.editable || newModel === this.previousModel) {
//             return;
//         }
//         const cards = this.wysiwyg.odooEditor.editable.querySelectorAll(".s_call_to_share_card");
//         for (const card of cards) {
//             const anchor = card.querySelector("a");
//             const img = card.querySelector("img");
//             card.dataset.campaignId = defaultCampaignId;
//             img.src = img.src.replace(
//                 /\/web\/image\/card.campaign\/([0-9]+)\/image_preview/,
//                 `/web/image/card.campaign/${defaultCampaignId}/image_preview`,
//             );
//             anchor.href = anchor.href.replace(
//                 /\/cards\/([0-9]+)\/preview/,
//                 `/cards/${defaultCampaignId}/preview`,
//             );
//         }
//         if (cards && cards.length) {
//             this.wysiwyg.odooEditor.historyStep();
//         }
//     },
//     /**
//      * @override
//      */
//     get wysiwygOptions() {
//         return {
//             massMailingDefaultCardCampaignId: this.defaultCardCampaignId,
//             ...super.wysiwygOptions,
//         };
//     },
// });
