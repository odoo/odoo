declare module "models" {
    import { Website as WebsiteClass } from "@website/common/website_model";
    import { WebsiteVisitor as WebsiteVisitorClass } from "@website/common/website_visitor_model";

    export interface Website extends WebsiteClass {}
    export interface WebsiteVisitor extends WebsiteVisitorClass {}

    export interface Store {
        website: StaticMailRecord<Website, typeof WebsiteClass>;
        "website.visitor": StaticMailRecord<WebsiteVisitor, typeof WebsiteVisitorClass>;
    }

    export interface Models {
        "website": Website;
        "website.visitor": WebsiteVisitor;
    }
}
