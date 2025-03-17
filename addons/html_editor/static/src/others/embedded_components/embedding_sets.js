import { fileEmbedding } from "@html_editor/others/embedded_components/backend/file/file";
import { readonlyFileEmbedding } from "@html_editor/others/embedded_components/core/file/readonly_file";
import {
    readonlyTableOfContentEmbedding,
    tableOfContentEmbedding,
} from "@html_editor/others/embedded_components/core/table_of_content/table_of_content";
import { toggleBlockEmbedding } from "@html_editor/others/embedded_components/core/toggle_block/toggle_block";
import { videoEmbedding } from "@html_editor/others/embedded_components/core/video/video";

export const MAIN_EMBEDDINGS = [
    fileEmbedding,
    tableOfContentEmbedding,
    toggleBlockEmbedding,
    videoEmbedding,
];

export const READONLY_MAIN_EMBEDDINGS = [
    readonlyFileEmbedding,
    readonlyTableOfContentEmbedding,
    toggleBlockEmbedding,
    videoEmbedding,
];
