declare module "models" {
    export interface DiscussChannel {
        hasActiveChatbot: Readonly<boolean>;
        hasWelcomeMessage: Readonly<boolean>;
        isLastCommentFromVisitor: Readonly<boolean>;
    }
}
