import { DocumentsCogMenu } from "../views/cog_menu/documents_cog_menu";
import { Breadcrumbs } from "@web/search/breadcrumbs/breadcrumbs";

export class DocumentsBreadcrumbs extends Breadcrumbs {
    static components = {
        ...Breadcrumbs.components,
        DocumentsCogMenu,
    };
    static template = "documents.Breadcrumbs";
}
