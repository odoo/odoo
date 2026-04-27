import { readonlyFileEmbedding } from "@html_editor/others/embedded_components/core/file/readonly_file";
import { readonlyTableOfContentEmbedding } from "@html_editor/others/embedded_components/core/table_of_content/table_of_content";
import { videoEmbedding } from "@html_editor/others/embedded_components/core/video/video";
import { readonlyArticleIndexEmbedding } from "@knowledge/editor/embedded_components/core/article_index/readonly_article_index";
import { clipboardEmbedding } from "@knowledge/editor/embedded_components/core/clipboard/embedded_clipboard";
import { viewPlaceholderEmbedding } from "@website_knowledge/frontend/editor/embedded_components/view/view_placeholder";
import { publicViewLinkEmbedding } from "@website_knowledge/frontend/editor/embedded_components/view_link/public_embedded_view_link";

export const KNOWLEDGE_PUBLIC_EMBEDDINGS = [
    clipboardEmbedding,
    publicViewLinkEmbedding,
    readonlyArticleIndexEmbedding,
    readonlyFileEmbedding,
    readonlyTableOfContentEmbedding,
    videoEmbedding,
    viewPlaceholderEmbedding,
];
