import { excalidrawEmbedding } from "@html_editor/others/embedded_components/backend/excalidraw/excalidraw";
import { readonlyExcalidrawEmbedding } from "@html_editor/others/embedded_components/core/excalidraw/readonly_excalidraw";
import { fileEmbedding } from "@html_editor/others/embedded_components/backend/file/file";
import { readonlyFileEmbedding } from "@html_editor/others/embedded_components/core/file/readonly_file";
import {
    readonlyTableOfContentEmbedding,
    tableOfContentEmbedding,
} from "@html_editor/others/embedded_components/core/table_of_content/table_of_content";
import { videoEmbedding } from "@html_editor/others/embedded_components/core/video/video";

export const MAIN_EMBEDDINGS = [
    excalidrawEmbedding,
    fileEmbedding,
    tableOfContentEmbedding,
    videoEmbedding,
];

export const READONLY_MAIN_EMBEDDINGS = [
    readonlyExcalidrawEmbedding,
    readonlyFileEmbedding,
    readonlyTableOfContentEmbedding,
    videoEmbedding,
];
