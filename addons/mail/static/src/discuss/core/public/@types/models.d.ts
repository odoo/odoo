declare module "models" {
    export interface Store {
        discuss_public_thread: Thread;
    }
    export interface Thread {
        setActiveURL: () => void;
    }
}
