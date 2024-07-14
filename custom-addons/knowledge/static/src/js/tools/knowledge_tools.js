/** @odoo-module */

const HEADINGS = [
    'H1',
    'H2',
    'H3',
    'H4',
    'H5',
    'H6',
];

/**
 * Allows to fetch relevant headings in the page when building the Table of Content.
 * Will filter out things we don't want:
 * - Empty headers
 * - Headers only containing the 'ZeroWidthSpace' element ('\u200B')
 * - Headers contained into templates
 *
 * @param {Element} element
 */
const fetchValidHeadings = (element) => {
    const templateHeadings = Array.from(element.querySelectorAll(
        HEADINGS.map((heading) => `.o_knowledge_behavior_type_template ${heading}`).join(',')
    ));

    return Array.from(element.querySelectorAll(HEADINGS.join(',')))
        .filter((heading) => heading.innerText.trim().replaceAll('\u200B', '').length > 0)
        .filter((heading) => !templateHeadings.includes(heading));
};

export { HEADINGS, fetchValidHeadings };
