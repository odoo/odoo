/** @odoo-module */

document.addEventListener('DOMContentLoaded', () => {
    const htmlEl = document.documentElement;
    const editTranslations = !!htmlEl.dataset.edit_translations;
    // Hack: on translation editor, textareas with translatable text content
    // will get a `<span/>` as translation value which stays visible until
    // the values are updated on the editor. The same issue was fixed on CSS
    // for `placeholder` and `value` attributes (since we can get the elements
    // with attribute translation on CSS). But here, we need to hide the text
    // on JS until the editor's code sets the right values on textareas.
    if (editTranslations) {
        [...document.querySelectorAll('textarea')].map(textarea => {
            if (textarea.value.indexOf('data-oe-translation-initial-sha') !== -1) {
                textarea.classList.add('o_text_content_invisible');
            }
        });
    }
    // Hack: we move the '#o_search_modal' from the '#header' to
    // '#o_shared_blocks'. Without this change, when the header has a
    // 'transform: translate' (when it's fixed), the modal, which is positioned
    // absolutely, takes the dimensions of the header instead of those of the
    // 'body'.
    const searchModalEl = document.querySelector("header#top .modal#o_search_modal");
    if (searchModalEl) {
        document.querySelector("#o_shared_blocks").appendChild(searchModalEl);
    }
});
