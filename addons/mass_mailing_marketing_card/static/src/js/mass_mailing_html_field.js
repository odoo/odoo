/** @odoo-module **/

import { MassMailingHtmlField } from "@mass_mailing/js/mass_mailing_html_field";
import { patch } from "@web/core/utils/patch";

patch(MassMailingHtmlField.prototype, {
    setup() {
        super.setup();
        this.previousModel = this.props.record.data.mailing_model_real;
    },
    commitChanges() {
        const editor = this.wysiwyg?.odooEditor;
        if (editor) {
            const cards = editor.editable.querySelectorAll(".s_call_to_share_card");
            for (const card of cards) {
                if (!card.dataset.campaignId) {
                    card.remove();
                }
            }
            editor.historyStep();
        }
        return super.commitChanges(...arguments);
    },
    _onModelChange(record) {
        super._onModelChange(record);
        this._removeMarketingCards(record);
        this.previousModel = record.data.mailing_model_real;
    },
    /**
     * Clean up all cards as they will likely all have invalid campaigns.
     */
    _removeMarketingCards(record) {
        if (!this.wysiwyg || record.data.mailing_model_real === this.previousModel) {
            return;
        }
        const cards = this.wysiwyg.odooEditor.editable.querySelectorAll(".s_call_to_share_card");
        for (const card of cards) {
            card.remove();
        }
        this.wysiwyg.odooEditor.historyStep();
    },
});
