/** @odoo-module */

import { patch } from '@web/core/utils/patch';
import { registry } from "@web/core/registry";

let uniqueSeed = 0;

odoo.loader.bus.addEventListener("module-started", (e) => {
    if (e.moduleName === "@social_twitter/js/stream_post_comments_reply") {
        patch(e.module.StreamPostCommentsReplyTwitter.prototype, "social_twitter_spam", {
            get authorPictureSrc() { return '' }
        });
    }
})


const triggerEnterEvent = (element) => {
    const ev = new window.KeyboardEvent('keydown', { bubbles: true, key: "Enter" });
    element.dispatchEvent(ev);
};

function createReplies(textareaSelector) {
    const maximumAllowedReplies = 3;
    uniqueSeed += 1;

    let tourSteps = [];

    // must be able to post "maximumAllowedReplies" replies
    for (let i = 0; i < maximumAllowedReplies; i++) {
        const message = `__social_twitter_test_tour_${uniqueSeed}_${i}__`;

        tourSteps.push(
            {
                trigger: '.o_social_comments_modal textarea',
                content: `Reply number ${i}`,
                run: () => {
                    const $inputComment = $(textareaSelector);
                    $inputComment.val(message);
                    triggerEnterEvent($inputComment[0]);
                }
            },
            {
                trigger: `.o_social_comment_text[data-original-message*="${message}"]`,
                content: 'Check if the comment has been posted',
            },
        );
    }

    // the next reply must fail
    const message = `__social_twitter_test_tour_${uniqueSeed}_last__`;
    tourSteps.push(
        {
            trigger: '.o_social_comments_modal textarea',
            content: 'Write the last comment that will fail',
            run: () => {
                const $inputComment = $(textareaSelector);
                $inputComment.val(message);
                triggerEnterEvent($inputComment[0]);
            },
        },
        {
            trigger: '.o_social_comments_modal',
            extra_trigger: '.o_social_textarea_message.text-danger',
            content: 'Should not be able to spam',
            run: () => {
                const $fourthComment = $(`.o_social_comment_text[data-original-message*="${message}"]`);
                if ($fourthComment.length) {
                    console.error('Should not be able to spam (message detected)');
                }
            },
        },
    );

    return tourSteps;
}

/**
  * Twitter has a spam detection and will take measures against spamming accounts.
  * We now have a spam check mechanism to prevent any potential issues.
  * This will test that:
  * - Users can't spam when replying to a stream.post
  * - Users can't spam when replying to another comment (on a stream.post)
  *
  * The spam detection is set to maximum 3 comments.
  **/
registry.category("web_tour.tours").add(
    'social_twitter/static/tests/tours/tour_social_twitter_spam.js',
    {
        url: '/web',
        test: true,
        steps: () => [
        {
            trigger: '.o_app[data-menu-xmlid="social.menu_social_global"]',
            content: 'Open the Social App',
            run: 'click',
        },
        {
            trigger: '.o_social_stream_post_message',
            content: 'Open the tweet comments',
            run: 'click',
        },
        // Test comments spam
        ...createReplies('.o_social_comments_modal textarea.o_social_add_comment:not([data-is-comment-reply])'),
        // Test replies spam
        // TODO awa: not sure how this one worked, as we have no textarea to reply already opened
        // ...createReplies('.o_social_comment:first textarea[name="message"]'),
    ]
});
