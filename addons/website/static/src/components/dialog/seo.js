import { _t } from "@web/core/l10n/translation";
import { pyToJsLocale, jsToPyLocale } from "@web/core/l10n/utils";
import { rpc } from "@web/core/network/rpc";
import { escapeRegExp } from "@web/core/utils/strings";
import { useService, useAutofocus } from '@web/core/utils/hooks';
import { MediaDialog } from '@web_editor/components/media_dialog/media_dialog';
import { WebsiteDialog } from './dialog';
import { Component, useState, reactive, onMounted, onWillStart, useEffect } from "@odoo/owl";

// This replaces \b, because accents(e.g. à, é) are not seen as word boundaries.
// Javascript \b is not unicode aware, and words beginning or ending by accents won't match \b
const WORD_SEPARATORS_REGEX = '([\\u2000-\\u206F\\u2E00-\\u2E7F\'!"#\\$%&\\(\\)\\*\\+,\\-\\.\\/:;<=>\\?¿¡@\\[\\]\\^_`\\{\\|\\}~\\s]+|^|$)';

const seoContext = reactive({
    description: '',
    keywords: [],
    title: '',
    seoName: '',
    metaImage: '',
    defaultTitle: '',
});

class MetaImage extends Component {
    static template = "website.MetaImage";
    static props = ["active", "src", "custom", "selectImage"];
}

class ImageSelector extends Component {
    static template = "website.ImageSelector";
    static components = {
        MetaImage,
    };
    static props = {
        previewDescription: String,
        defaultTitle: String,
        hasSocialDefaultImage: Boolean,
        pageImages: Array,
        url: String,
    };

    setup() {
        this.website = useService('website');
        this.dialogs = useService('dialog');

        this.seoContext = useState(seoContext);

        const firstImageId = this.props.hasSocialDefaultImage ? 'social_default_image' : 'logo';
        const firstImageSrc = `/web/image/website/${encodeURIComponent(this.website.currentWebsite.id)}/${firstImageId}`;
        const firstImage = {
            src: firstImageSrc,
            active: this.areSameImages(firstImageSrc, this.seoContext.metaImage),
            custom: false,
        };

        this.state = useState({
            images: [
                firstImage,
                ...this.props.pageImages.map((src) => {
                    return {
                        src,
                        active: this.areSameImages(src, this.seoContext.metaImage),
                        custom: false,
                    };
                }),
            ],
        });

        if (this.seoContext.metaImage && !this.state.images.map(({src}) => this.getImagePathname(src)).includes(this.getImagePathname(this.seoContext.metaImage))) {
            this.state.images.push({
                src: this.seoContext.metaImage,
                active: true,
                custom: true,
            });
        }

        if (!this.activeMetaImage) {
            this.selectImage(this.state.images[0].src);
        }
    }

    get title() {
        return this.seoContext.title || this.props.defaultTitle;
    }

    get description() {
        return this.seoContext.description || this.props.previewDescription;
    }

    get activeMetaImage() {
        const activeImage = this.state.images.find(({active}) => active);
        return activeImage && activeImage.src;
    }

    getImagePathname(src) {
        return new URL(src, this.website.pageDocument.location.origin).pathname;
    }

    areSameImages(src1, src2) {
        return this.getImagePathname(src1) === this.getImagePathname(src2);
    }

    selectImage(src) {
        this.state.images = this.state.images.map(img => {
            img.active = img.src === src;
            return img;
        });
        this.seoContext.metaImage = src;
    }

    openMediaDialog() {
        this.dialogs.add(MediaDialog, {
            // onlyImages: true,
            resModel: 'ir.ui.view',
            useMediaLibrary: true,
            save: image => {
                let existingImage;
                this.state.images = this.state.images.map(img => {
                    img.active = false;
                    if (img.src === image.src) {
                        existingImage = img;
                        img.active = true;
                    }
                    return img;
                });
                if (!existingImage) {
                    this.state.images.push({
                        src: image.src,
                        active: true,
                        custom: true,
                    });
                }
                this.seoContext.metaImage = image.src;
            },
        });
    }
}

class Keyword extends Component {
    static template = "website.Keyword";
    static props = {
        language: String,
        keyword: String,
        addKeyword: Function,
        removeKeyword: Function,
    };

    setup() {
        this.website = useService('website');

        this.seoContext = useState(seoContext);

        this.state = useState({
            suggestions: [],
        });

        onMounted(async () => {
            const suggestions = await rpc('/website/seo_suggest', {
                lang: jsToPyLocale(this.props.language),
                keywords: this.props.keyword,
            });
            const regex = new RegExp(
                WORD_SEPARATORS_REGEX + escapeRegExp(this.props.keyword) + WORD_SEPARATORS_REGEX,
                "gi"
            );
            this.state.suggestions = [...new Set(JSON.parse(suggestions).map(word => word.replace(regex, '').trim()))];
        });
    }

