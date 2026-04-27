import {
    readonlyFileEmbedding,
    ReadonlyEmbeddedFileComponent,
} from "@html_editor/others/embedded_components/core/file/readonly_file";
import { MacrosFileMixin } from "@knowledge/editor/embedded_components/backend/file/macros_file_mixin";

export const ReadonlyMacrosEmbeddedFileComponent = MacrosFileMixin(
    ReadonlyEmbeddedFileComponent,
    "knowledge.ReadonlyEmbeddedFile"
);

export const readonlyMacrosFileEmbedding = {
    ...readonlyFileEmbedding,
    Component: ReadonlyMacrosEmbeddedFileComponent,
};
