// import { patch } from "@web/core/utils/patch";

// import { MassMailingWysiwyg } from "@mass_mailing/js/mass_mailing_wysiwyg";

// patch(MassMailingWysiwyg.prototype, {
//     setup() {
//         this._massMailingDefaultCampaignId = this.props.options.massMailingDefaultCardCampaignId || 0;
//         this._updateDefaultCardCampaignCallbacks = new Set();
//         return super.setup();
//     },
//     /**
//      * subscription system to pass data to the menu as it's not accessible directly
//      * @param {async function} campaignUpdateCallback
//      * @returns an unsubscribe function to remove the callback
//      */
//     _subscribeUpdateDefaultCardCampaign(campaignUpdateCallback) {
//         this._updateDefaultCardCampaignCallbacks.add(campaignUpdateCallback);
//         return () => this._updateDefaultCardCampaignCallbacks.delete(campaignUpdateCallback);
//     },
//     _notifyUpdateDefaultCardCampaign(cardCampaignId) {
//         this._massMailingDefaultCampaignId = cardCampaignId;
//         for (const updateCallback of this._updateDefaultCardCampaignCallbacks) {
//             updateCallback(cardCampaignId);
//         }
//     },
//     /**
//      * @override
//      */
//     get snippetsMenuOptions() {
//         return {
//             originalDefaultCampaignId: this._massMailingDefaultCampaignId,
//             ...super.snippetsMenuOptions,
//         };
//     },
// });
