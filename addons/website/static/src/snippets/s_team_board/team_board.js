import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { SendMessageModal } from "./send_message_modal";
import { _t } from "@web/core/l10n/translation";

export class TeamBoard extends Interaction {
    static selector = ".s_team_board";
    
    dynamicContent = {
        ".o_team_board_card": {
            "t-on-click": this._onClickCard,
        }
    };

    setup(){
        this.dialog = useService("dialog");
    }

    destroy() {
        if (this.closeModal){
            this.closeModal();
        }
    }


    _onClickCard(ev) {
        const card = ev.target.closest('.o_team_board_card');
        if (!card) return;
        
        const data = {
            name: card.querySelector('.card-title')?.textContent.trim(),
            function: card.querySelector('.card-subtitle.text-secondary')?.textContent.trim(),
            description: card.querySelector('.card-text:not(.text-secondary)')?.textContent.trim(),
            picture: card.querySelector('img.o_card_img')?.getAttribute('src'),
        };
        this.closeModal = this.dialog.add(SendMessageModal, {
            name : data.name,
            role: data.function,
            description: data.description,
            photo: data.picture,
        });
    }
}

registry.category("public.interactions").add("website.team_board", TeamBoard);
