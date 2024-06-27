import { SelectMenu } from "@web/core/select_menu/select_menu";

export class SelectMenuForum extends SelectMenu {
    get multiSelectChoices() {
        [...this.props.choices, ...this.props.groups.flatMap((g) => g.choices)].map((c) => {
            if (c.id === "new") {
                c.label = c.name;
            }
        });
        return super.multiSelectChoices;
    }
}
