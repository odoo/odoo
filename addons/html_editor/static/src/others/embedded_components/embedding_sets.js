/** @odoo-module native */
import { captionEmbedding } from "@html_editor/others/embedded_components/backend/caption/caption";
import { dateEmbedding } from "@html_editor/others/embedded_components/backend/date/date";
import { fileEmbedding } from "@html_editor/others/embedded_components/backend/file/file";
import { syntaxHighlightingEmbedding } from "@html_editor/others/embedded_components/backend/syntax_highlighting/syntax_highlighting";
import { videoEmbedding } from "@html_editor/others/embedded_components/backend/video/video";
import { readonlyDateEmbedding } from "@html_editor/others/embedded_components/core/date/readonly_date";
import { readonlyFileEmbedding } from "@html_editor/others/embedded_components/core/file/readonly_file";
import {
    readonlyTableOfContentEmbedding,
    tableOfContentEmbedding,
} from "@html_editor/others/embedded_components/core/table_of_content/table_of_content";
import { toggleBlockEmbedding } from "@html_editor/others/embedded_components/core/toggle_block/toggle_block";
import { readonlyVideoEmbedding } from "@html_editor/others/embedded_components/core/video/readonly_video";

import { readonlySyntaxHighlightingEmbedding } from "./core/syntax_highlighting/readonly_syntax_highlighting.js";

export const MAIN_EMBEDDINGS = [
    fileEmbedding,
    dateEmbedding,
    tableOfContentEmbedding,
    toggleBlockEmbedding,
    videoEmbedding,
    captionEmbedding,
    syntaxHighlightingEmbedding,
];

export const READONLY_MAIN_EMBEDDINGS = [
    readonlyFileEmbedding,
    readonlyDateEmbedding,
    readonlyTableOfContentEmbedding,
    toggleBlockEmbedding,
    readonlyVideoEmbedding,
    captionEmbedding,
    readonlySyntaxHighlightingEmbedding,
];
