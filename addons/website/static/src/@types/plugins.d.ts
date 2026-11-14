declare module "plugins" {
    import { CarouselOptionPlugin } from "@website/builder/plugins/carousel_option_plugin";
    import { CustomizeWebsitePlugin, on_website_color_updated_handlers } from "@website/builder/plugins/customize_website_plugin";
    import { on_content_manually_updated_handlers, EditInteractionPlugin } from "@website/builder/plugins/edit_interaction_plugin";
    import { floating_snippet_scope_providers, floating_snippets_selectors } from "@website/builder/plugins/floating_snippets_plugin";
    import { WebsiteFontPlugin } from "@website/builder/plugins/font/font_plugin";
    import { FormOptionPlugin } from "@website/builder/plugins/form/form_option_plugin";
    import { ImageHoverPlugin } from "@website/builder/plugins/image/image_hover_plugin";
    import { MenuDataPlugin } from "@website/builder/plugins/menu_data_plugin";
    import { AnimateOptionPlugin, can_have_hover_effect_predicates, on_hover_animation_mode_cleaned_handlers, on_hover_animation_mode_applied_handlers } from "@website/builder/plugins/options/animate_option_plugin";
    import { WebsiteBackgroundVideoPlugin } from "@website/builder/plugins/options/background_option_plugin";
    import { CardImageOptionPlugin } from "@website/builder/plugins/options/card_image_option_plugin";
    import { ChartOptionPlugin } from "@website/builder/plugins/options/chart_option_plugin";
    import { CookiesBarOptionPlugin } from "@website/builder/plugins/options/cookies_bar_option";
    import { DynamicSnippetCarouselOptionPlugin } from "@website/builder/plugins/options/dynamic_snippet_carousel_option_plugin";
    import { on_dynamic_snippet_template_updated_handlers, DynamicSnippetOptionPlugin } from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
    import { footer_templates_providers, FooterOptionPlugin } from "@website/builder/plugins/options/footer_option_plugin";
    import { gallery_items_providers, reorder_items_processors } from "@website/builder/plugins/options/gallery_element_option_plugin";
    import { GoogleMapsOptionPlugin } from "@website/builder/plugins/options/google_maps_option/google_maps_option_plugin";
    import { header_templates_providers, HeaderOptionPlugin } from "@website/builder/plugins/options/header/header_option_plugin";
    import { ImageGalleryOptionPlugin } from "@website/builder/plugins/options/image_gallery_option_plugin";
    import { InstagramOptionPlugin } from "@website/builder/plugins/options/instagram_option_plugin";
    import { MegaMenuOptionShared } from "@website/builder/plugins/options/mega_menu_option_plugin";
    import { NavTabsStyleOptionPlugin } from "@website/builder/plugins/options/navtabs_style_option_plugin";
    import { WebsiteParallaxPlugin } from "@website/builder/plugins/options/parallax_option_plugin";
    import { searchbar_option_order_by_items } from "@website/builder/plugins/options/searchbar_option_plugin";
    import { SocialMediaOptionPlugin } from "@website/builder/plugins/options/social_media_option_plugin";
    import { on_visibility_toggled_handlers, visibility_selector_parameters } from "@website/builder/plugins/options/visibility_option_plugin";
    import { WebsitePageConfigOptionPlugin } from "@website/builder/plugins/options/website_page_config_option_plugin";
    import { PopupVisibilityPlugin } from "@website/builder/plugins/popup_visibility_plugin";
    import { SwitchableViewsPlugin } from "@website/builder/plugins/switchable_views_plugin";
    import { theme_options, ThemeTabPlugin } from "@website/builder/plugins/theme/theme_tab_plugin";
    import { MediaTranslationPlugin } from "@website/builder/plugins/translation/options/media_translation_plugin";
    import { TranslateWebpageOptionPlugin } from "@website/builder/plugins/translation/options/translate_webpage_option_plugin";
    import { on_nodes_marked_translatable_handlers, TranslationPlugin } from "@website/builder/plugins/translation/translation_plugin";
    import { save_element_context_processors } from "@website/builder/plugins/website_save_plugin";
    import { force_background_translation_state_selectors } from "@website/builder/plugins/translation/repeat_translation_state_plugin";
    import { ValueHistoryPlugin } from "@website/builder/plugins/value_history_plugin";
    import { WebsiteBridgePlugin } from "@website/builder/plugins/website_bridge_plugin";

    interface SharedMethods {
        animateOption: SharedOf<typeof AnimateOptionPlugin>;
        carouselOption: SharedOf<typeof CarouselOptionPlugin>;
        cardImageOption: SharedOf<typeof CardImageOptionPlugin>;
        chartOptionPlugin: SharedOf<typeof ChartOptionPlugin>;
        CookiesBarOptionPlugin: SharedOf<typeof CookiesBarOptionPlugin>;
        customizeWebsite: SharedOf<typeof CustomizeWebsitePlugin>;
        dynamicSnippetCarouselOption: SharedOf<typeof DynamicSnippetCarouselOptionPlugin>;
        dynamicSnippetOption: SharedOf<typeof DynamicSnippetOptionPlugin>;
        edit_interaction: SharedOf<typeof EditInteractionPlugin>;
        footerOption: SharedOf<typeof FooterOptionPlugin>;
        googleMapsOption: SharedOf<typeof GoogleMapsOptionPlugin>;
        headerOption: SharedOf<typeof HeaderOptionPlugin>;
        imageGalleryOption: SharedOf<typeof ImageGalleryOptionPlugin>;
        imageHover: SharedOf<typeof ImageHoverPlugin>;
        instagramOption: SharedOf<typeof InstagramOptionPlugin>;
        mediaTranslation: SharedOf<typeof MediaTranslationPlugin>;
        megaMenuOptionPlugin: MegaMenuOptionShared;
        menuDataPlugin: SharedOf<typeof MenuDataPlugin>;
        navTabsOptionStyle: SharedOf<typeof NavTabsStyleOptionPlugin>;
        popupVisibilityPlugin: SharedOf<typeof PopupVisibilityPlugin>;
        socialMediaOptionPlugin: SharedOf<typeof SocialMediaOptionPlugin>;
        switchableViews: SharedOf<typeof SwitchableViewsPlugin>;
        themeTab: SharedOf<typeof ThemeTabPlugin>;
        translateWebpageOption: SharedOf<typeof TranslateWebpageOptionPlugin>;
        translation: SharedOf<typeof TranslationPlugin>;
        valueHistory: SharedOf<typeof ValueHistoryPlugin>;
        websiteBackgroundVideoPlugin: SharedOf<typeof WebsiteBackgroundVideoPlugin>;
        websiteFont: SharedOf<typeof WebsiteFontPlugin>;
        websiteFormOption: SharedOf<typeof FormOptionPlugin>;
        websitePageConfigOptionPlugin: SharedOf<typeof WebsitePageConfigOptionPlugin>;
        websiteParallaxPlugin: SharedOf<typeof WebsiteParallaxPlugin>;
        websiteBridge: SharedOf<typeof WebsiteBridgePlugin>;
    }

    interface GlobalResources extends WebsiteResourcesAccess {}
    export type WebsiteResourcesAccess = BuilderResourcesAccess & ResourcesTypesFactory<WebsiteResourcesList>;
    export type WebsiteResources = ResourcesDeclarationsFactory<WebsiteResourcesAccess>;
    export interface WebsiteResourcesList {
        // Handlers
        on_content_manually_updated_handlers: on_content_manually_updated_handlers;
        on_dynamic_snippet_template_updated_handlers: on_dynamic_snippet_template_updated_handlers;
        on_hover_animation_mode_cleaned_handlers: on_hover_animation_mode_cleaned_handlers;
        on_hover_animation_mode_applied_handlers: on_hover_animation_mode_applied_handlers;
        on_nodes_marked_translatable_handlers: on_nodes_marked_translatable_handlers;
        on_visibility_toggled_handlers: on_visibility_toggled_handlers;
        on_website_color_updated_handlers: on_website_color_updated_handlers;

        // Predicates
        can_have_hover_effect_predicates: can_have_hover_effect_predicates;

        // Processors
        reorder_items_processors: reorder_items_processors;
        save_element_context_processors: save_element_context_processors;

        // Providers
        floating_snippet_scope_providers: floating_snippet_scope_providers;
        footer_templates_providers: footer_templates_providers;
        gallery_items_providers: gallery_items_providers;
        header_templates_providers: header_templates_providers;

        // Data
        searchbar_option_order_by_items: searchbar_option_order_by_items;
        floating_snippets_selectors: floating_snippets_selectors;
        force_background_translation_state_selectors: force_background_translation_state_selectors;
        theme_options: theme_options;
        visibility_selector_parameters: visibility_selector_parameters;
    }
}
