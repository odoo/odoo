export const HEADER_LOGO_SELECTOR = ".navbar-brand.logo span img";
const LOGO_SELECTOR = `${HEADER_LOGO_SELECTOR}, .o_footer_logo img`;
// The width is kept because footer templates set it.
const LOGO_STYLES_TO_REMOVE = [
    "transform",
    "transform-box",
    "transform-origin",
    "transform-style",
    "height",
];

export function applyLogo(root, pickedImg) {
    for (const img of root.querySelectorAll(LOGO_SELECTOR)) {
        for (const key of Object.keys(img.dataset)) {
            delete img.dataset[key];
        }
        for (const property of LOGO_STYLES_TO_REMOVE) {
            img.style.removeProperty(property);
        }
        img.setAttribute("src", pickedImg.getAttribute("src"));
        img.removeAttribute("srcset");
        img.classList.toggle(
            "o_modified_image_to_save",
            pickedImg.classList.contains("o_modified_image_to_save")
        );
        Object.assign(img.dataset, pickedImg.dataset);
    }
}

// Used to force Chrome to refresh the tab label.
export const PREVIEW_TITLE_MARK = "\u200b";

// Texts are compared with `document.title`, whose spaces the browser collapses.
const collapseSpaces = (text) => text.replace(/[\t\n\f\r ]+/g, " ").trim();

export function createTitlePreview(titlePlugin, doc) {
    const defaultTitleMeta = doc.querySelector("meta[name='default_title']");
    const showsDefaultTitle =
        !!defaultTitleMeta && collapseSpaces(defaultTitleMeta.content) === doc.title;
    const getPageTitle = () => titlePlugin.getParts().action || "";
    let originalTitle;
    return {
        show(name, previousName) {
            const title = collapseSpaces(getPageTitle().replace(PREVIEW_TITLE_MARK, ""));
            originalTitle ??= title;
            previousName = collapseSpaces(previousName);
            if (showsDefaultTitle && title.endsWith(previousName)) {
                const newTitle = title.slice(0, -previousName.length) + collapseSpaces(name);
                titlePlugin.setParts({
                    action: newTitle === originalTitle ? newTitle : newTitle + PREVIEW_TITLE_MARK,
                });
            }
        },
    };
}

// What the website serves as favicon when it has none.
const FAVICON_PLACEHOLDER_URL = "/web/static/img/placeholder.png";

export function createFaviconPreview(doc = window.top.document) {
    const resetHrefs = new Map();
    const show = (url) => {
        for (const link of doc.head.querySelectorAll("link[rel*='icon']")) {
            if (!resetHrefs.has(link)) {
                resetHrefs.set(link, link.href);
            }
            link.href = url;
        }
    };
    return {
        show,
        showPlaceholder: () => show(FAVICON_PLACEHOLDER_URL),
        commit() {
            resetHrefs.clear();
        },
        reset() {
            for (const [link, href] of resetHrefs) {
                link.href = href;
            }
            resetHrefs.clear();
        },
    };
}
