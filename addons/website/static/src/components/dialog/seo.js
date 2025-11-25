import { _t } from "@web/core/l10n/translation";
import { deduceURLfromText } from "@html_editor/main/link/utils";
import { pyToJsLocale, jsToPyLocale } from "@web/core/l10n/utils";
import { htmlToTextContentInline } from "@mail/utils/common/format";
import { rpc } from "@web/core/network/rpc";
import { escapeRegExp } from "@web/core/utils/strings";
import { useService, useAutofocus } from "@web/core/utils/hooks";
import { isVisible } from "@web/core/utils/ui";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { MediaDialog } from "@html_editor/main/media/media_dialog/media_dialog";
import { WebsiteDialog } from "./dialog";
import {
    Component,
    onMounted,
    onWillStart,
    reactive,
    useEffect,
    useState,
    useRef,
} from "@odoo/owl";
import wUtils from "@website/js/utils";

// This replaces \b, because accents(e.g. à, é) are not seen as word boundaries.
// Javascript \b is not unicode aware, and words beginning or ending by accents won't match \b
const WORD_SEPARATORS_REGEX =
    "([\\u2000-\\u206F\\u2E00-\\u2E7F'!\"#\\$%&\\(\\)\\*\\+,\\-\\.\\/:;<=>\\?¿¡@\\[\\]\\^_`\\{\\|\\}~\\s]+|^|$)";

const seoContext = reactive({
    description: "",
    keywords: [],
    title: "",
    seoName: "",
    metaImage: "",
    defaultTitle: "",
    updatedAlts: [],
    brokenLinks: [],
});

const LINK_CHECK_BASE_OPTIONS = {
    method: "GET",
    referrerPolicy: "no-referrer",
    credentials: "omit",
};
const LINK_CHECK_MANUAL_OPTIONS = { ...LINK_CHECK_BASE_OPTIONS, redirect: "manual" };
const LINK_CHECK_NO_CORS_OPTIONS = { ...LINK_CHECK_BASE_OPTIONS, mode: "no-cors" };

const inspectLink = async (url, options) => {
    try {
        const response = await fetch(url, options);
        if (response.type === "opaqueredirect") {
            return "external_redirect";
        }
        if (response.status >= 400) {
            return "error";
        }
        return "ok";
    } catch {
        return "failed";
    }
};

const checkLinkStatus = async (url, { useNoCorsFallback = false } = {}) => {
    let status = await inspectLink(url, LINK_CHECK_BASE_OPTIONS);
    if (status === "failed") {
        const fallbackStatus = await inspectLink(url, LINK_CHECK_MANUAL_OPTIONS);
        status = fallbackStatus === "external_redirect" ? "ok" : fallbackStatus;
    }
    if (useNoCorsFallback && status === "failed") {
        status = await inspectLink(url, LINK_CHECK_NO_CORS_OPTIONS);
    }
    return status;
};

