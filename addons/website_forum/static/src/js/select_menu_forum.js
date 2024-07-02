import { SelectMenu } from "@web/core/select_menu/select_menu";

// TODO: MSH: Removing tag not removing value from hidden element
// TODO: MSH: Create label is not coming in suggestion
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
