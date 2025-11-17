declare module "plugins" {
    import { CarouselOptionShared } from "@website/builder/plugins/carousel_option_plugin";
    import { CustomizeWebsiteShared } from "@website/builder/plugins/customize_website_plugin";
    import { content_manually_updated_handlers, EditInteractionShared } from "@website/builder/plugins/edit_interaction_plugin";
    import { WebsiteFontShared } from "@website/builder/plugins/font/font_plugin";
    import { FormOptionShared } from "@website/builder/plugins/form/form_option_plugin";
    import { ImageHoverShared } from "@website/builder/plugins/image/image_hover_plugin";
    import { AddElementOptionShared } from "@website/builder/plugins/layout_option/add_element_option_plugin";
    import { MenuDataShared } from "@website/builder/plugins/menu_data_plugin";
    import { hover_effect_allowed_predicates } from "@website/builder/plugins/options/animate_option";
    import { AnimateOptionShared, remove_hover_effect_handlers, set_hover_effect_handlers } from "@website/builder/plugins/options/animate_option_plugin";
    import { WebsiteBackgroundVideoShared } from "@website/builder/plugins/options/background_option_plugin";
    import { CardImageOptionShared } from "@website/builder/plugins/options/card_image_option_plugin";
    import { ChartOptionShared } from "@website/builder/plugins/options/chart_option_plugin";
    import { CookiesBarOptionShared } from "@website/builder/plugins/options/cookies_bar_option";
    import { DynamicSnippetCarouselOptionShared } from "@website/builder/plugins/options/dynamic_snippet_carousel_option_plugin";
    import { dynamic_snippet_template_updated, DynamicSnippetOptionShared } from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
    import { footer_templates_providers, FooterOptionShared } from "@website/builder/plugins/options/footer_option_plugin";
    import { get_gallery_items_handlers, reorder_items_handlers } from "@website/builder/plugins/options/gallery_element_option_plugin";
    import { GoogleMapsOptionShared } from "@website/builder/plugins/options/google_maps_option/google_maps_option_plugin";
    import { ImageGalleryOptionShared } from "@website/builder/plugins/options/image_gallery_option_plugin";
    import { InstagramOptionShared } from "@website/builder/plugins/options/instagram_option_plugin";
    import { MegaMenuOptionShared } from "@website/builder/plugins/options/mega_menu_option_plugin";
    import { NavTabsStyleOptionShared } from "@website/builder/plugins/options/navtabs_style_option_plugin";
    import { WebsiteParallaxShared } from "@website/builder/plugins/options/parallax_option_plugin";
    import { searchbar_option_display_items, searchbar_option_order_by_items } from "@website/builder/plugins/options/searchbar_option_plugin";
    import { SocialMediaOptionShared } from "@website/builder/plugins/options/social_media_option_plugin";
    import { visibility_selector_parameters } from "@website/builder/plugins/options/visibility_option_plugin";
    import { WebsitePageConfigOptionShared } from "@website/builder/plugins/options/website_page_config_option_plugin";
    import { PopupVisibilityShared } from "@website/builder/plugins/popup_visibility_plugin";
    import { SwitchableViewsShared } from "@website/builder/plugins/switchable_views_plugin";
    import { theme_options, ThemeTabShared } from "@website/builder/plugins/theme/theme_tab_plugin";
    import { mark_translatable_nodes } from "@website/builder/plugins/translation_plugin";
    import { translate_options } from "@html_builder/core/builder_options_plugin_translate";
    import { WebsiteSessionShared } from "@website/builder/plugins/website_session_plugin";

    interface SharedMethods {
        addElementOption: AddElementOptionShared;
        animateOption: AnimateOptionShared;
        carouselOption: CarouselOptionShared;
        cardImageOption: CardImageOptionShared;
        chartOptionPlugin: ChartOptionShared;
        CookiesBarOptionPlugin: CookiesBarOptionShared;
        customizeTranslationTab: CustomizeTranslationTabShared;
        customizeWebsite: CustomizeWebsiteShared;
        dynamicSnippetCarouselOption: DynamicSnippetCarouselOptionShared;
        dynamicSnippetOption: DynamicSnippetOptionShared;
        edit_interaction: EditInteractionShared;
        footerOption: FooterOptionShared;
        googleMapsOption: GoogleMapsOptionShared;
        imageGalleryOption: ImageGalleryOptionShared;
        imageHover: ImageHoverShared;
        instagramOption: InstagramOptionShared;
        megaMenuOptionPlugin: MegaMenuOptionShared;
        menuDataPlugin: MenuDataShared;
        navTabsOptionStyle: NavTabsStyleOptionShared;
        popupVisibilityPlugin: PopupVisibilityShared;
        socialMediaOptionPlugin: SocialMediaOptionShared;
        switchableViews: SwitchableViewsShared;
        themeTab: ThemeTabShared;
        websiteBackgroundVideoPlugin: WebsiteBackgroundVideoShared;
        websiteFont: WebsiteFontShared;
        websiteFormOption: FormOptionShared;
        websitePageConfigOptionPlugin: WebsitePageConfigOptionShared;
        websiteParallaxPlugin: WebsiteParallaxShared;
        websiteSession: WebsiteSessionShared;
    }

    interface GlobalResources extends WebsiteResourcesAccess {}
    export type WebsiteResourcesAccess = BuilderResourcesAccess & ResourcesTypesFactory<WebsiteResourcesList>;
    export type WebsiteResources = ResourcesDeclarationsFactory<WebsiteResourcesAccess>;
    export interface WebsiteResourcesList {
        // Handlers
        content_manually_updated_handlers: content_manually_updated_handlers;
        dynamic_snippet_template_updated: dynamic_snippet_template_updated;
        get_gallery_items_handlers: get_gallery_items_handlers;
        mark_translatable_nodes: mark_translatable_nodes;
        remove_hover_effect_handlers: remove_hover_effect_handlers;
        reorder_items_handlers: reorder_items_handlers;
        set_hover_effect_handlers: set_hover_effect_handlers;

        // Overrides

        // Predicates
        hover_effect_allowed_predicates: hover_effect_allowed_predicates;

        // Processors

        // Providers
        footer_templates_providers: footer_templates_providers;

        // Data
        searchbar_option_display_items: searchbar_option_display_items;
        searchbar_option_order_by_items: searchbar_option_order_by_items;
        theme_options: theme_options;
        translate_options: translate_options;
        visibility_selector_parameters: visibility_selector_parameters;
    }
}
