import { realOrm } from "@web/../tests/_framework/module_set.hoot";

function removeImageSrc(xmlString) {
    const doc = new DOMParser().parseFromString(xmlString, "text/html");
    for (let img of doc.getElementsByTagName("img")) {
        img.removeAttribute("src");
    }
    const elementsWithBackgroundImage = doc.querySelectorAll('[style*="background-image"]');
    for (let el of elementsWithBackgroundImage) {
        const style = el.getAttribute("style");
        const newStyle = style.replace(/background-image\s*:\s*url\([^\)]+\);?/g, ''); // Remove background-image rule
        el.setAttribute("style", newStyle);
    }
    return new XMLSerializer().serializeToString(doc);
}

let websiteSnippets;
export const getWebsiteSnippets = async () => {
    if (!websiteSnippets) {
        const str = await realOrm(
            "ir.ui.view",
            "render_public_asset",
            ["website.snippets"],
            {}
        );
        websiteSnippets = removeImageSrc(str.trim());
    }
    return websiteSnippets;
};
