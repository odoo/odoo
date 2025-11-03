declare module "services" {
    import { snippetService } from "@html_builder/snippets/snippet_service";

    export interface Services {
        "html_builder.snippets": typeof snippetService;
    }
}