    isKeywordIn(string) {
        return new RegExp(
            WORD_SEPARATORS_REGEX + escapeRegExp(this.props.keyword) + WORD_SEPARATORS_REGEX,
            "gi"
        ).test(string);
    }

    getHeaders(tag) {
        return Array.from(this.website.pageDocument.documentElement.querySelectorAll(`#wrap ${tag}`)).map(header => header.textContent);
    }

    getBodyText() {
        return this.website.pageDocument.body.textContent;
    }

    get usedInH1() {
        return this.isKeywordIn(this.getHeaders('h1'));
    }

    get usedInH2() {
        return this.isKeywordIn(this.getHeaders('h2'));
    }

    get usedInTitle() {
        return this.isKeywordIn(this.seoContext.title || this.seoContext.defaultTitle);
    }

    get usedInDescription() {
        return this.isKeywordIn(this.seoContext.description);
    }

    get usedInContent() {
        return this.isKeywordIn(this.getBodyText());
    }
}

class MetaKeywords extends Component {
    static template = "website.MetaKeywords";
    static components = {
        Keyword,
    };
    static props = {};

    setup() {
        this.website = useService('website');

        this.seoContext = useState(seoContext);

        this.state = useState({
            language: '',
            keyword: '',
        });

        this.maxKeywords = 10;

        onWillStart(async () => {
            this.languages = await rpc('/website/get_languages');
            this.state.language = this.getLanguage();
        });
    }

    onKeyup(ev) {
        // Add keyword on enter.
        if (ev.key === "Enter") {
            this.addKeyword(this.state.keyword);
        }
    }

    getLanguage() {
        return (
            pyToJsLocale(this.website.pageDocument.documentElement.getAttribute("lang")) || "en-US"
        );
    }

    get isFull() {
        return this.seoContext.keywords.length >= this.maxKeywords;
    }

    addKeyword(keyword) {
        keyword = keyword.replaceAll(/,\s*/gi, " ").trim();
        if (keyword && !this.isFull && !this.seoContext.keywords.includes(keyword)) {
            this.seoContext.keywords.push(keyword);
            this.state.keyword = '';
        }
    }

    removeKeyword(keyword) {
        this.seoContext.keywords = this.seoContext.keywords.filter(kw => kw !== keyword);
    }
}

class SEOPreview extends Component {
    static template = "website.SEOPreview";
    static props = {
        isIndexed: Boolean,
        title: String,
        description: String,
        url: String,
    };

    get description() {
        if (this.props.description?.length > 160) {
            return this.props.description.substring(0, 159) + '…';
        }
        return this.props.description || "";
    }
}
class TitleDescription extends Component {
    static template = "website.TitleDescription";
    static props = {
        canEditDescription: Boolean,
        canEditUrl: Boolean,
        canEditTitle: Boolean,
        seoNameHelp: String,
        seoNameDefault: { optional: true, String },
        isIndexed: Boolean,
        defaultTitle: String,
        previewDescription: String,
        url: String,
    };
    static components = {
        SEOPreview,
    };

    setup() {
        this.seoContext = useState(seoContext);
        useAutofocus();

        this.previousSeoName = this.seoContext.seoName;

        this.maxRecommendedDescriptionSize = 300;
        this.minRecommendedDescriptionSize = 50;

        // Update the title when its input value changes
        useEffect(() => {
            document.title = this.title;
        }, () => [this.seoContext.title]);

        // Restore the original title when unmounting the component
        useEffect(() => {
            const initialTitle = document.title;
            return () => document.title = initialTitle;
        }, () => []);
    }

    //--------------------------------------------------------------------------
    // Getters
    //--------------------------------------------------------------------------

    get seoNameUrl() {
        return this.previousSeoName || this.props.seoNameDefault;
    }

    get seoNamePre() {
        return this.pathname.split(this.seoNameUrl)[0];
    }

    get seoNamePost() {
        return this.pathname.split(this.seoNameUrl).slice(-1)[0]; // at least the -id theorically
    }

    get pathname() {
        return new URL(this.props.url).pathname;
    }

    get url() {
        if (this.seoContext.seoName) {
            return this.props.url.replace(this.seoNameUrl, this.seoContext.seoName);
        }
        return this.props.url.replace(this.seoNameUrl, this.props.seoNameDefault);
    }

    get title() {
        return this.seoContext.title || this.props.defaultTitle;
    }

    get description() {
        return this.seoContext.description || this.props.previewDescription;
    }

