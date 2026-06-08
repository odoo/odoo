export function insertHtmlContent(interaction, content, locationEl, position) {
    const parser = new DOMParser();
    const body = parser.parseFromString(content, "text/html").body;
    const contentEls = body.children;
    if (contentEls.length === 0) {
        locationEl.textContent = body.textContent;
        return;
    }
    interaction.insert(contentEls[0], locationEl, position);
    for (const contentEl of Array.from(contentEls)) {
        interaction.insert(contentEl, locationEl, "beforeend");
    }
}

/**
 * Helper: Get the slide dict matching the given criteria
 * @param {Array<Object>} slideList List of dict representing a slide
 * @param {Object<string, any>} matcher
 */
export function findSlide(slideList, matcher) {
    return slideList.find((slide) =>
        Object.keys(matcher).every((key) => matcher[key] === slide[key])
    );
}
