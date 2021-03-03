/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, one2one } from '@mail/model/model_field';

function factory(dependencies) {

    class SelectablePartnersList extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------


        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        _computeSelectablePartners() {
            if(this.isOpened) {
                this.env.models['mail.partner'].imSearch({
                    callback: () => {},
                    keyword: _.escape(this.inputSearch),
                    limit: 10,
                });
                const allOrderedAndPinnedChats = this.env.models['mail.partner']
                    .all()
                    .sort((c1, c2) => c1.displayName < c2.displayName ? -1 : 1);
                const qsVal = this.inputSearch ? this.inputSearch.toLowerCase() : "";
                const lesPartners = allOrderedAndPinnedChats.filter(chat => {
                    const nameVal = chat.nameOrDisplayName.toLowerCase();
                    return nameVal.includes(qsVal);
                });
                return [['replace', lesPartners]];
            }
        }
    }

    SelectablePartnersList.fields = {
        inputSearch: attr({
            default: "",
        }),
        isOpened: attr({
            default: false,
        }),
        messaging: one2one('mail.messaging', {
            inverse: 'selectablePartnersList',
        }),
        selectablePartners: many2many('mail.partner', {
            compute: '_computeSelectablePartners',
            dependencies: [
                'inputSearch',
                'isOpened'
            ],
        }),
    };

    SelectablePartnersList.modelName = 'mail.selectable_partners_list';

    return SelectablePartnersList;
}

registerNewModel('mail.selectable_partners_list', factory);
