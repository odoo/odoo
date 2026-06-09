import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { TeamBoardDialog } from "@website/components/team_board_contact_dialog/team_board_contact_dialog";

export class TeamBoard extends Interaction {
    static selector = ".s_team_board";

    dynamicContent = {
        ".card": {
            "t-on-click": this.showDialog,
            "t-on-keydown": this.onKeydown,
        },
    };

    showDialog(event) {
        const card = event.currentTarget;
        const props = {
            img: card.querySelector("img").src,
            content: card.querySelector(".card-body").innerHTML,
        };
        this.services.dialog.add(TeamBoardDialog, props);
    }

    onKeydown(event) {
        const hotkey = getActiveHotkey(event);
        if (hotkey === "enter" || hotkey === "space") {
            event.preventDefault();
            this.showDialog(event);
        }
    }
    destroy() {
        this.services.dialog.closeAll(TeamBoardDialog);
    }
}

registry.category("public.interactions").add("website.team_board", TeamBoard);
