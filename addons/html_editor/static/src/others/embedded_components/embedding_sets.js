import { excalidrawEmbedding } from "@html_editor/others/embedded_components/backend/excalidraw/excalidraw";
import { readonlyExcalidrawEmbedding } from "@html_editor/others/embedded_components/core/excalidraw/readonly_excalidraw";
import { fileEmbedding } from "@html_editor/others/embedded_components/backend/file/file";
import { readonlyFileEmbedding } from "@html_editor/others/embedded_components/core/file/readonly_file";

export const MAIN_EMBEDDINGS = [
    excalidrawEmbedding,
    fileEmbedding,
];

export const READONLY_MAIN_EMBEDDINGS = [
    readonlyExcalidrawEmbedding,
    readonlyFileEmbedding,
];
