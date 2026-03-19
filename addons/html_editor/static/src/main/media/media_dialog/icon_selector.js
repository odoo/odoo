import { SearchMedia } from "./search_media";
import { fonts } from "@html_editor/utils/fonts";
import { _t } from "@web/core/l10n/translation";
import { MS_ICONS_BY_CATEGORY, MS_CATEGORY_LABELS } from "./material_symbols_icons";

import { Component, proxy } from "@odoo/owl";

/**
 * Custom Odoo UI icons (oi font, not Material Symbols).
 * These are rendered as: <span class="oi" data-icon="oi_<name>">
 *
 * Sourced from the $custom_oi_icons SCSS map in web/static/src/webclient/icons.scss.
 */
const OI_ICONS = {
    Brands: [
        "threads", "kickstarter", "x", "twitter", "x-square", "twitter-square", "tiktok",
        "bluesky", "google-play", "strava", "discord", "amazon", "angellist", "bandcamp",
        "binoculars", "bitbucket-square", "bitbucket", "black-tie", "bomb", "buysellads",
        "cc-amex", "github-square", "500px", "adn", "android", "apple", "behance-square",
        "behance", "birthday-cake", "chrome", "codepen", "codiepie", "connectdevelop",
        "contao", "creative-commons", "css3", "delicious", "deviantart", "digg", "dribbble",
        "dropbox", "drupal", "edge", "eercast", "empire", "envira", "etsy", "expeditedssl",
        "fa", "facebook-official", "facebook-square", "facebook", "firefox", "first-order",
        "flickr", "fonticons", "fort-awesome", "forumbee", "foursquare", "free-code-camp",
        "get-pocket", "gg-circle", "gg", "git-square", "git", "github-alt", "github",
        "gitlab", "gittip", "glide-g", "glide", "google-plus-circle", "google-plus-square",
        "google-plus", "google-wallet", "google", "grav", "hacker-news", "hand-lizard-o",
        "hand-peace-o", "hand-scissors-o", "hand-spock-o", "houzz", "html5", "imdb",
        "instagram", "internet-explorer", "ioxhost", "joomla", "jsfiddle", "lastfm-square",
        "lastfm", "leanpub", "lemon-o", "linkedin-square", "linkedin", "linode", "linux",
        "magnet", "maxcdn", "meanpath", "medium", "meetup", "mercury", "mixcloud", "modx",
        "neuter", "odnoklassniki-square", "odnoklassniki", "opencart", "openid", "opera",
        "optin-monster", "pagelines", "paypal", "pied-piper-alt", "pied-piper-pp",
        "pied-piper", "pinterest-p", "pinterest-square", "pinterest", "product-hunt", "qq",
        "quora", "ra", "ravelry", "reddit-alien", "reddit-square", "reddit", "renren",
        "safari", "scribd", "sellsy", "shirtsinbulk", "simplybuilt", "skyatlas", "skype",
        "slack", "slideshare", "snapchat-ghost", "snapchat-square", "snapchat", "soundcloud",
        "spotify", "stack-exchange", "stack-overflow", "steam-square", "steam",
        "stumbleupon-circle", "stumbleupon", "superpowers", "telegram", "tencent-weibo",
        "themeisle", "trademark", "trello", "tripadvisor", "tumblr-square", "tumblr",
        "twitch", "user-secret", "viacoin", "viadeo-square", "viadeo", "vimeo-square",
        "vimeo", "vine", "vk", "wechat", "whatsapp", "wikipedia-w", "windows", "wordpress",
        "wpbeginner", "wpexplorer", "wpforms", "xing-square", "xing", "y-combinator",
        "yahoo", "yelp", "youtube-play", "youtube-square", "youtube", "cc-diners-club",
        "cc-stripe", "cc-visa", "cc-jcb", "dashcube", "cc-mastercard", "cc-discover",
    ],
    Views: ["view-pivot", "view-cohort", "studio"],
    Misc: [
        "odoo", "mars-double", "mars-stroke-h", "mars-stroke-v", "mars-stroke",
        "venus-double", "venus-mars",
    ],
};

export class IconSelector extends Component {
    static mediaSpecificClasses = ["oi"];
    static mediaSpecificStyles = ["color", "background-color"];
    static mediaExtraClasses = [/^text-\S+$/, /^bg-\S+$/, /^fa-\S+$/];
    static tagNames = ["SPAN", "I"];
    static template = "html_editor.IconSelector";
    static components = {
        SearchMedia,
    };
    static props = ["*"];

    setup() {
        // Pre-populate filled state when editing an existing filled icon
        const filled = this.props.media?.classList.contains("oi-filled") ?? false;
        this.state = proxy({
            categories: this.props.categories,
            needle: "",
            selectedCategory: "",
            filled,
        });
    }

    get selectedMediaIds() {
        return this.props.selectedMedia[this.props.id].map(({ id }) => id);
    }

