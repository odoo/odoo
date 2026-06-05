import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";

export class StretchedColumnsPlugin extends Plugin {
    static id = "stretchedColumns";
    static dependencies = ["spacing", "responsiveBlock", "math", "style"];
    resources = {
        element_layout_analysis_processors: this.addStretchingConstrains.bind(this),
        merge_fact_overrides: this.registerPaddingFacts.bind(this),
        refine_layout_processors: this.addPaddingCells.bind(this),
    };

    setup() {}

    addStretchingConstrains({ layout, analysis }, { referenceNode, parentEmailNode }) {
        // goal:
        // create a constraint function which identifies if a parent/ancestor is eligible
        // to propagate the report, returns a new constraint function based on that ancestor
    }

    registerPaddingFacts({ emailNode, fact, value }) {
        // explode the fact value on the cell and the ancestor table
    }

    addPaddingCells(layout, { emailNode }) {
        // in a stretching table, add synthetic email nodes for
        // padding cells/rows
    }
}

registry
    .category("mail-html-conversion-main-plugins")
    .add(StretchedColumnsPlugin.id, StretchedColumnsPlugin);
