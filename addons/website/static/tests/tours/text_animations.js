import {
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour("text_animations", {
    url: "/",
    edition: true,
}, () => [
    ...insertSnippet({
        id: "s_cover",
        name: "Cover",
        groupName: "Intro",
    }),
    {
        content: "Select the snippet title",
        trigger: ":iframe .s_cover h1",
        async run(actions) {
            await actions.click();
            const range = document.createRange();
            const selection = this.anchor.ownerDocument.getSelection();
            range.selectNodeContents(this.anchor);
            selection.removeAllRanges();
            selection.addRange(range);
        },
    },
    {
        content: "Click on the 'Animate Text' button to activate the option",
        trigger: "div.o_we_animate_text",
        run: "click",
    },
    {
        content: "Check that the animation was applied",
        trigger: ":iframe .s_cover h1 span.o_animated_text",
    },
    {
        content: "Click on the 'Animate Text' button",
        trigger: "div.o_we_animate_text",
        run: "click",
    },
    {
        content: "Check that the animation was disabled for the title",
        trigger: ":iframe .s_cover:not(:has(.o_animated_text))",
    },
    {
        content: "Try to apply the text animation again",
        trigger: "div.o_we_animate_text",
        run: "click",
    },
    {
        content: "Check that the animation was applied",
        trigger: ":iframe .s_cover:has(span.o_animated_text)",
    },
]);
