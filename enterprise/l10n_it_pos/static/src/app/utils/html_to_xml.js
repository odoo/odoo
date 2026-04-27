export function htmlToXml(htmlString, tags, attributes) {
    // replace all tags and attributes
    for (const tag of [
        ...tags.sort((a, b) => b.length - a.length),
        ...attributes.sort((a, b) => b.length - a.length),
    ]) {
        htmlString = htmlString.replaceAll(tag.toLowerCase(), tag);
    }

    // make self-closing tags
    const xmlString = htmlString.replaceAll(/<(\w+)([^>]*)>\s*<\/\1>/g, "<$1$2 />");

    return xmlString;
}
