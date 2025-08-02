import { readonlyFileEmbedding } from "@html_editor/others/embedded_components/core/file/readonly_file";
import { readonlyTableOfContentEmbedding } from "@html_editor/others/embedded_components/core/table_of_content/table_of_content";
import { toggleBlockEmbedding } from "@html_editor/others/embedded_components/core/toggle_block/toggle_block";
import { readonlyVideoEmbedding } from "@html_editor/others/embedded_components/core/video/readonly_video";

export const PUBLIC_EMBEDDINGS = [
    readonlyFileEmbedding,
    readonlyTableOfContentEmbedding,
    toggleBlockEmbedding,
    readonlyVideoEmbedding,
];
