import { File } from "@babel/types";

export interface Env extends PartialEnv {
    inFilePath: string;
}

export interface PartialEnv {
    getAST: (filePath: string) => File | null;
    tagAsModified: (filePath: string) => void;
    cleaning: Set<() => void>;
}
