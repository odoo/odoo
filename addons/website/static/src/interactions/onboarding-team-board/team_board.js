import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class TeamBoard extends Interaction {
    static selector = ".s_team_board";
    dynamicContent = {
        ".s_team_board_member_button": {
            "t-on-click": this.onMemberClick,
        },
    };

    onMemberClick(ev) {
        const memberEl = ev.currentTarget.closest(".s_team_board_member");
        if (!memberEl) {
            return;
        }
        const [modalEl] = this.renderAt("website.s_team_board.modal", {}, document.body);
        const payload = {
            member: this.getMemberData(memberEl),
            memberEl,
            modalEl,
        };

        // The use of env.bus async communication between the TeamBoard and
        // TeamBoardModal interactions is most probably overkill/complicated for
        // this use case, but it's a good example of how to use it anyway
        this.waitForAnimationFrame(() => {
            this.env.bus.trigger("WEBSITE:TEAM_BOARD:MODAL:SHOW", payload);
        });
    }

    getMemberData(memberEl) {
        const imageEl = memberEl.querySelector("img");
        const name = memberEl.querySelector(".card-title")?.textContent?.trim() || "";

        return {
            memberId: memberEl.dataset.memberId || null,
            name: name,
            role: memberEl.querySelector(".text-muted")?.textContent?.trim() || "",
            bio: memberEl.querySelector(".card-text")?.textContent?.trim() || "",
            imageSrc: imageEl?.getAttribute("src") || "",
            imageAlt: imageEl?.getAttribute("alt") || name,
        };
    }
}

registry.category("public.interactions").add("website.team_board", TeamBoard);
