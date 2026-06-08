declare module "services" {
    import { websiteCookiesService } from "@website/core/website_cookies_service";
    import { websiteEditService } from "@website/core/website_edit_service";
    import { websiteMapService } from "@website/core/website_map_service";
    import { websiteMenusService } from "@website/core/website_menus_service";
    import { websitePageService } from "@website/core/website_page_service";
    import { websiteCustomMenus } from "@website/services/website_custom_menus";
    import { websiteService } from "@website/services/website_service";

    export interface Services {
        website: typeof websiteService;
        website_cookies: typeof websiteCookiesService;
        website_custom_menus: typeof websiteCustomMenus;
        website_edit: typeof websiteEditService;
        website_map: typeof websiteMapService;
        website_menus: typeof websiteMenusService;
        website_page: typeof websitePageService;
    }
}
