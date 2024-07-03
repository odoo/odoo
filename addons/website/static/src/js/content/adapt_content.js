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

    // Special case for Safari browser: padding on wrapwrap is added by the
    // layout option (boxed, etc), but it also receives a border on top of
    // it to simulate an addition of padding. That padding is added with
    // the "sidebar" header template to combine both options/effects.
    // Sadly, the border hack is not working on safari, the menu is somehow
    // broken and its content is not visible.
    // This class will be used in scss to instead add the border size to the
    // padding directly on Safari when "sidebar" menu is enabled.
    if (/^((?!chrome|android).)*safari/i.test(navigator.userAgent)) {
        document.querySelector("#wrapwrap").classList.add("o_safari_browser");
    }
});
