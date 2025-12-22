declare module "mock_models" {
    import { Website as Website2 } from "../website";
    import { WebsiteVisitor as WebsiteVisitor2 } from "../website_visitor";

    export interface Website extends Website2 {}
    export interface WebsiteVisitor extends WebsiteVisitor2 {}

    export interface Models {
        "website": Website,
        "website.visitor": WebsiteVisitor,
    }
}
