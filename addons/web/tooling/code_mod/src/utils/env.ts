import { File } from "@babel/types";

export interface ExtendedEnv extends Env {
    inFilePath: string;
}

export interface Env {
    getAST: (filePath: string) => File | null;
    tagAsModified: (filePath: string) => void;
    cleaning: Set<() => void>;
}
