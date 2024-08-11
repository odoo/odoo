import options from "@web_editor/js/editor/snippets.options";

options.registry.faqHorizontalMultipleItems = options.registry.MultipleItems.extend({
    _addItemCallback() {
        // Find the iframe and its #wrapwrap
        const iframe = document.querySelector('.o_iframe');
        const iframeDocument = iframe.contentDocument || iframe.contentWindow.document;
        const wrapwrap = iframeDocument.getElementById('wrapwrap');

        const topics = this.$target[0].getElementsByClassName('s_faq_horizontal_entry');
        const newTopic = topics[topics.length - 1];
        const newTopicRect = newTopic.getBoundingClientRect();
        const wrapwrapRect = wrapwrap.getBoundingClientRect();

        const scrollTop = wrapwrap.scrollTop;
        const centerY = (newTopicRect.top - wrapwrapRect.top) + scrollTop - (wrapwrap.clientHeight / 2) + (newTopicRect.height / 2);

        wrapwrap.scrollTo({
            top: centerY,
            behavior: 'smooth'
        });
    }
});
