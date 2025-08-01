export function insertHtmlContent(interaction, content, locationEl, position) {
    const parser = new DOMParser();
    const body = parser.parseFromString(content, "text/html").body;
    const contentEls = body.children;
    if (contentEls.length === 0) {
        locationEl.textContent = body.textContent;
        return;
    }
    interaction.insert(contentEls[0], locationEl, position);
    for (let i = 1; i < contentEls.length; i++) {
        interaction.insert(contentEls[i], contentEls[i - 1], "afterend");
    }
}

/**
 * Helper: Get the slide dict matching the given criteria
 * @param {Array<Object>} slideList List of dict reprensenting a slide
 * @param {[string] : any} matcher
 */
export function findSlide(slideList, matcher) {
    return slideList.find((slide) =>
        Object.keys(matcher).every((key) => matcher[key] === slide[key])
    );
}
