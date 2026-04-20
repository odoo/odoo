import { fileEmbedding } from "@html_editor/others/embedded_components/backend/file/file";
import { captionEmbedding } from "@html_editor/others/embedded_components/backend/caption/caption";
import { readonlyFileEmbedding } from "@html_editor/others/embedded_components/core/file/readonly_file";
import {
    readonlyTableOfContentEmbedding,
    tableOfContentEmbedding,
} from "@html_editor/others/embedded_components/core/table_of_content/table_of_content";
import { toggleBlockEmbedding } from "@html_editor/others/embedded_components/core/toggle_block/toggle_block";
import { videoEmbedding } from "@html_editor/others/embedded_components/backend/video/video";
import { readonlyVideoEmbedding } from "@html_editor/others/embedded_components/core/video/readonly_video";
import { syntaxHighlightingEmbedding } from "@html_editor/others/embedded_components/backend/syntax_highlighting/syntax_highlighting";
import { readonlySyntaxHighlightingEmbedding } from "./core/syntax_highlighting/readonly_syntax_highlighting";
import { dateEmbedding } from "./backend/date/date";
import { readonlyDateEmbedding } from "./core/date/readonly_date";

export const MAIN_EMBEDDINGS = [
    fileEmbedding,
    tableOfContentEmbedding,
    toggleBlockEmbedding,
    dateEmbedding,
    videoEmbedding,
    captionEmbedding,
    syntaxHighlightingEmbedding,
];

export const READONLY_MAIN_EMBEDDINGS = [
    readonlyDateEmbedding,
    readonlyFileEmbedding,
    readonlyTableOfContentEmbedding,
    toggleBlockEmbedding,
    readonlyVideoEmbedding,
    captionEmbedding,
    readonlySyntaxHighlightingEmbedding,
];
