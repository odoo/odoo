import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

// TODO
class HeaderTop extends Interaction {
    static selector = "header#top";
    dynamicContent = {
        "#top_menu_collapse, #top_menu_collapse_mobile": {
            "t-att-class": () => ({
                "o_top_menu_collapse_shown": this.shownCollapse,
            }),
            "t-on-show.bs.offcanvas": this.onCollapseShow,
            "t-on-hidden.bs.offcanvas": this.onCollapseHidden,
        },
    }

    setup() {
        this.mobileNavbarEl = this.el.querySelector("#top_menu_collapse_mobile");
    }

    onCollapseShow() {
        // this.options.wysiwyg?.odooEditor.observerUnactive("addCollapseClass");
        this.shownCollapse = true;
        // this.options.wysiwyg?.odooEditor.observerActive("addCollapseClass");
    }

    onCollapseHidden() {
        // this.options.wysiwyg?.odooEditor.observerUnactive("removeCollapseClass");
        if (!this.mobileNavbarEl.matches(".show, .showing")) {
            this.shownCollapse = false;
        }
        // this.options.wysiwyg?.odooEditor.observerActive("removeCollapseClass");
    }
}

registry
    .category("public.interactions")
    .add("website.header_top", HeaderTop);

registry
    .category("public.interactions.edit")
    .add("website.header_top", {
        Interaction: HeaderTop,
    });
