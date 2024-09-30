declare module "models" {
    import { Website as WebsiteClass } from "@website/mail/core/common/website_model";
    import { WebsitePage as WebsitePageClass } from "@website/mail/core/common/website_page_model";
    import { WebsiteTrack as WebsiteTrackClass } from "@website/mail/core/common/website_track_model";
    import { WebsiteVisitor as WebsiteVisitorClass } from "@website/mail/core/common/website_visitor_model";

    export interface Website extends WebsiteClass {}
    export interface WebsitePage extends WebsitePageClass {}
    export interface WebsiteTrack extends WebsiteTrackClass {}
    export interface WebsiteVisitor extends WebsiteVisitorClass {}

    export interface Store {
        website: StaticMailRecord<Website, typeof WebsiteClass>;
        "website.page": StaticMailRecord<WebsitePage, typeof WebsitePageClass>;
        "website.track": StaticMailRecord<WebsiteTrack, typeof WebsiteTrackClass>;
        "website.visitor": StaticMailRecord<WebsiteVisitor, typeof WebsiteVisitorClass>;
    }

    export interface Models {
        "website": Website;
        "website.page": WebsitePage;
        "website.track": WebsiteTrack;
        "website.visitor": WebsiteVisitor;
    }
}
