import { registry } from "@web/core/registry";
import { TeamBoard } from "./team_board";

export const TeamBoardEditMixin = (I) =>
    class extends I {
        setup() {
            super.setup();
            this.dynamicContent = {
                ...this.dynamicContent,
                "[data-bs-toggle='modal']": {
                    // Disable Bootstrap modal auto-trigger in edit mode
                    "t-att-data-bs-toggle": () => false,
                    "t-on-click": (ev) => {
                        ev.preventDefault();
                        ev.stopPropagation();
                    },
                },
            };
        }
    };

registry.category("public.interactions.edit").add("website.team_board", {
    Interaction: TeamBoard,
    mixin: TeamBoardEditMixin,
});
