import { registry } from '@web/core/registry';

registry.category('website_custom_menus').add('website_links.menu_link_tracker', {
    openWidget: (services) => services.website.goToWebsite({ path: `/r?u=${encodeURIComponent(services.website.contentWindow.location.href)}` }),
    isDisplayed: (env) => env.services.website.currentWebsite && env.services.website.contentWindow,
});
