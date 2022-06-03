/** @odoo-module */

import { CLIPBOARD_WHITELISTS } from '@web_editor/../lib/odoo-editor/src/OdooEditor';
import { nonEditableMediaAncestorsSelectors } from '@web_editor/js/common/wysiwyg_utils';

/**
 * Allow @see o_knowledge_ classes to be preserved in the editor on paste.
 */
CLIPBOARD_WHITELISTS.classes.push(/^o_knowledge_/);

nonEditableMediaAncestorsSelectors.push(
    '.o_knowledge_file',
    '.o_knowledge_toolbar',
);
