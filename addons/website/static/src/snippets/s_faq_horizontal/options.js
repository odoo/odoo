import options from "@web_editor/js/editor/snippets.options";

options.registry.faqHorizontalMultipleItems = options.registry.MultipleItems.extend({
    _addItemCallback() {
        // Find the iframe and its #wrapwrap
        const iframe = document.querySelector('.o_iframe');
        const iframeDocument = iframe.contentDocument || iframe.contentWindow.document;
        const scrollingEl = iframeDocument.scrollingElement;

        const topics = this.$target[0].getElementsByClassName('s_faq_horizontal_entry');
        const newTopic = topics[topics.length - 1];
        const newTopicRect = newTopic.getBoundingClientRect();

        const scrollTop = scrollingEl.scrollTop;
        const centerY = newTopicRect.top + scrollTop - (scrollingEl.clientHeight / 2) + (newTopicRect.height / 2);

        scrollingEl.scrollTo({
            top: centerY,
            behavior: 'smooth'
        });
    }
});
