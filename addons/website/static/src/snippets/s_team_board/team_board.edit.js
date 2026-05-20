import { TeamBoard } from "@website/snippets/s_team_board/team_board";
import { registry } from "@web/core/registry";

const TeamBoardEdit = (I) =>
    class extends I {
        setup() {
            super.setup();
            if (this.modalEl?.classList.contains("show")) {
                this.modalEl.classList.remove("show");
                this.modalEl.style.display = "none";
                this.modalEl.setAttribute("aria-hidden", "true");
                document.body.classList.remove("modal-open");
                document.body.style.removeProperty("overflow");
                document.body.style.removeProperty("padding-right");
                document.querySelectorAll(".modal-backdrop").forEach((el) => el.remove());
            }
        }

        onCardClick() {}
        onCardKeydown() {}
    };

registry.category("public.interactions.edit").add("website.team_board", {
    Interaction: TeamBoard,
    mixin: TeamBoardEdit,
});
