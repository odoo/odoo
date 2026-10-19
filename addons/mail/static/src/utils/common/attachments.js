/**
 * @typedef {Object} AttachmentGroup
 * @property {import("models").Attachment} attachment the attachment standing
 *  for the whole group
 * @property {import("models").Attachment[]} duplicates every attachment of the
 *  group, the representative one included
 */

/**
 * Group the given attachments, preserving their order. Attachments sharing
 * their content are only put in a same group when `byContent` is set, e.g. in
 * the chatter attachment box where a signature image repeated on every message
 * would otherwise bury the relevant files.
 *
 * @param {import("models").Attachment[]} attachments
 * @param {Object} [options]
 * @param {boolean} [options.byContent=false]
 * @returns {AttachmentGroup[]}
 */
export function groupAttachments(attachments, { byContent = false } = {}) {
    const keyOf = (attachment) =>
        byContent && attachment.checksum
            ? `checksum-${attachment.checksum}`
            : `id-${attachment.id}`;
    /** @type {Map<string, import("models").Attachment[]>} */
    const duplicatesByKey = new Map();
    for (const attachment of attachments) {
        const key = keyOf(attachment);
        if (!duplicatesByKey.has(key)) {
            duplicatesByKey.set(key, []);
        }
        duplicatesByKey.get(key).push(attachment);
    }
    const groups = [];
    for (const attachment of attachments) {
        const duplicates = duplicatesByKey.get(keyOf(attachment));
        // the group takes the place of its last occurrence, so that grouping
        // doesn't move a file away from where the caller ordered it
        if (attachment.eq(duplicates.at(-1))) {
            groups.push({ attachment, duplicates });
        }
    }
    return groups;
}
