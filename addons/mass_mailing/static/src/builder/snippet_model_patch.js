export const massMailingSnippetModelPatch = {
    cleanSnippetForSave(snippetCopyEl, cleanForSaveHandlers) {
        super.cleanSnippetForSave(snippetCopyEl, cleanForSaveHandlers);
        const dynamicPlaceholders = snippetCopyEl.querySelectorAll("t[t-out]");
        dynamicPlaceholders.forEach((placeholderEl) => {
            const placeholderString =
                placeholderEl.innerText || placeholderEl.getAttribute("t-out");
            placeholderEl.before(placeholderString);
            placeholderEl.remove();
        });
        snippetCopyEl.removeAttribute("data-filter-domain");
    },
};