const getSeo = async (self, onlyKeywords = false) => {
    const pageTextContentEl =
        self.website.pageDocument.documentElement.querySelector("#wrap, main, body");
    const lang = self.state.language || "en";
    const tagWeights = {
        h1: 5,
        h2: 4,
        h3: 3,
        a: 2,
        p: 1,
    };
    const maxNGrams = 2;

    const getKeywordsFromText = (text, weight, wordCounts) => {
        const segmenter = new Intl.Segmenter(lang, { granularity: "word" });
        const segmentedText = segmenter.segment(text);
        const words = [...segmentedText]
            .filter((s) => s.isWordLike)
            .map((s) => s.segment.toLowerCase())
            .filter((word) => !/[0-9]+/.test(word));
        const singleWordsLength = words.length;
        for (let nGram = maxNGrams; nGram > 1; nGram--) {
            for (let i = 0; i <= singleWordsLength - nGram; i++) {
                if (words[i].length > 4 && words[i + nGram - 1].length > 4) {
                    words.push(words.slice(i, i + nGram).join(" "));
                }
            }
        }
        if (words) {
            words
                .filter((word) => word.length > 4)
                .forEach((word) => {
                    if (!wordCounts[word]) {
                        wordCounts[word] = 0;
                    }
                    wordCounts[word] += weight * (word.length - 3);
                });
        }
    };

    const jaccardSimilarity = (str1, str2) => {
        const set1 = new Set(str1.replace(/\s+/g, "").split(""));
        const set2 = new Set(str2.replace(/\s+/g, "").split(""));

        const intersection = new Set([...set1].filter((item) => set2.has(item)));
        const union = new Set([...set1, ...set2]);

        return intersection.size / union.size;
    };

    const extractKeywords = () => {
        const wordCounts = {};

        Object.keys(tagWeights).forEach((tag) => {
            const elements = pageTextContentEl.getElementsByTagName(tag);
            for (const element of elements) {
                getKeywordsFromText(element.innerText, tagWeights[tag], wordCounts);
            }
        });

        const keywords = Object.entries(wordCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 20);

        for (let i = 0; i < keywords.length; i++) {
            for (let j = 0; j < keywords.length; j++) {
                if (i == j || keywords[i][1] === 0) {
                    continue;
                }
                if (jaccardSimilarity(keywords[i][0], keywords[j][0]) > 0.5) {
                    keywords[i][1] += keywords[j][1];
                    keywords[j][1] = 0;
                }
            }
        }
        const sortedKeywords = keywords
            .sort((a, b) => b[1] - a[1])
            .filter((entry) => entry[1] > 0)
            .map((entry) => entry[0])
            .slice(0, 7);
        return sortedKeywords;
    };

    const extractDescription = () => {
        let subtitlesEls = pageTextContentEl.querySelectorAll(
            "[class*='subtitle'],[class*='lead'],[data-oe-field*='subtitle'],[data-oe-field*='description']"
        );
        subtitlesEls = Array.from(subtitlesEls).filter(
            (el) => isVisible(el) && el.innerText.trim()
        );
        if (subtitlesEls.length) {
            return subtitlesEls[0].innerText.trim();
        }
        let headersEls = pageTextContentEl.querySelectorAll("h2,h3");
        headersEls = Array.from(headersEls).filter(
            (el) => isVisible(el) && el.innerText.trim().replace(/[\W\d]/g, "")
        );
        if (headersEls.length) {
            return headersEls.map((el) => el.innerText.trim().replace(/\s+/g, " ")).join(", ");
        }
        return self.seoContext.title || self.seoContext.description || "";
    };

    const keywords = extractKeywords();
    if (keywords.length) {
        self.seoContext.keywords = keywords;
    }
    if (!onlyKeywords) {
        self.seoContext.title = htmlToTextContentInline(self.seoContext.defaultTitle);
        self.seoContext.description = extractDescription();
    }
};

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
        this.website = useService("website");
        this.dialogs = useService("dialog");

        this.seoContext = useState(seoContext);

        const firstImageId = this.props.hasSocialDefaultImage ? "social_default_image" : "logo";
        const firstImageSrc = `/web/image/website/${encodeURIComponent(
            this.website.currentWebsite.id
        )}/${firstImageId}`;
        const firstImage = {
            src: firstImageSrc,
            active: this.areSameImages(firstImageSrc, this.seoContext.metaImage),
            custom: false,
        };

        this.state = useState({
            images: [
                firstImage,
                ...this.props.pageImages.map((src) => ({
                    src,
                    active: this.areSameImages(src, this.seoContext.metaImage),
                    custom: false,
                })),
            ],
        });

        if (
            this.seoContext.metaImage &&
            !this.state.images
                .map(({ src }) => this.getImagePathname(src))
                .includes(this.getImagePathname(this.seoContext.metaImage))
        ) {
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

    get activeMetaImage() {
        const activeImage = this.state.images.find(({ active }) => active);
        return activeImage && activeImage.src;
    }

    getImagePathname(src) {
        return new URL(src, this.website.pageDocument.location.origin).pathname;
    }

    areSameImages(src1, src2) {
        return this.getImagePathname(src1) === this.getImagePathname(src2);
    }

    selectImage(src) {
        this.state.images = this.state.images.map((img) => {
            img.active = img.src === src;
            return img;
        });
        this.seoContext.metaImage = src;
    }

    openMediaDialog() {
        this.dialogs.add(MediaDialog, {
            onlyImages: true,
            resModel: "ir.ui.view",
            useMediaLibrary: true,
            save: (image) => {
                let existingImage;
                const src = image.getAttribute("src");
                this.state.images = this.state.images.map((img) => {
                    img.active = false;
                    if (img.src === src) {
                        existingImage = img;
                        img.active = true;
                    }
                    return img;
                });
                if (!existingImage) {
                    this.state.images.push({
                        src: src,
                        active: true,
                        custom: true,
                    });
                }
                this.seoContext.metaImage = src;
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
        this.website = useService("website");

        this.seoContext = useState(seoContext);

        this.state = useState({
            suggestions: [],
        });

        this.translatedStrings = {
            usedInH1: _t('"%(keyword)s" is used in page first level heading', {
                keyword: this.props.keyword,
            }),
            usedInH2: _t('"%(keyword)s" is used in page second level heading', {
                keyword: this.props.keyword,
            }),
            usedInTitle: _t('"%(keyword)s" is used in page title', {
                keyword: this.props.keyword,
            }),
            usedInDescription: _t('"%(keyword)s" is used in page description', {
                keyword: this.props.keyword,
            }),
            usedInContent: _t('"%(keyword)s" is used in page content', {
                keyword: this.props.keyword,
            }),
            suggestionTag: (suggestion) => _t('Add "%(suggestion)s"', { suggestion }),
            googleTrendsTitle: _t("See Google Trends about '%(keyword)s'", {
                keyword: this.props.keyword,
            }),
            removeBtn: _t('Remove "%(keyword)s"', { keyword: this.props.keyword }),
        };

        onMounted(async () => {
            const suggestions = await rpc("/website/seo_suggest", {
                lang: jsToPyLocale(this.props.language),
                keywords: this.props.keyword,
            });
            const regex = new RegExp(
                WORD_SEPARATORS_REGEX + escapeRegExp(this.props.keyword) + WORD_SEPARATORS_REGEX,
                "gi"
            );
            this.state.suggestions = [
                ...new Set(
                    JSON.parse(suggestions)
                        .map((word) => word.replace(regex, "").trim())
                        .filter(Boolean)
                ),
            ];
        });
    }

    isKeywordIn(string) {
        return new RegExp(
            WORD_SEPARATORS_REGEX + escapeRegExp(this.props.keyword) + WORD_SEPARATORS_REGEX,
            "gi"
        ).test(string);
    }

    getGoogleTrendsURL() {
        return `https://trends.google.com/trends/explore?q=${encodeURIComponent(
            this.props.keyword
        )}`;
    }

    getHeaders(tag) {
        return Array.from(
            this.website.pageDocument.documentElement.querySelectorAll(`#wrap ${tag}`)
        ).map((header) => header.textContent);
    }

    getBodyText() {
        return this.website.pageDocument.body.textContent;
    }

    get usedInH1() {
        return this.isKeywordIn(this.getHeaders("h1"));
    }

    get usedInH2() {
        return this.isKeywordIn(this.getHeaders("h2"));
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
        this.website = useService("website");

        this.seoContext = useState(seoContext);

        this.state = useState({
            language: "",
            keyword: "",
        });

        this.maxKeywords = 10;

        onWillStart(async () => {
            this.languages = await rpc("/website/get_languages");
            this.state.language = this.getLanguage();
        });
    }

    provideKeywords() {
        getSeo(this, true);
    }

    onKeyup(ev) {
        // Add keyword on enter.
        if (ev.key === "Enter") {
            this.addKeyword(this.state.keyword);
        }
    }

    getLanguage() {
        return pyToJsLocale(
            this.website.pageDocument.documentElement.getAttribute("lang") || "en-US"
        );
    }

    get isFull() {
        return this.seoContext.keywords.length >= this.maxKeywords;
    }

    addKeyword(keyword) {
        keyword = keyword.replaceAll(/,\s*/gi, " ").trim();
        if (keyword && !this.isFull && !this.seoContext.keywords.includes(keyword)) {
            this.seoContext.keywords.push(keyword);
            this.state.keyword = "";
        }
    }

    removeKeyword(keyword) {
        this.seoContext.keywords = this.seoContext.keywords.filter((kw) => kw !== keyword);
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

    setup() {
        this.website = useService("website");
        this.seoContext = useState(seoContext);
        this.logo = `/web/image/website/${encodeURIComponent(this.website.currentWebsite.id)}/logo`;
    }

    get urlToBreadcrumbs() {
        const MAX_LENGTH = 45;
        const REPLACEMENT = "…";
        let translatedPage = false;
        if (this.website.currentWebsite.metadata.langName !== undefined) {
            translatedPage = true;
        }
        const urlObj = new URL(this.props.url);
        const hostname = urlObj.hostname;
        const path = urlObj.pathname;

        const segments = path.split("/").filter((segment) => segment);
        // Remove non-readable elements (numeric parts)
        const readableSegments = segments.map((segment) => {
            // Remove numeric suffixes (e.g., "astronomy-2" becomes "astronomy")
            const noNumericSuffix = segment.replace(/-\d+$/, "");
            // Replace dashes with spaces and remove numbers
            return noNumericSuffix.replace(/-/g, " ").replace(/\d+/g, "");
        });
        // Capitalise the first word of each segment
        let capitalisedSegments = readableSegments.map(
            (segment) => segment.replace(/\b\w/, (char) => char.toUpperCase()) // Capitalise each word
        );
        // Remove the localisation part if it's there
        if (translatedPage) {
            capitalisedSegments = capitalisedSegments.slice(1);
        }
        capitalisedSegments.unshift(`https://${hostname}`);
        // Manage the truncated parts if it's too long
        let lastIndexOfEllipsis = null;
        while (
            capitalisedSegments.length > 2 &&
            capitalisedSegments.join("   ").length > MAX_LENGTH
        ) {
            let replaced = false;
            for (let index = 1; index < capitalisedSegments.length - 1; index++) {
                if (capitalisedSegments[index] !== REPLACEMENT) {
                    capitalisedSegments[index] = REPLACEMENT;
                    replaced = true;
                    lastIndexOfEllipsis = index;
                    break;
                }
            }
            if (!replaced) {
                break;
            }
        }
        if (lastIndexOfEllipsis) {
            capitalisedSegments = capitalisedSegments.filter(
                (item, index) => item !== REPLACEMENT || index === lastIndexOfEllipsis
            );
        }
        return capitalisedSegments.join(" › ");
    }

    get description() {
        if (this.props.description?.length > 160) {
            return this.props.description.substring(0, 159) + "…";
        } else if (!this.props.description?.length) {
            return _t(
                "If you don't write one, the description will be generated by the search engines based on the content of your page."
            );
        }
        return this.props.description || "";
    }
}
class TitleDescription extends Component {
    static template = "website.TitleDescription";
    static props = {
        canEditSeo: Boolean,
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
        this.website = useService("website");
        useAutofocus();

        this.state = useState({
            language: this.getLanguage(),
        });
        this.previousSeoName = this.seoContext.seoName;

        this.maxRecommendedDescriptionSize = 160;
        this.minRecommendedDescriptionSize = 50;

        this.titleTooltip = _t(
            'Add your own title or leave empty to use "%(defaultTitle)s". Your page title should contain max 65 characters.',
            { defaultTitle: this.props.defaultTitle }
        );

        // Update the title when its input value changes
        useEffect(
            () => {
                document.title = this.title;
            },
            () => [this.seoContext.title]
        );

        // Restore the original title when unmounting the component
        useEffect(
            () => {
                const initialTitle = document.title;
                return () => (document.title = initialTitle);
            },
            () => []
        );
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

    get titleOrDescriptionNotSet() {
        return !this.seoContext.title || !this.seoContext.description;
    }

    get title() {
        return this.seoContext.title || this.props.defaultTitle;
    }

    get description() {
        return this.seoContext.description || "";
    }

    get descriptionWarning() {
        if (!this.seoContext.description) {
            return false;
        }
        if (this.seoContext.description.length < this.minRecommendedDescriptionSize) {
            return _t("Too short (min 50 chars)");
        } else if (this.seoContext.description.length > this.maxRecommendedDescriptionSize) {
            return _t("Too long (max 160 chars)");
        }
        return false;
    }

    getLanguage() {
        return pyToJsLocale(
            this.website.pageDocument.documentElement.getAttribute("lang") || "en-US"
        );
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    autoFill() {
        getSeo(this);
    }

    /**
     * @private
     * @param {InputEvent} ev
     */
    _updateInputValue(ev) {
        this.seoContext.seoName = wUtils.slugify(ev.target.value);
    }
}

export class BrokenLink extends Component {
    static template = "website.BrokenLink";

    static props = {
        link: Object,
    };

    setup() {
        this.website = useService("website");
        this.urlInputRef = useRef("url-input");
        this.link = this.props.link;

        this.state = useState({
            checkingLink: false,
        });

        useEffect(
            (input) => {
                if (!input) {
                    return;
                }
                const options = {
                    body: this.website.pageDocument.body,
                    position: "bottom-fit",
                    urlChosen: () => {
                        this.link.newLink = input.value;
                    },
                };
                const unmountAutocompleteWithPages = wUtils.autocompleteWithPages(
                    input,
                    options,
                    this.env
                );
                return () => unmountAutocompleteWithPages();
            },
            () => [this.urlInputRef.el]
        );
    }

    async modifyLink(link) {
        this.state.checkingLink = true;
        let broken = false;
        link.newLink = deduceURLfromText(link.newLink) || link.newLink;
        let url;
        try {
            const base = link.newLink.startsWith("/") ? window.origin : undefined;
            url = new URL(link.newLink, base);
        } catch {
            url = null;
            broken = true;
        }
        if (url?.protocol === "http:" || url?.protocol === "https:") {
            const sameOrigin = url.origin === window.location.origin;
            const targetUrl = sameOrigin ? url.pathname + url.search : url.href;
            const status = await checkLinkStatus(targetUrl, {
                useNoCorsFallback: !sameOrigin,
            });
            broken = status === "error" || status === "failed";
        }
        link.broken = broken;
        link.validLink = !broken ? link.newLink : null;
        this.state.checkingLink = false;
    }

    removeLink(link) {
        link.newLink = "";
        link.broken = false;
        link.remove = true;
    }

    checkButtonDisabled(link) {
        return (
            this.state.checkingLink ||
            !link.newLink.trim().length ||
            link.newLink.trim() == link.oldLink ||
            link.validLink == link.newLink.trim()
        );
    }
}

export class SeoChecks extends Component {
    static template = "website.SeoChecks";
    static components = {
        CheckBox,
        BrokenLink,
    };
    static props = {};

    async setup() {
        this.website = useService("website");
        this.seoContext = useState(seoContext);
        const {
            metadata: { mainObject, seoObject },
        } = this.website.currentWebsite;
        this.object = seoObject || mainObject;
        this.state = useState({
            altAttributes: [],
            checkingLinks: false,
            checkedLinks: false,
            counterLinks: 0,
            totalLinks: 0,
        });
        this.imgUpdated = this.imgUpdated.bind(this);
        onWillStart(async () => {
            this.state.altAttributes = await this.getAltAttributes();
            this.seoContext.updatedAlts = [];
        });
        onMounted(() => {
            this.getBrokenLinks();
        });
    }

    imgUpdated(img) {
        img.updated = true;
        this.seoContext.updatedAlts = this.state.altAttributes.filter((img) => img.updated);
    }

    async getAltAttributes() {
        const uniqueRecords = new Set();

        // Select all relevant <img> elements in the editable page.
        const imgEls = this.website.pageDocument.documentElement.querySelectorAll("#wrapwrap img");

        imgEls.forEach((el) => {
            // Find the closest ancestor element containing Odoo metadata.
            const recordEl = el.closest("[data-oe-model][data-oe-field][data-oe-id]");
            if (!recordEl) {
                return; // Skip images without a proper metadata wrapper.
            }

            const model = recordEl.dataset.oeModel;
            const id = recordEl.dataset.oeId;
            const field = recordEl.dataset.oeField;
            const type = recordEl.dataset.oeType;

            // Only include images that belong to static content definitions.
            if ((model !== "ir.ui.view" || field !== "arch") && type !== "html") {
                return;
            }

            // Build a unique signature string to avoid duplicates.
            uniqueRecords.add(`${model}||${id}||${field}||${type}`);
        });

        // Transform the Set of unique strings back into structured objects.
        const models = Array.from(uniqueRecords).map((entry) => {
            const [model, id, field, type] = entry.split("||");
            return { model, id: parseInt(id), field, type };
        });

        const results = await rpc("/website/get_alt_images", { models });

        return JSON.parse(results);
    }

    async getBrokenLinks() {
        this.state.checkingLinks = true;
        this.state.counterLinks = 1;
        const hrefEls = this.website.pageDocument.documentElement.querySelectorAll(
            "#wrapwrap a[href]:not(.oe_unremovable)"
        );
        let links = Array.from(hrefEls)
            .filter((a) => {
                const href = a.href;
                // Check if the href is not empty and belongs to the same origin as the
                // current page
                return (
                    href !== "" &&
                    href.startsWith("http") &&
                    new URL(href).origin === window.location.origin &&
                    a.getAttribute("href") !== "#"
                );
            })
            .map((el, index) => {
                const recordEl = el.closest(
                    "[data-res-model][data-res-id], [data-oe-model][data-oe-id]"
                );
                if (
                    !recordEl ||
                    ((recordEl.dataset.oeModel !== "ir.ui.view" ||
                        recordEl.dataset.oeField !== "arch") &&
                        recordEl.dataset.oeType !== "html")
                ) {
                    return false;
                }
                const hashIndex = el.href.indexOf("#");
                const cleanedUrl = hashIndex !== -1 ? el.href.substring(0, hashIndex) : el.href;
                const path = new URL(cleanedUrl);
                let label = "";
                let isImageLink = false;
                const textContent = el.textContent.trim();
                if (textContent) {
                    label = textContent;
                } else {
                    const imgLinkEl = el.querySelector("img");
                    if (imgLinkEl?.src) {
                        label = imgLinkEl.src.split("/").pop();
                        isImageLink = true;
                    } else if (el.querySelector(".fa")) {
                        label =
                            el.ariaLabel || el.title || el.href.split("/").filter(Boolean).pop();
                        isImageLink = true;
                    }
                }
                return {
                    link: path.pathname + path.search,
                    res_model: recordEl.dataset.resModel || recordEl.dataset.oeModel,
                    res_id: parseInt(recordEl.dataset.resId || recordEl.dataset.oeId, 10),
                    field: recordEl.dataset.oeField || null,
                    label: label,
                    isImageLink: isImageLink,
                    position: index,
                };
            })
            .filter(Boolean);
        const seen = new Set();
        links = links.filter((item) => {
            const key = `${item.link}::${item.res_model || ""}::${item.res_id || ""}::${
                item.field || ""
            }`;
            if (seen.has(key)) {
                return false;
            }
            seen.add(key);
            return true;
        });
        this.state.totalLinks = links.length;
        const brokenLinks = [];
        const promises = links.map(async (link) => {
            // Let the browser follow internal redirects; most site routes land here.
            const status = await checkLinkStatus(link.link);

            if (status === "error" || status === "failed") {
                brokenLinks.push(link);
            }

            this.state.counterLinks++;
        });
        await Promise.all(promises);
        this.state.checkingLinks = false;
        this.state.checkedLinks = true;
        // Keep links order in the DOM.
        brokenLinks.sort((a, b) => a.position - b.position);
        this.seoContext.brokenLinks = brokenLinks.map((link) => ({
            oldLink: link.link,
            newLink: link.link,
            broken: true,
            remove: false,
            res_model: link.res_model,
            res_id: link.res_id,
            field: link.field,
            label: link.label,
            isImageLink: link.isImageLink,
            validLink: null,
        }));
    }
}

export class OptimizeSEODialog extends Component {
    static template = "website.OptimizeSEODialog";
    static components = {
        WebsiteDialog,
        TitleDescription,
        ImageSelector,
        MetaKeywords,
        SeoChecks,
        BrokenLink,
    };
    static props = {
        close: Function,
    };

    setup() {
        this.website = useService("website");
        this.dialogs = useService("dialog");
        this.orm = useService("orm");

        this.title = _t("Search Engine Optimization");
        this.saveButton = _t("Save");
        this.size = "lg";
        this.contentClass = "oe_seo_configuration";

        onWillStart(async () => {
            // Wait for the preview iframe because this dialog reads directly
            // from the iframe DOM.
            await this.waitForIframe();
            const {
                metadata: { mainObject, seoObject, path },
            } = this.website.currentWebsite;
            this.object = seoObject || mainObject;
            this.data = await rpc("/website/get_seo_data", {
                res_id: this.object.id,
                res_model: this.object.model,
            });

            this.canEditSeo = this.data.can_edit_seo;
            this.canEditDescription = this.canEditSeo && "website_meta_description" in this.data;
            this.canEditTitle = this.canEditSeo && "website_meta_title" in this.data;
            this.canEditUrl = this.canEditSeo && "seo_name" in this.data;
            seoContext.title = this.canEditTitle && this.data.website_meta_title;

            // If website.page, hide the google preview & tell user his page is currently unindexed
            this.isIndexed = "website_indexed" in this.data ? this.data.website_indexed : true;
            this.seoNameHelp = _t(
                "This value will be escaped to be compliant with all major browsers and used in url. Keep it empty to use the default name of the record."
            );
            this.previousSeoName = this.canEditUrl && this.data.seo_name;
            seoContext.seoName = this.previousSeoName;
            this.seoNameDefault = this.canEditUrl && this.data.seo_name_default;

            seoContext.description = this.getMeta({ name: "description" });
            this.previewDescription = _t(
                "Your page description should be between 50 and 160 characters long."
            );
            this.defaultTitle = this.getMeta({ name: "default_title" }) || "";
            seoContext.defaultTitle = this.defaultTitle;
            this.url = path;

            seoContext.metaImage =
                this.data.website_meta_og_img || this.getMeta({ property: "og:image" });

            this.pageImages = this.getImages();
            this.socialPreviewDescription = _t(
                "The description will be generated by social media based on page content unless you specify one."
            );
            this.hasSocialDefaultImage = this.data.has_social_default_image;

            this.canEditKeywords = "website_meta_keywords" in this.data;
            seoContext.keywords = this.getMeta({ name: "keywords" });
        });
    }

    async waitForIframe() {
        await new Promise((resolve) => {
            const iframeEl = document.querySelector(
                ".o_iframe_container > iframe:not(.o_ignore_in_tour)"
            );
            if (!iframeEl || iframeEl.contentDocument?.readyState === "complete") {
                return resolve();
            }
            iframeEl.addEventListener("load", resolve, { once: true });
        });
    }

    get pageDocumentElement() {
        return this.website.pageDocument.documentElement;
    }

    getImages() {
        const imageEls = this.pageDocumentElement.querySelectorAll("#wrap img");
        return [
            ...new Set(
                Array.from(imageEls)
                    .filter((img) => img.naturalHeight > 200 && img.naturalWidth > 200)
                    .map((img) => img.getAttribute("src"))
            ),
        ];
    }

    getMeta({ name, property }) {
        let query = "";
        if (name) {
            query = `meta[name="${name}"]`;
        }
        if (property) {
            query = `meta[property="${property}"]`;
        }
        const el = this.pageDocumentElement.querySelector(query);
        if (name === "keywords") {
            // Keywords might contain spaces which makes them fail the content
            // check. Trim the strings to prevent this from happening.
            const parsed = el && el.content.split(",").map((kw) => kw.trim());
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
            data.website_meta_keywords = seoContext.keywords.join(",");
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
                website_id: this.website.currentWebsite.id,
            },
        });

        const rpcCalls = [];
        if (
            seoContext.brokenLinks.some(
                (link) => link.oldLink !== link.newLink || link.remove === true
            )
        ) {
            rpcCalls.push(
                rpc("/website/update_broken_links", {
                    links: seoContext.brokenLinks,
                })
            );
        }
        if (seoContext.updatedAlts?.length) {
            rpcCalls.push(
                rpc("/website/update_alt_images", {
                    imgs: seoContext.updatedAlts,
                })
            );
        }

        await Promise.all(rpcCalls);

        this.website.goToWebsite({
            path: this.url.replace(this.previousSeoName || this.seoNameDefault, seoContext.seoName),
        });
    }
}