    /**
     * Applies the current text needle and selected category as combined filters.
     * If the needle matches a category label, all icons in that category are shown
     * regardless of individual icon search terms.
     */
    applyFilters() {
        const lower = this.state.needle.toLowerCase();
        const catId = this.state.selectedCategory;

        this.state.categories = this.props.categories
            .filter((category) => !catId || category.id === catId)
            .map((category) => {
                if (!lower) {
                    return category;
                }
                // Full category match: show all icons when the label contains the needle
                if (category.label.toLowerCase().includes(lower)) {
                    return category;
                }
                // Partial match: filter icons individually by name and tags
                return {
                    ...category,
                    icons: category.icons.filter((icon) =>
                        icon.searchTerms.includes(lower)
                    ),
                };
            });
    }

    search(needle) {
        this.state.needle = needle;
        this.applyFilters();
    }

    onCategoryChange(ev) {
        this.state.selectedCategory = ev.target.value;
        this.applyFilters();
    }

    /**
     * Determines whether the icon being selected differs from the current media element.
     * For MS/OI icons this compares the data-icon attribute and filled state;
     * for FA icons it compares class names.
     *
     * @param {Object} icon
     * @returns {boolean}
     */
    iconHasChanged(icon) {
        if (!this.props.media) {
            return false;
        }
        if (icon.source === "fa") {
            return !icon.names.some((name) => this.props.media.classList.contains(name));
        }
        // Material Symbols and Odoo UI icons: compare data-icon and filled state
        const dataIconChanged = this.props.media.dataset.icon !== icon.dataIcon;
        const filledChanged =
            this.props.media.classList.contains("oi-filled") !== this.state.filled;
        return dataIconChanged || filledChanged;
    }

    async onClickIcon(category, icon) {
        this.props.selectMedia({
            ...icon,
            filled: this.state.filled,
            initialIconChanged: this.iconHasChanged(icon),
        });
        await this.props.save();
    }

    /**
     * Utility methods, used by the MediaDialog component.
     */
    static createElements(selectedMedia) {
        return selectedMedia.map((icon) => {
            const iconEl = document.createElement("span");
            if (icon.source === "fa") {
                // Legacy FontAwesome: icon is identified by CSS classes
                iconEl.classList.add(icon.fontBase, icon.names[0]);
            } else {
                // Material Symbols and Odoo UI icons: icon is identified by data-icon attribute
                iconEl.classList.add("oi");
                if (icon.filled) {
                    iconEl.classList.add("oi-filled");
                }
                iconEl.dataset.icon = icon.dataIcon;
            }
            return iconEl;
        });
    }

    /**
     * Builds the full list of icon categories for the picker, merging:
     *   1. Material Symbols (from the bundled icons data module)
     *   2. Odoo UI custom icons (brands, views, misc)
     *   3. Legacy FontAwesome icons (CSS-parsed, kept for retro-compatibility)
     *
     * @returns {Array.<{id: string, label: string, source: string, base: string, icons: Array}>}
     */
    static initFonts() {
        // 1. Material Symbols — one category object per Google Fonts category
        const msCategories = Object.keys(MS_ICONS_BY_CATEGORY)
            .sort()
            .map((catId) => ({
                id: `ms_${catId}`,
                label: MS_CATEGORY_LABELS[catId] || catId,
                source: "ms",
                base: "oi",
                icons: MS_ICONS_BY_CATEGORY[catId].map((icon) => ({
                    id: `ms_${icon.name}`,
                    name: icon.name,
                    dataIcon: icon.name,
                    // tags is a space-separated string for efficient substring search
                    searchTerms: `${icon.name} ${icon.tags}`.toLowerCase(),
                    source: "ms",
                })),
            }));

        // 2. Odoo UI custom icons (oi font) — brands, views, and misc
        const oiCategories = Object.entries(OI_ICONS).map(([label, names]) => ({
            id: `oi_${label.toLowerCase()}`,
            label: `Odoo - ${label}`,
            source: "oi",
            base: "oi",
            icons: names.map((name) => ({
                id: `oi_${name}`,
                name,
                dataIcon: `oi_${name}`,
                searchTerms: name.toLowerCase().replace(/-/g, " "),
                source: "oi",
            })),
        }));

        // 3. Legacy FontAwesome — CSS-parsed, same logic as before
        fonts.computeFonts();
        const faCategories = fonts.fontIcons.map(({ cssData, base }) => {
            const uniqueIcons = Array.from(
                new Map(
                    cssData.map((icon) => {
                        const alias = icon.names.join(",");
                        const id = `${base}_${alias}`;
                        const searchTerms = alias
                            .replace(/fa-/g, "")
                            .replace(/,/g, " ")
                            .toLowerCase();
                        return [
                            id,
                            { ...icon, alias, id, searchTerms, source: "fa", fontBase: base },
                        ];
                    })
                ).values()
            );
            return {
                id: `fa_${base}`,
                label: _t("Legacy (FontAwesome)"),
                source: "fa",
                base,
                icons: uniqueIcons,
            };
        });

        return [...msCategories, ...oiCategories, ...faCategories];
    }
}
