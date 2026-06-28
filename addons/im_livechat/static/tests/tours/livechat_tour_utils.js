export const LIVECHAT_COMPOSER = ".o-livechat-root:shadow .o-mail-Composer-input";

/** Type `text` into the livechat composer once it is ready, without sending it. */
export const editComposer = (text) => ({
    trigger: `${LIVECHAT_COMPOSER}:enabled`,
    run: `edit ${text}`,
});

/**
 * Tour step clicking the livechat composer Send button once it is enabled.
 *
 * This is the standard way to send a livechat message: only press Enter when a
 * test specifically exercises the Enter key. Waiting for `:enabled` avoids
 * clicking while the composer/button is still disabled (e.g. a pending step
 * response), which would no-op or send stale content.
 */
export const clickSend = () => ({
    trigger: ".o-livechat-root:shadow .o-mail-Composer button[aria-label='Send']:enabled",
    run: "click",
});

/**
 * Steps editing the livechat composer once ready, then sending via the Send
 * button. Returns an array, so spread it into a tour: `...postMessage(text)`.
 *
 * Editing waits for the composer `:enabled`: a chatbot step message is
 * delivered over the bus and can arrive before the awaited step trigger
 * response that moves the chatbot to the next step and re-enables the composer.
 * Editing too early would answer the previous step.
 */
export const postMessage = (text) => [editComposer(text), clickSend()];

/**
 * Tour step waiting for a livechat message whose body is exactly `text`.
 *
 * Targets `.o-mail-Message-body` with `:text()` (exact) rather than the whole
 * message with `:contains()` (substring), so author, date or answer-button text
 * cannot satisfy the match. Pass `index` to target the nth such message when the
 * same text appears more than once, and `selfAuthored` to require the message to
 * be authored by the current user.
 */
export const waitForMessage = (text, { index, selfAuthored } = {}) => ({
    trigger:
        ".o-livechat-root:shadow .o-mail-Message" +
        (selfAuthored ? ".o-selfAuthored" : "") +
        `:has(.o-mail-Message-body:text("${text}"))` +
        (index === undefined ? "" : `:eq(${index})`),
});
