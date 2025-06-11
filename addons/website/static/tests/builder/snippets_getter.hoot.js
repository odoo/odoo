import { unmockedOrm } from "@web/../tests/_framework/module_set.hoot";

function removeImageSrc(xmlString) {
    const doc = new DOMParser().parseFromString(xmlString, "text/html");
    for (const img of doc.getElementsByTagName("img")) {
        img.removeAttribute("src");
    }
    const elementsWithBackgroundImage = doc.querySelectorAll('[style*="background-image"]');
    for (const el of elementsWithBackgroundImage) {
        const style = el.getAttribute("style");
        const newStyle = style.replace(/background-image\s*:\s*url\([^)]+\);?/g, ""); // Remove background-image rule
        el.setAttribute("style", newStyle);
    }
    return new XMLSerializer().serializeToString(doc);
}

let websiteSnippetsPromise;
export const getWebsiteSnippets = async () => {
    if (!websiteSnippetsPromise) {
        websiteSnippetsPromise = unmockedOrm(
            "ir.ui.view",
            "render_public_asset",
            ["website.snippets"],
            {}
        );
    }
    const str = await websiteSnippetsPromise;
    return removeImageSrc(str.trim());
};
