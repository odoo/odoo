import {
    fileEmbedding,
    EmbeddedFileComponent,
} from "@html_editor/others/embedded_components/backend/file/file";
import { MacrosFileMixin } from "@knowledge/editor/embedded_components/backend/file/macros_file_mixin";

export const MacrosEmbeddedFileComponent = MacrosFileMixin(
    EmbeddedFileComponent,
    "knowledge.EmbeddedFile"
);

export const macrosFileEmbedding = {
    ...fileEmbedding,
    Component: MacrosEmbeddedFileComponent,
};