    get descriptionWarning() {
        if (!this.seoContext.description) {
            return false;
        }
        if (this.seoContext.description.length < this.minRecommendedDescriptionSize) {
            return _t("Your description looks too short.");
        } else if (this.seoContext.description.length > this.maxRecommendedDescriptionSize) {
            return _t("Your description looks too long.");
        }
        return false;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {InputEvent} ev
     */
    _updateInputValue(ev) {
        // `NFKD` as in `http_routing` python `slugify()`
        ev.target.value = ev.target.value.trim().normalize('NFKD').toLowerCase()
            .replace(/\s+/g, '-') // Replace spaces with -
            .replace(/[^\w-]+/g, '') // Remove all non-word chars
            .replace(/--+/g, '-'); // Replace multiple - with single -
        this.seoContext.seoName = ev.target.value;
    }
}

export class OptimizeSEODialog extends Component {
    static template = "website.OptimizeSEODialog";
    static components = {
        WebsiteDialog,
        TitleDescription,
        ImageSelector,
        MetaKeywords,
    };
    static props = {
        close: Function,
    };

    setup() {
        this.website = useService('website');
        this.dialogs = useService('dialog');
        this.orm = useService('orm');

        this.title = _t("Optimize SEO");
        this.saveButton = _t("Save");
        this.size = 'lg';
        this.contentClass = "oe_seo_configuration";

        onWillStart(async () => {
            const { metadata: { mainObject, seoObject, path } } = this.website.currentWebsite;

            this.object = seoObject || mainObject;
            this.data = await rpc('/website/get_seo_data', {
                'res_id': this.object.id,
                'res_model': this.object.model,
            });

            this.canEditSeo = this.data.can_edit_seo;
            this.canEditDescription = this.canEditSeo && 'website_meta_description' in this.data;
            this.canEditTitle = this.canEditSeo && 'website_meta_title' in this.data;
            this.canEditUrl = this.canEditSeo && 'seo_name' in this.data;
            seoContext.title = this.canEditTitle && this.data.website_meta_title;

            // If website.page, hide the google preview & tell user his page is currently unindexed
            this.isIndexed = 'website_indexed' in this.data ? this.data.website_indexed : true;
            this.seoNameHelp = _t("This value will be escaped to be compliant with all major browsers and used in url. Keep it empty to use the default name of the record.");
            this.previousSeoName = this.canEditUrl && this.data.seo_name;
            seoContext.seoName = this.previousSeoName;
            this.seoNameDefault = this.canEditUrl && this.data.seo_name_default;

            seoContext.description = this.getMeta({ name: 'description' });
            this.previewDescription = _t("The description will be generated by search engines based on page content unless you specify one.");
            this.defaultTitle = this.getMeta({ name: 'default_title' });
            seoContext.defaultTitle = this.defaultTitle;
            this.url = path;

            seoContext.metaImage = this.data.website_meta_og_img || this.getMeta({ property: 'og:image' });

            this.pageImages = this.getImages();
            this.socialPreviewDescription = _t("The description will be generated by social media based on page content unless you specify one.");
            this.hasSocialDefaultImage = this.data.has_social_default_image;

            this.canEditKeywords = 'website_meta_keywords' in this.data;
            seoContext.keywords = this.getMeta({ name: 'keywords' });
        });
    }

    get pageDocumentElement() {
        return this.website.pageDocument.documentElement;
    }

    getImages() {
        const imageEls = this.pageDocumentElement.querySelectorAll('#wrap img');
        return [...new Set(Array.from(imageEls)
                .filter(img => img.naturalHeight > 200 && img.naturalWidth > 200)
                .map(({src}) => (src))
            )];
    }

    getMeta({ name, property }) {
        let query = '';
        if (name) {
            query = `meta[name="${name}"]`;
        }
        if (property) {
            query = `meta[property="${property}"]`;
        }
        const el = this.pageDocumentElement.querySelector(query);
        if (name === 'keywords') {
            // Keywords might contain spaces which makes them fail the content
            // check. Trim the strings to prevent this from happening.
            const parsed = el && el.content.split(',').map(kw => kw.trim());
            return parsed && parsed[0] ? [...new Set(parsed)] : [];
        }
        return el && el.content;
    }

    async save() {
        const data = {};
        if (this.canEditTitle) {
            data.website_meta_title = seoContext.title;
        }
        if (this.canEditDescription) {
            data.website_meta_description = seoContext.description;
        }
        if (this.canEditKeywords) {
            data.website_meta_keywords = seoContext.keywords.join(',');
        }
        if (this.canEditUrl) {
            if (seoContext.seoName !== this.previousSeoName) {
                data.seo_name = seoContext.seoName;
            }
        }
        data.website_meta_og_img = seoContext.metaImage;
        await this.orm.write(this.object.model, [this.object.id], data, {
            context: {
                lang: this.website.currentWebsite.metadata.lang,
                'website_id': this.website.currentWebsite.id,
            },
        });
        this.website.goToWebsite({path: this.url.replace(this.previousSeoName || this.seoNameDefault, seoContext.seoName)});
    }
}
